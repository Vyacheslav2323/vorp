import { translate } from './translation.js';
import { getBase } from './utils.js';
import { getAuthToken, getCurrentUser } from './auth.js';

// State management
let speakRecognition = null;
let listenRecognition = null;
let currentElements = null;
let currentCallback = null;
let statusUpdateCallback = null;
let nativeLang = null;

// Recording state
let recording = false;
let activeMode = null; // 'speak' or 'listen' or null
let mediaRecorder = null;
let mediaStream = null;
let recordedChunks = [];
let recordingStartTime = null;

// Transcript state
let chat = [];
let interimText = '';
let finalTranscript = '';
let currentRole = null;

function mapLangToLocale(lang) {
  const mapping = {
    'en': 'en-US',
    'ko': 'ko-KR',
    'ru': 'ru-RU',
    'zh': 'zh-CN',
    'vi': 'vi-VN'
  };
  return mapping[lang] || 'en-US';
}

function createRecognition(lang) {
  const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
  if (!SpeechRecognition) return null;
  
  const rec = new SpeechRecognition();
  rec.lang = lang;
  rec.continuous = true;
  rec.interimResults = true;
  rec.onresult = (e) => handleResult(e);
  rec.onerror = (e) => handleError(e);
  rec.onend = () => handleRecognitionEnd();
  return rec;
}

export function initRecognition(elements, onResultCallback, onStatusUpdate) {
  const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
  
  if (!SpeechRecognition) {
    return { supported: false };
  }
  
  const user = getCurrentUser();
  nativeLang = user?.native_language || 'en';
  const nativeLocale = mapLangToLocale(nativeLang);
  
  currentElements = elements;
  currentCallback = onResultCallback;
  statusUpdateCallback = onStatusUpdate;
  
  speakRecognition = createRecognition(nativeLocale);
  listenRecognition = createRecognition('ko-KR');
  
  return { supported: true };
}

async function startRecording() {
  if (recording) return; // Already recording
  
  try {
    mediaStream = await navigator.mediaDevices.getUserMedia({
      audio: {
        echoCancellation: true,
        noiseSuppression: true,
        autoGainControl: true
      }
    });
    mediaRecorder = new MediaRecorder(mediaStream);
    recordedChunks = [];
    recordingStartTime = Date.now();
    
    mediaRecorder.ondataavailable = (e) => {
      if (e.data.size > 0) {
        recordedChunks.push(e.data);
      }
    };
    
    mediaRecorder.onstop = () => {
      if (recordedChunks.length > 0) {
        saveRecording();
      }
    };
    
    mediaRecorder.start();
    recording = true;
    console.log('Recording started');
  } catch (e) {
    console.error('Error starting MediaRecorder:', e);
    if (currentElements?.statusEl) {
      currentElements.statusEl.textContent = 'Microphone access denied';
    }
  }
}

function stopRecording() {
  if (!recording) return;
  
  recording = false;
  
  // Stop MediaRecorder
  if (mediaRecorder && mediaRecorder.state !== 'inactive') {
    mediaRecorder.stop();
  }
  
  // Stop media stream
  if (mediaStream) {
    mediaStream.getTracks().forEach(track => track.stop());
    mediaStream = null;
  }
  
  // Stop all recognition
  if (speakRecognition) {
    try {
      speakRecognition.stop();
    } catch (e) {
      // Ignore errors
    }
  }
  if (listenRecognition) {
    try {
      listenRecognition.stop();
    } catch (e) {
      // Ignore errors
    }
  }
  
  // Clear interim text
  interimText = '';
  chat = clearDraft({ chat, role: currentRole });
  renderChat({ el: currentElements?.chatEl, chat, interim: '' });
  
  console.log('Recording stopped and saved');
  
  if (statusUpdateCallback) {
    statusUpdateCallback();
  }
}

