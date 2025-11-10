import { translate } from './translation.js';
import { getBase } from './utils.js';
import { getAuthToken, getCurrentUser } from './auth.js';
let speakRecognition = null;
let listenRecognition = null;
let finalTranscript = '';
let recording = false;
let currentLang = null;
let currentElements = null;
let currentCallback = null;
let statusUpdateCallback = null;
let chat = [];
let interimText = '';
let currentRole = null;
let translateTimer = null;
let nativeLang = null;
let mediaRecorder = null;
let mediaStream = null;
let recordedChunks = [];

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
  rec.onstart = () => {
    currentLang = lang;
    handleStart();
  };
  rec.onresult = (e) => handleResult(e);
  rec.onerror = (e) => handleError(e);
  rec.onend = () => handleEnd();
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

async function handleStart() {
  recording = true;
  currentRole = deriveRole({ lang: currentLang });
  finalTranscript = '';
  recordedChunks = [];
  try {
    mediaStream = await navigator.mediaDevices.getUserMedia({ audio: true });
    mediaRecorder = new MediaRecorder(mediaStream);
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
  } catch (e) {
    console.error('Error starting MediaRecorder:', e);
  }
  if (statusUpdateCallback) {
    statusUpdateCallback();
  }
}

function handleResult(event) {
  const res = Array.from(event.results).slice(event.resultIndex);
  const texts = res.map(r => ({ t: r[0].transcript, f: r.isFinal }));
  const finals = texts.filter(x => x.f).map(x => x.t).join(' ');
  const interims = texts.filter(x => !x.f).map(x => x.t).join(' ');
  if (finals) finalTranscript = (finalTranscript + ' ' + finals).trim();
  interimText = interims;
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
  chat = clearDraft({ chat, role: currentRole });
  renderChat({ el: currentElements.chatEl, chat, interim: interimText });
  added.forEach(i => translateMessageAt({ index: i }));
  added.forEach(i => maybeIngestKo(chat[i]));
  if (currentCallback) currentCallback(finalTranscript);
}

function handleError(event) {
  recording = false;
  if (mediaRecorder && mediaRecorder.state !== 'inactive') {
    mediaRecorder.stop();
  }
  if (mediaStream) {
    mediaStream.getTracks().forEach(track => track.stop());
    mediaStream = null;
  }
  
  if (currentElements.statusEl) {
    if (event.error === 'no-speech') {
      currentElements.statusEl.textContent = 'No speech detected';
    } else if (event.error === 'not-allowed') {
      currentElements.statusEl.textContent = 'Microphone access denied';
    } else {
      currentElements.statusEl.textContent = `Error: ${event.error}`;
    }
  }
}

function handleEnd() {
  recording = false;
  if (mediaRecorder && mediaRecorder.state !== 'inactive') {
    mediaRecorder.stop();
  }
  if (mediaStream) {
    mediaStream.getTracks().forEach(track => track.stop());
    mediaStream = null;
  }
  currentLang = null;
  if (statusUpdateCallback) {
    statusUpdateCallback();
  }
}

export function toggleSpeak() {
  if (speakRecognition) {
    if (recording) {
      speakRecognition.stop();
      if (listenRecognition) listenRecognition.stop();
    } else {
      if (listenRecognition) listenRecognition.stop();
      speakRecognition.start();
    }
  }
}

export function toggleListen() {
  if (listenRecognition) {
    if (recording) {
      listenRecognition.stop();
      if (speakRecognition) speakRecognition.stop();
    } else {
      if (speakRecognition) speakRecognition.stop();
      listenRecognition.start();
    }
  }
}

export function isRecording() {
  return recording;
}

export function getCurrentLang() {
  return currentLang;
}

export function getFinalTranscript() {
  return finalTranscript.trim();
}
function deriveRole(arg) {
  const l = arg.lang || '';
  const nativeLocale = nativeLang ? mapLangToLocale(nativeLang) : 'en-US';
  return l.startsWith(nativeLocale.split('-')[0]) ? 'speak' : 'listen';
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
  const list = (arg.chat || []).filter(m => !m.draft);
  if (!el) return;
  el.innerHTML = '';
  const nodes = list.map(m => {
    const item = document.createElement('div');
    item.className = `msg ${m.role === 'speak' ? 'left' : 'right'} ${m.draft ? 'draft' : ''}`;
    const bubble = document.createElement('div');
    bubble.className = `bubble ${m.kind === 'translation' ? 'trans' : ''}`;
    bubble.textContent = m.text;
    item.appendChild(bubble);
    return item;
  });
  nodes.forEach(n => el.appendChild(n));
  el.scrollTop = el.scrollHeight;
}

async function translateMessageAt(arg) {
  const i = arg.index;
  const m = chat[i];
  if (!m || m.draft) return;
  const s = m.role === 'speak' ? (nativeLang || 'en') : 'ko';
  const t = s === 'ko' ? (nativeLang || 'en') : 'ko';
  const r = await translate(m.text, s, t);
  const txt = r && r.text ? r.text : '';
  chat = insertOrReplaceTranslation({ chat, sourceIndex: i, role: m.role, text: txt });
  renderChat({ el: currentElements.chatEl, chat, interim: interimText });
  const after = i + 1;
  maybeIngestKo(chat[after]);
  
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
  fetch(base + '/vocab/ingest', { method: 'POST', headers: { 'Content-Type': 'application/json', 'Authorization': token ? ('Bearer ' + token) : '' }, body: JSON.stringify({ text: m.text }) });
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
    const lang = currentLang ? currentLang.split('-')[0] : null;
    try {
      await fetch(base + '/recording/save', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': token ? ('Bearer ' + token) : ''
        },
        body: JSON.stringify({
          audio: base64,
          role: currentRole || 'speak',
          transcript: transcript || null,
          language: lang || null
        })
      });
    } catch (e) {
      console.error('Error saving recording:', e);
    }
  };
  reader.readAsDataURL(blob);
  recordedChunks = [];
}