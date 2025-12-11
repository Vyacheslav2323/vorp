import { getBase } from './utils.js';
import { getAuthToken, isAuthenticated } from './auth.js';
import { loadTemplateIntoContainer } from './template-loader.js';
import { t, translatePage } from './translations.js';

const RETENTION_LIMIT = 0.85;
let vocabItems = [];
let currentIndex = 0;
let isFlipped = false;
let card = null;
let cardWord = null;
let cardTranslation = null;
let finishedForToday = false;

export async function initLearnPage() {
  await new Promise(resolve => setTimeout(resolve, 100));
  translatePage();
  if (!isAuthenticated()) {
    console.error('User not authenticated');
    vocabItems = [];
    setupCard();
    bindEvents();
    if (cardWord) {
      cardWord.textContent = t('learn.login_required');
    }
    return;
  }
  await loadVocab();
  setupCard();
  if (!card || !cardWord || !cardTranslation) {
    console.error('Learn page elements not found');
    return;
  }
  bindEvents();
  showNextCard();
}

async function loadVocab() {
  const base = getBase();
  const token = getAuthToken();
  const headers = { 'Authorization': token ? ('Bearer ' + token) : '' };
  try {
    const r = await fetch(base + '/vocab/list', { headers });
    const j = await r.json();
    if (!r.ok) {
      console.error('Failed to load vocab:', r.status, j.error || 'Unknown error');
      if (r.status === 401) {
        console.error('Authentication failed. Please log in again.');
      }
      vocabItems = [];
      finishedForToday = false;
      return;
    }
    const rows = Array.isArray(j.items) ? j.items : [];
    const filtered = filterByRetention(rows);
    finishedForToday = filtered.length === 0 && rows.length > 0;
    vocabItems = sortByRetention(filtered);
    currentIndex = 0;
  } catch (e) {
    console.error('Error loading vocab:', e);
    vocabItems = [];
    finishedForToday = false;
  }
}

function setupCard() {
  card = document.getElementById('card');
  cardWord = document.getElementById('cardWord');
  cardTranslation = document.getElementById('cardTranslation');
}

function bindEvents() {
  if (!card) return;
  
  let startX = 0;
  let startY = 0;
  let isDragging = false;
  let hasMoved = false;
  let touchStartTime = 0;
  
  const handleTouchStart = (e) => {
    if (!isFlipped) {
      touchStartTime = Date.now();
      return;
    }
    startX = e.touches[0].clientX;
    startY = e.touches[0].clientY;
    isDragging = true;
    hasMoved = false;
  };
  
  const handleTouchMove = (e) => {
    if (!isDragging || !isFlipped) return;
    const currentX = e.touches[0].clientX;
    const currentY = e.touches[0].clientY;
    const deltaX = currentX - startX;
    const deltaY = currentY - startY;
    
    if (Math.abs(deltaX) > Math.abs(deltaY) && Math.abs(deltaX) > 5) {
      e.preventDefault();
      e.stopPropagation();
      hasMoved = true;
      card.style.transform = `translateX(${deltaX}px) rotate(${deltaX * 0.1}deg)`;
      card.style.opacity = Math.max(0.5, 1 - Math.abs(deltaX) / 300);
    }
  };
  
  const handleTouchEnd = (e) => {
    if (!isFlipped) {
      const touchDuration = Date.now() - touchStartTime;
      if (touchDuration < 300 && !hasMoved) {
        flipCard();
      }
      return;
    }
    
    if (!isDragging) return;
    isDragging = false;
    
    const deltaX = e.changedTouches[0].clientX - startX;
    
    if (Math.abs(deltaX) > 100 && hasMoved) {
      if (deltaX > 0) {
        handleSwipe('right');
      } else {
        handleSwipe('left');
      }
    } else {
      resetCardPosition();
    }
    hasMoved = false;
  };
  
  const handleTouchCancel = () => {
    if (isDragging) {
      isDragging = false;
      resetCardPosition();
      hasMoved = false;
    }
  };
  
  card.addEventListener('touchstart', handleTouchStart, { passive: false });
  card.addEventListener('touchmove', handleTouchMove, { passive: false });
  card.addEventListener('touchend', handleTouchEnd, { passive: true });
  card.addEventListener('touchcancel', handleTouchCancel, { passive: true });
  
  card.addEventListener('click', (e) => {
    if (hasMoved || isDragging) {
      e.preventDefault();
      e.stopPropagation();
      hasMoved = false;
      return;
    }
    if (!isFlipped) {
      flipCard();
    }
  });
  
  card.addEventListener('mousedown', (e) => {
    if (!isFlipped) return;
    startX = e.clientX;
    startY = e.clientY;
    isDragging = true;
    hasMoved = false;
    card.style.cursor = 'grabbing';
  });
  
  card.addEventListener('mousemove', (e) => {
    if (!isDragging || !isFlipped) return;
    const deltaX = e.clientX - startX;
    const deltaY = e.clientY - startY;
    
    if (Math.abs(deltaX) > 5 || Math.abs(deltaY) > 5) {
      hasMoved = true;
    }
    
    if (Math.abs(deltaX) > Math.abs(deltaY)) {
      card.style.transform = `translateX(${deltaX}px) rotate(${deltaX * 0.1}deg)`;
      card.style.opacity = Math.max(0.5, 1 - Math.abs(deltaX) / 300);
    }
  });
  
  card.addEventListener('mouseup', (e) => {
    if (!isDragging || !isFlipped) return;
    isDragging = false;
    card.style.cursor = 'pointer';
    const deltaX = e.clientX - startX;
    
    if (Math.abs(deltaX) > 100 && hasMoved) {
      if (deltaX > 0) {
        handleSwipe('right');
      } else {
        handleSwipe('left');
      }
    } else {
      resetCardPosition();
    }
    hasMoved = false;
  });
  
  card.addEventListener('mouseleave', () => {
    if (isDragging) {
      isDragging = false;
      card.style.cursor = 'pointer';
      resetCardPosition();
      hasMoved = false;
    }
  });
}

