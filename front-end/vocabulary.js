import { getBase } from './utils.js';
import { getAuthToken } from './auth.js';

let userVocab = new Set();
let analyzedWords = [];

export async function loadVocab() {
  const base = getBase();
  const token = getAuthToken();
  const headers = {};
  if (token) {
    headers['Authorization'] = `Bearer ${token}`;
  }
  const r = await fetch(base + '/vocab/list', { headers });
  const j = await r.json();
  const items = Array.isArray(j.items) ? j.items : [];
  userVocab.clear();
  items.forEach(item => {
    if (item.base && item.base.length > 0) {
      userVocab.add(item.base);
    }
  });
  return userVocab.size;
}


export async function analyzeBaseForms(text) {
  if (!text) return [];
  const base = getBase();
  const token = getAuthToken();
  const headers = { 'Content-Type': 'application/json' };
  if (token) {
    headers['Authorization'] = `Bearer ${token}`;
  }
  const r = await fetch(base + '/analyze', {
    method: 'POST',
    headers,
    body: JSON.stringify({ text })
  });
  const j = await r.json();
  analyzedWords = (j.words || []).map(w => w.word || '');
  return analyzedWords;
}

export function getCoverage(text) {
  const words = analyzedWords.length > 0 ? analyzedWords : (text.match(/\S+/g) || []);
  const unique = new Set(words);
  const known = [...unique].filter(w => userVocab.has(w));
  const unknown = [...unique].filter(w => !userVocab.has(w));
  const pct = unique.size > 0 ? Math.round(known.length * 100 / unique.size) : 0;
  return { pct, known: known.length, total: unique.size, unknown };
}

function countWords() {
  const counts = {};
  analyzedWords.forEach(w => {
    counts[w] = (counts[w] || 0) + 1;
  });
  return counts;
}

export function getKnownWordsWithCounts() {
  if (!analyzedWords || analyzedWords.length === 0) return [];
  const counts = countWords();
  const known = Object.keys(counts).filter(w => userVocab.has(w));
  const sorted = known.sort((a, b) => counts[b] - counts[a]);
  return sorted.map(w => ({ word: w, count: counts[w] }));
}