function startRecognition(mode) {
  const targetRec = mode === 'speak' ? speakRecognition : listenRecognition;
  if (!targetRec) return;
  
  // Clear draft for previous role if switching
  if (currentRole && currentRole !== mode) {
    chat = clearDraft({ chat, role: currentRole });
    interimText = '';
  }
  
  // Stop the other recognition if running
  if (mode === 'speak' && listenRecognition) {
    try {
      listenRecognition.stop();
    } catch (e) {}
  } else if (mode === 'listen' && speakRecognition) {
    try {
      speakRecognition.stop();
    } catch (e) {}
  }
  
  // Start the target recognition
  try {
    currentRole = mode;
    targetRec.start();
    const lang = mode === 'speak' ? mapLangToLocale(nativeLang) : 'ko-KR';
    console.log(`Recognition started: ${mode} (${lang})`);
  } catch (e) {
    console.error(`Error starting ${mode} recognition:`, e);
  }
}

function handleResult(event) {
  const res = Array.from(event.results).slice(event.resultIndex);
  const texts = res.map(r => ({ t: r[0].transcript, f: r.isFinal }));
  const finals = texts.filter(x => x.f).map(x => x.t).join(' ');
  const interims = texts.filter(x => !x.f).map(x => x.t).join(' ');
  
  // Update final transcript
  if (finals) {
    finalTranscript = (finalTranscript + ' ' + finals).trim();
  }
  
  // Update interim text and show immediately
  interimText = interims;
  if (interimText) {
    chat = upsertDraft({ chat, role: currentRole, text: interimText });
  } else {
    chat = clearDraft({ chat, role: currentRole });
  }
  
  // Process final results - translate with OpenAI
  if (finals) {
    const split = splitSentences({ text: finals });
    let added = [];
    
    if (split.sentences.length > 0) {
      const appended = appendMessages({ chat, role: currentRole, sentences: split.sentences });
      chat = appended.list;
      added = appended.indices;
    } else if (finals) {
      const appended2 = appendMessages({ chat, role: currentRole, sentences: [finals] });
      chat = appended2.list;
      added = appended2.indices;
    }
    
    // Clear draft after adding final messages
    chat = clearDraft({ chat, role: currentRole });
    interimText = '';
    
    // Translate each final message with OpenAI
    added.forEach(i => translateMessageAt({ index: i }));
    added.forEach(i => maybeIngestKo(chat[i]));
  }
  
  // Render chat with interim results
  renderChat({ el: currentElements?.chatEl, chat, interim: interimText });
  
  if (currentCallback) {
    currentCallback(finalTranscript);
  }
}

function handleError(event) {
  console.error('Recognition error:', event.error);
  
  if (currentElements?.statusEl) {
    if (event.error === 'no-speech') {
      currentElements.statusEl.textContent = 'No speech detected';
    } else if (event.error === 'not-allowed') {
      currentElements.statusEl.textContent = 'Microphone access denied';
    } else {
      currentElements.statusEl.textContent = `Error: ${event.error}`;
    }
  }
  
  // Don't stop recording on error, just restart recognition
  if (recording && activeMode) {
    setTimeout(() => {
      if (recording && activeMode) {
        startRecognition(activeMode);
      }
    }, 500);
  }
}

function handleRecognitionEnd() {
  // If still recording, restart recognition automatically
  if (recording && activeMode) {
    setTimeout(() => {
      if (recording && activeMode) {
        startRecognition(activeMode);
      }
    }, 100);
  }
}

export function toggleSpeak() {
  if (!speakRecognition) return;
  
  if (recording && activeMode === 'speak') {
    // Already recording in speak mode - stop and save
    stopRecording();
    activeMode = null;
    finalTranscript = '';
  } else if (recording && activeMode === 'listen') {
    // Switch from listen to speak - keep recording, just switch recognition
    startRecognition('speak');
    activeMode = 'speak';
  } else {
    // Start recording and recognition
    activeMode = 'speak';
    startRecording();
    startRecognition('speak');
  }
  
  if (statusUpdateCallback) {
    statusUpdateCallback();
  }
}

