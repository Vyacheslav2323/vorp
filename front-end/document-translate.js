import { translate } from './translation.js';
import { analyzeBaseForms } from './vocabulary.js';
import { t, translatePage } from './translations.js';
import { getCurrentUser, getAuthToken, isAuthenticated } from './auth.js';
import { getBase } from './utils.js';

const docState = { processing: false, userLang: 'en', elements: null };

export function initDocumentTranslatePage() {
  docState.userLang = resolveUserLang();
  docState.elements = buildDocElements();
  translatePage();
  if (!docState.elements.root) {
    return;
  }
  bindDocHandlers();
  resetDocView();
}

function resolveUserLang() {
  const user = getCurrentUser();
  if (user && user.native_language) {
    return user.native_language;
  }
  const stored = localStorage.getItem('selectedLanguage');
  if (stored) {
    return stored;
  }
  return 'en';
}

function buildDocElements() {
  const refs = {
    root: document.querySelector('.document-translate-page'),
    input: document.getElementById('docInput'),
    translation: document.getElementById('docTranslation'),
    status: document.getElementById('docStatus'),
    translateBtn: document.getElementById('docTranslateBtn'),
    clearBtn: document.getElementById('docClearBtn'),
    langSelect: document.getElementById('docSourceLang'),
    cards: document.getElementById('docCards'),
    cardCount: document.getElementById('docCardCount')
  };
  return refs;
}

function bindDocHandlers() {
  const el = docState.elements;
  if (!el) {
    return;
  }
  if (el.translateBtn) {
    el.translateBtn.onclick = () => {
      handleDocTranslate();
    };
  }
  if (el.clearBtn) {
    el.clearBtn.onclick = () => {
      handleDocClear();
    };
  }
}

function resetDocView() {
  const el = docState.elements;
  if (!el) {
    return;
  }
  if (el.input) {
    el.input.value = '';
  }
  if (el.translation) {
    el.translation.textContent = '';
  }
  if (el.cards) {
    el.cards.innerHTML = buildEmptyState();
  }
  if (el.cardCount) {
    el.cardCount.textContent = '0';
  }
  if (el.langSelect) {
    el.langSelect.value = 'ko';
  }
  setDocStatus(t('doc.status_idle'));
}

async function handleDocTranslate() {
  if (docState.processing) {
    return;
  }
  const payload = readPayload();
  if (!payload.text) {
    setDocStatus(t('doc.status_error'));
    return;
  }
  startProcessing();
  setDocStatus(t('doc.status_processing'));
  try {
    await processDocument(payload);
    setDocStatus(t('doc.status_success'));
  } catch (error) {
    setDocStatus(resolveErrorMessage(error));
  } finally {
    stopProcessing();
  }
}

function readPayload() {
  const raw = docState.elements.input ? docState.elements.input.value : '';
  const selected = docState.elements.langSelect ? docState.elements.langSelect.value : 'ko';
  const text = raw.trim();
  const source = selected === 'native' ? docState.userLang : 'ko';
  const target = source === 'ko' ? docState.userLang : 'ko';
  return { text, source, target };
}

function startProcessing() {
  docState.processing = true;
  toggleButtons(true);
}

function stopProcessing() {
  docState.processing = false;
  toggleButtons(false);
}

function toggleButtons(disabled) {
  const el = docState.elements;
  if (!el) {
    return;
  }
  if (el.translateBtn) {
    el.translateBtn.disabled = disabled;
  }
  if (el.clearBtn) {
    el.clearBtn.disabled = disabled;
  }
}

function setDocStatus(text) {
  if (!docState.elements.status) {
    return;
  }
  docState.elements.status.textContent = text;
}

async function processDocument(arg) {
  const translated = await translate(arg.text, arg.source, arg.target);
  const output = translated && translated.text ? translated.text.trim() : '';
  if (!output) {
    throw new Error('doc.status_error');
  }
  applyTranslation(output);
  const korean = pickKoreanText({ source: arg.source, original: arg.text, translated: output });
  const words = await analyzeKoreanText(korean);
  await ingestKoreanText(korean);
  renderCards({ words });
}

function pickKoreanText(arg) {
  if (arg.source === 'ko') {
    return arg.original;
  }
  return arg.translated;
}

function applyTranslation(text) {
  if (!docState.elements.translation) {
    return;
  }
  docState.elements.translation.textContent = text;
}

async function analyzeKoreanText(text) {
  if (!text) {
    return [];
  }
  const words = await analyzeBaseForms(text);
  return Array.isArray(words) ? words : [];
}

async function ingestKoreanText(text) {
  if (!text) {
    throw new Error('doc.status_error');
  }
  if (!isAuthenticated()) {
    throw new Error('doc.auth_required');
  }
  const token = getAuthToken();
  if (!token) {
    throw new Error('doc.auth_required');
  }
  const response = await fetch(`${getBase()}/vocab/ingest`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'Authorization': `Bearer ${token}`
    },
    body: JSON.stringify({ text })
  });
  const result = await response.json();
  if (!response.ok || !result.success) {
    throw new Error('doc.status_error');
  }
  return true;
}

function renderCards(arg) {
  if (!docState.elements.cards) {
    return;
  }
  const summary = summarizeWords(arg.words || []);
  if (docState.elements.cardCount) {
    docState.elements.cardCount.textContent = String(summary.length);
  }
  if (summary.length === 0) {
    docState.elements.cards.innerHTML = buildEmptyState();
    return;
  }
  docState.elements.cards.innerHTML = buildCardMarkup(summary);
}

function summarizeWords(words) {
  const counts = words.reduce((acc, word) => {
    if (!word) {
      return acc;
    }
    acc[word] = (acc[word] || 0) + 1;
    return acc;
  }, {});
  const entries = Object.entries(counts).sort((a, b) => b[1] - a[1]);
  return entries;
}

function buildCardMarkup(list) {
  const items = list.map(([word, count]) => {
    return `<div class="doc-card"><div class="doc-card-word">${escapeText(word)}</div><div class="doc-card-count">${count}</div></div>`;
  });
  return items.join('');
}

function buildEmptyState() {
  return `<div class="doc-empty">${escapeText(t('doc.no_words'))}</div>`;
}

function escapeText(value) {
  const map = { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' };
  const safe = String(value || '');
  return safe.replace(/[&<>"']/g, (char) => map[char]);
}

function handleDocClear() {
  if (!docState.elements.input) {
    return;
  }
  docState.elements.input.value = '';
  applyTranslation('');
  renderCards({ words: [] });
  setDocStatus(t('doc.status_idle'));
}

function resolveErrorMessage(error) {
  if (!error || !error.message) {
    return t('doc.status_error');
  }
  if (error.message === 'doc.auth_required') {
    return t('doc.auth_required');
  }
  if (error.message === 'doc.status_error') {
    return t('doc.status_error');
  }
  if (error.message === 'doc.status_success') {
    return t('doc.status_success');
  }
  return t('doc.status_error');
}

