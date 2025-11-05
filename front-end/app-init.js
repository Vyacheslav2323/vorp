import { initRecognition, toggleSpeak, toggleListen, isRecording, getCurrentLang } from './recognition.js';
import { getCurrentUser } from './auth.js';
import { t, translatePage } from './translations.js';

let translationTimeout = null;

function getLangDisplayName(locale) {
  const langCode = locale.split('-')[0];
  const user = getCurrentUser();
  const nativeLang = user?.native_language || 'en';
  
  const names = {
    en: {
      'en': 'English',
      'ko': 'Korean',
      'ru': 'Russian',
      'zh': 'Chinese',
      'vi': 'Vietnamese'
    },
    ru: {
      'en': 'Английский',
      'ko': 'Корейский',
      'ru': 'Русский',
      'zh': 'Китайский',
      'vi': 'Вьетнамский'
    },
    zh: {
      'en': '英语',
      'ko': '韩语',
      'ru': '俄语',
      'zh': '中文',
      'vi': '越南语'
    },
    vi: {
      'en': 'Tiếng Anh',
      'ko': 'Tiếng Hàn',
      'ru': 'Tiếng Nga',
      'zh': 'Tiếng Trung',
      'vi': 'Tiếng Việt'
    }
  };
  
  const langMap = names[nativeLang] || names.en;
  return langMap[langCode] || 'Unknown';
}

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

export function initMainApp() {
  console.log('initMainApp called');
  
  const elements = {
    speakBtn: document.getElementById('speakBtn'),
    listenBtn: document.getElementById('listenBtn'),
    statusEl: document.getElementById('status'),
    chatEl: document.getElementById('chat'),
    voiceToggle: document.getElementById('voiceTranslationToggle')
  };
  
  console.log('Elements found:', {
    speakBtn: !!elements.speakBtn,
    listenBtn: !!elements.listenBtn,
    statusEl: !!elements.statusEl,
    chatEl: !!elements.chatEl,
    voiceToggle: !!elements.voiceToggle
  });
  
  if (!elements.speakBtn || !elements.listenBtn || !elements.statusEl || !elements.chatEl) {
    console.error('Required elements not found!', elements);
    return;
  }
  
  const savedToggleState = localStorage.getItem('voiceTranslationEnabled');
  if (elements.voiceToggle) {
    elements.voiceToggle.checked = savedToggleState !== 'false';
    elements.voiceToggle.addEventListener('change', (e) => {
      localStorage.setItem('voiceTranslationEnabled', e.target.checked.toString());
    });
  }

  function onRecognitionResult() {
    
  }

  function handleSpeakClick() {
    toggleSpeak();
  }

  function handleListenClick() {
    toggleListen();
  }

  function updateStatus() {
    const lang = getCurrentLang();
    if (isRecording() && lang) {
      const langName = getLangDisplayName(lang);
      if (elements.statusEl) {
        elements.statusEl.textContent = t('status.recording', { language: langName });
        elements.statusEl.classList.add('recording');
      }
      const user = getCurrentUser();
      const nativeLang = user?.native_language || 'en';
      const nativeLocale = mapLangToLocale(nativeLang);
      if (lang.startsWith(nativeLocale.split('-')[0])) {
        elements.speakBtn?.classList.add('recording');
        elements.listenBtn?.classList.remove('recording');
      } else {
        elements.listenBtn?.classList.add('recording');
        elements.speakBtn?.classList.remove('recording');
      }
    } else {
      if (elements.statusEl) {
        elements.statusEl.textContent = t('status.ready');
        elements.statusEl.classList.remove('recording');
      }
      elements.speakBtn?.classList.remove('recording');
      elements.listenBtn?.classList.remove('recording');
    }
  }

  function init() {
    try {
      translatePage();
      const result = initRecognition(elements, onRecognitionResult, updateStatus);
      if (!result.supported) {
        if (elements.statusEl) {
          elements.statusEl.textContent = t('status.not_supported');
        }
        elements.speakBtn.disabled = true;
        elements.listenBtn.disabled = true;
        return;
      }
      elements.speakBtn.addEventListener('click', handleSpeakClick);
      elements.listenBtn.addEventListener('click', handleListenClick);
      console.log('initMainApp completed successfully');
    } catch (e) {
      console.error('Error in initMainApp:', e);
      throw e;
    }
  }

  init();
}