export function toggleListen() {
  if (!listenRecognition) return;
  
  if (recording && activeMode === 'listen') {
    // Already recording in listen mode - stop and save
    stopRecording();
    activeMode = null;
    finalTranscript = '';
  } else if (recording && activeMode === 'speak') {
    // Switch from speak to listen - keep recording, just switch recognition
    startRecognition('listen');
    activeMode = 'listen';
  } else {
    // Start recording and recognition
    activeMode = 'listen';
    startRecording();
    startRecognition('listen');
  }
  
  if (statusUpdateCallback) {
    statusUpdateCallback();
  }
}

export function isRecording() {
  return recording;
}

export function getCurrentLang() {
  if (activeMode === 'speak') {
    return mapLangToLocale(nativeLang);
  } else if (activeMode === 'listen') {
    return 'ko-KR';
  }
  return null;
}

export function getFinalTranscript() {
  return finalTranscript.trim();
}

function splitSentences(arg) {
  const s = arg.text || '';
  if (!s) return { sentences: [], remainder: '' };
  const parts = s.split(/([.!?…]+)\s+/).filter(x => x);
  const grouped = [];
  let carry = '';
  parts.forEach(p => {
    if (/[.!?…]+$/.test(p)) {
      grouped.push((carry + p).trim());
      carry = '';
    } else {
      carry = (carry + ' ' + p).trim();
    }
  });
  return { sentences: grouped, remainder: carry };
}

function appendMessages(arg) {
  const list = arg.chat || [];
  const role = arg.role;
  const sentences = arg.sentences || [];
  const msgs = sentences.map(text => ({ role, text, draft: false, kind: 'transcript' }));
  const start = list.length;
  const merged = list.concat(msgs);
  const indices = msgs.map((_, k) => start + k);
  return { list: merged, indices };
}

function upsertDraft(arg) {
  const list = arg.chat || [];
  const role = arg.role;
  const text = arg.text || '';
  const idx = [...list].reverse().findIndex(m => m.role === role && m.draft && m.kind === 'transcript');
  if (idx === -1) return list.concat([{ role, text, draft: true, kind: 'transcript' }]);
  const pos = list.length - 1 - idx;
  const updated = list.slice(0, pos).concat([{ role, text, draft: true, kind: 'transcript' }], list.slice(pos + 1));
  return updated;
}

function clearDraft(arg) {
  const list = arg.chat || [];
  const role = arg.role;
  const idx = [...list].reverse().findIndex(m => m.role === role && m.draft && m.kind === 'transcript');
  if (idx === -1) return list;
  const pos = list.length - 1 - idx;
  return list.slice(0, pos).concat(list.slice(pos + 1));
}

function renderChat(arg) {
  const el = arg.el;
  const list = arg.chat || [];
  const interim = arg.interim || '';
  if (!el) return;
  el.innerHTML = '';
  
  // Render all messages including drafts (interim results)
  const nodes = list.map(m => {
    const item = document.createElement('div');
    item.className = `msg ${m.role === 'speak' ? 'left' : 'right'} ${m.draft ? 'draft' : ''}`;
    const bubble = document.createElement('div');
    bubble.className = `bubble ${m.kind === 'translation' ? 'trans' : ''} ${m.draft ? 'interim' : ''}`;
    bubble.textContent = m.text;
    item.appendChild(bubble);
    return item;
  });
  
  // If there's interim text and no draft message for current role, show it
  if (interim && currentRole && !list.some(m => m.role === currentRole && m.draft)) {
    const item = document.createElement('div');
    item.className = `msg ${currentRole === 'speak' ? 'left' : 'right'} draft`;
    const bubble = document.createElement('div');
    bubble.className = 'bubble interim';
    bubble.textContent = interim;
    item.appendChild(bubble);
    nodes.push(item);
  }
  
  nodes.forEach(n => el.appendChild(n));
  el.scrollTop = el.scrollHeight;
}

