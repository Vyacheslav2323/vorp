import { getBase } from './utils.js';

async function translateBackend(p) {
  const base = getBase();
  const r = await fetch(base + '/translate', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ text: p.text, source: p.source, target: p.target })
  });
  const j = await r.json();
  return { text: j && j.text ? j.text : '', status: `HTTP ${r.status}` };
}

export async function translate(text, sourceLang, targetLang) {
  if (!text) return '';
  return await translateBackend({ text, source: sourceLang, target: targetLang });
}

