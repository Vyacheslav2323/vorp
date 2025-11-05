import { getBase } from './utils.js';
import { getAuthToken, logout, isAuthenticated } from './auth.js';

export async function initVocabPage() {
  if (!isAuthenticated()) {
    console.error('User not authenticated');
    state.items = [];
    bindSort();
    renderSorted();
    return;
  }
  
  const base = getBase();
  const token = getAuthToken();
  console.log('Loading vocab with token:', token ? 'present' : 'missing');
  try {
    const r = await fetch(base + '/vocab/list', { headers: { 'Authorization': token ? ('Bearer ' + token) : '' } });
    const j = await r.json();
    if (!r.ok) {
      console.error('Failed to load vocab:', r.status, j.error || 'Unknown error');
      if (r.status === 401) {
        console.error('Authentication failed. Token may be expired or invalid.');
        logout();
        window.location.reload();
      }
      state.items = [];
      bindSort();
      renderSorted();
      return;
    }
    state.items = Array.isArray(j.items) ? j.items : [];
    console.log('Loaded vocab items:', state.items.length);
    state.sortKey = 'base';
    state.sortDir = 'asc';
    bindSort();
    renderSorted();
  } catch (e) {
    console.error('Error loading vocab:', e);
    state.items = [];
    bindSort();
    renderSorted();
  }
}

const state = { items: [], sortKey: 'base', sortDir: 'asc' };

function bindSort() {
  const buttons = document.querySelectorAll('.v-sort');
  buttons.forEach(b => b.addEventListener('click', () => {
    const key = b.getAttribute('data-key');
    if (state.sortKey === key) {
      state.sortDir = state.sortDir === 'asc' ? 'desc' : 'asc';
    } else {
      state.sortKey = key;
      state.sortDir = key === 'base' ? 'asc' : 'desc';
    }
    renderSorted();
  }));
}

function renderSorted() {
  const items = [...state.items].sort(compare(state.sortKey, state.sortDir));
  render(items);
}

function render(items) {
  const el = document.getElementById('vocabList');
  if (!el) return;
  el.innerHTML = items.map(row => template(row)).join('');
}

function template(r) {
  const base = escapeHtml(r.base || '');
  const tr = escapeHtml(r.translation || '');
  return `<div class="vocab-row"><span class="v-base">${base}</span><span class="v-tr">${tr}</span></div>`;
}

function escapeHtml(s) {
  const m = { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' };
  return String(s).replace(/[&<>"']/g, c => m[c]);
}

function compare(key, dir) {
  return (a, b) => {
    const va = normalize(a[key]);
    const vb = normalize(b[key]);
    if (va < vb) return dir === 'asc' ? -1 : 1;
    if (va > vb) return dir === 'asc' ? 1 : -1;
    return 0;
  };
}

function normalize(v) {
  if (keyIsDate(v)) return Date.parse(v) || 0;
  if (typeof v === 'number') return v;
  const n = Number(v);
  if (!Number.isNaN(n)) return n;
  return String(v || '').toLowerCase();
}

function keyIsDate(v) {
  return typeof v === 'string' && v.length >= 10 && v.includes('-') && (v.includes('T') || v.includes(':'));
}