function retentionValue(row) {
  const v = Number(row?.retention);
  return Number.isFinite(v) ? v : 0;
}

function sortByRetention(list) {
  return [...list].sort((a, b) => retentionValue(a) - retentionValue(b));
}

function filterByRetention(list) {
  return list.filter(item => retentionValue(item) < RETENTION_LIMIT);
}

function flipCard() {
  if (isFlipped) return;
  isFlipped = true;
  cardTranslation.classList.remove('hidden');
}

function resetCardPosition() {
  if (!card) return;
  card.style.transform = '';
  card.style.opacity = '1';
  card.style.transition = 'transform 0.3s ease, opacity 0.3s ease';
  setTimeout(() => {
    if (card) {
      card.style.transition = '';
    }
  }, 300);
}

function showNextCard() {
  if (!card || !cardWord || !cardTranslation) {
    console.error('Card elements not initialized');
    return;
  }
  if (finishedForToday) {
    cardWord.textContent = t('learn.done');
    cardTranslation.textContent = '';
    cardTranslation.classList.add('hidden');
    return;
  }
  if (vocabItems.length === 0) {
    cardWord.textContent = t('learn.no_items');
    cardTranslation.textContent = '';
    cardTranslation.classList.add('hidden');
    return;
  }
  if (currentIndex >= vocabItems.length) {
    finishedForToday = true;
    cardWord.textContent = t('learn.done');
    cardTranslation.textContent = '';
    cardTranslation.classList.add('hidden');
    return;
  }
  const item = vocabItems[currentIndex];
  isFlipped = false;
  resetCardPosition();
  
  cardWord.textContent = item.base || '';
  cardTranslation.textContent = item.translation || 'No translation';
  cardTranslation.classList.add('hidden');
  
  if (item.audio_path) {
    playAudio(item.audio_path);
  }
}

function playAudio(audioPath) {
  const base = getBase();
  const audio = new Audio(`${base}/${audioPath}`);
  audio.play().catch(e => {
    console.error('Audio play failed:', e);
    console.error('Audio path:', audioPath);
  });
}

async function handleSwipe(direction) {
  if (vocabItems.length === 0) return;
  
  const item = vocabItems[currentIndex];
  const base = getBase();
  const token = getAuthToken();
  
  if (direction === 'right') {
    await recordRemember(base, token, item.base, item.pos);
  } else {
    await recordDontRemember(base, token, item.base, item.pos);
  }
  
  card.style.transition = 'transform 0.3s, opacity 0.3s';
  card.style.transform = direction === 'right' 
    ? 'translateX(1000px) rotate(30deg)' 
    : 'translateX(-1000px) rotate(-30deg)';
  card.style.opacity = '0';
  
  setTimeout(() => {
    currentIndex++;
    if (currentIndex >= vocabItems.length) {
      currentIndex = vocabItems.length;
      finishedForToday = true;
    }
    card.style.transition = '';
    showNextCard();
  }, 300);
}

async function recordRemember(base, token, wordBase, pos) {
  const headers = { 'Content-Type': 'application/json' };
  if (token) {
    headers['Authorization'] = `Bearer ${token}`;
  }
  await fetch(base + '/learn/remember', {
    method: 'POST',
    headers,
    body: JSON.stringify({ base: wordBase, pos })
  });
}

async function recordDontRemember(base, token, wordBase, pos) {
  const headers = { 'Content-Type': 'application/json' };
  if (token) {
    headers['Authorization'] = `Bearer ${token}`;
  }
  await fetch(base + '/learn/dont-remember', {
    method: 'POST',
    headers,
    body: JSON.stringify({ base: wordBase, pos })
  });
}

