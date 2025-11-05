import { getBase } from './utils.js';

async function tryMyMemory(p) {
  const u = `https://api.mymemory.translated.net/get?q=${encodeURIComponent(p.text)}&langpair=${p.source}|${p.target}`;
  const r = await fetch(u);
  const j = await r.json();
  if (j && j.responseData && j.responseData.translatedText) {
    return { text: j.responseData.translatedText, status: `HTTP ${r.status}` };
  }
  return null;
}

async function tryBackend(p) {
  const base = getBase();
  const r = await fetch(base + '/translate', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ text: p.text, target: p.target })
  });
  const j = await r.json();
  return { text: j && j.text ? j.text : '', status: `HTTP ${r.status}` };
}

export async function translate(text, sourceLang, targetLang) {
  if (!text) return '';
  const first = await tryMyMemory({ text, source: sourceLang, target: targetLang });
  if (first) return first;
  return await tryBackend({ text, target: targetLang });
}