async function translateMessageAt(arg) {
  const i = arg.index;
  const m = chat[i];
  if (!m || m.draft) return;
  
  const s = m.role === 'speak' ? (nativeLang || 'en') : 'ko';
  const t = s === 'ko' ? (nativeLang || 'en') : 'ko';
  
  // Translate with OpenAI API
  const r = await translate(m.text, s, t);
  const txt = r && r.text ? r.text : '';
  
  chat = insertOrReplaceTranslation({ chat, sourceIndex: i, role: m.role, text: txt });
  renderChat({ el: currentElements?.chatEl, chat, interim: interimText });
  
  const after = i + 1;
  maybeIngestKo(chat[after]);
  
  // Play translation audio
  if (txt) {
    if (m.role === 'listen') {
      playTranslationAudio(txt, nativeLang || 'en');
    } else if (m.role === 'speak') {
      playTranslationAudio(txt, 'ko');
    }
  }
}

function insertOrReplaceTranslation(arg) {
  const list = arg.chat || [];
  const i = arg.sourceIndex;
  const role = arg.role;
  const text = arg.text || '';
  const after = i + 1;
  if (list[after] && list[after].kind === 'translation' && list[after].role === role) {
    const updated = list.slice(0, after).concat([{ role, text, draft: false, kind: 'translation' }], list.slice(after + 1));
    return updated;
  }
  const head = list.slice(0, after);
  const tail = list.slice(after);
  return head.concat([{ role, text, draft: false, kind: 'translation' }], tail);
}

function maybeIngestKo(m) {
  if (!m) return;
  const isKo = m.kind === 'transcript' ? (m.role === 'listen') : (m.kind === 'translation');
  if (!isKo) return;
  const token = getAuthToken();
  const base = getBase();
  fetch(base + '/vocab/ingest', { 
    method: 'POST', 
    headers: { 
      'Content-Type': 'application/json', 
      'Authorization': token ? ('Bearer ' + token) : '' 
    }, 
    body: JSON.stringify({ text: m.text }) 
  });
}

function isVoiceTranslationEnabled() {
  const toggle = document.getElementById('voiceTranslationToggle');
  if (!toggle) return true;
  return toggle.checked;
}

async function playTranslationAudio(text, lang) {
  if (!text || !text.trim()) return;
  if (!isVoiceTranslationEnabled()) return;
  
  const base = getBase();
  try {
    const response = await fetch(base + '/tts', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ text: text.trim(), lang })
    });
    
    const result = await response.json();
    if (result.success && result.audio) {
      const audio = new Audio(`data:audio/mp3;base64,${result.audio}`);
      audio.play().catch(e => {
        console.error('Error playing translation audio:', e);
      });
    }
  } catch (e) {
    console.error('Error generating translation audio:', e);
  }
}

async function saveRecording() {
  if (recordedChunks.length === 0) return;
  
  const blob = new Blob(recordedChunks, { type: 'audio/webm' });
  const reader = new FileReader();
  
  reader.onloadend = async () => {
    const base64 = reader.result.split(',')[1];
    const token = getAuthToken();
    const base = getBase();
    const transcript = getFinalTranscript();
    const lang = activeMode === 'speak' ? (nativeLang || 'en') : 'ko';
    
    try {
      await fetch(base + '/recording/save', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': token ? ('Bearer ' + token) : ''
        },
        body: JSON.stringify({
          audio: base64,
          role: activeMode || 'speak',
          transcript: transcript || null,
          language: lang || null
        })
      });
      console.log('Recording saved to database');
    } catch (e) {
      console.error('Error saving recording:', e);
    }
  };
  
  reader.readAsDataURL(blob);
  recordedChunks = [];
}
