import { getBase } from './utils.js';
import { getAuthToken, logout, isAuthenticated } from './auth.js';
import { t } from './translations.js';

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
  renderChart(state.items);
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
  const freq = escapeHtml((r.frequency ?? 0).toString());
  const retention = escapeHtml(formatRetention(r.retention));
  return `<div class="vocab-row"><span class="v-base">${base}</span><span class="v-freq">${freq}</span><span class="v-ret">${retention}</span><span class="v-tr">${tr}</span></div>`;
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

function formatRetention(value) {
  const v = Number(value);
  if (!Number.isFinite(v) || v <= 0) {
    return '0%';
  }
  if (v >= 0.9995) {
    return '100%';
  }
  const pct = (v * 100).toFixed(1);
  return `${pct}%`;
}

function renderChart(rows) {
  const nodes = queryChartNodes();
  if (!nodes.canvas || !nodes.total) {
    return;
  }
  const series = buildSeries(rows);
  setChartSummary({ nodes, series });
  nodes.canvas.innerHTML = series.length ? buildChartSVG(series) : buildChartEmpty();
}

function queryChartNodes() {
  return {
    canvas: document.getElementById('vocabChart'),
    total: document.getElementById('vocabChartTotal'),
    start: document.getElementById('vocabChartStart'),
    end: document.getElementById('vocabChartEnd')
  };
}

function setChartSummary(arg) {
  const { nodes, series } = arg;
  const lastValue = series.length ? series[series.length - 1].value : 0;
  const firstDate = series.length ? series[0].date : '';
  const lastDate = series.length ? series[series.length - 1].date : '';
  nodes.total.textContent = lastValue.toString();
  if (nodes.start) {
    nodes.start.textContent = firstDate;
  }
  if (nodes.end) {
    nodes.end.textContent = lastDate;
  }
}

function buildSeries(rows) {
  const counts = groupCounts(rows);
  const dates = sortKeys(counts);
  let total = 0;
  return dates.map(date => {
    total += counts[date];
    return { date, value: total };
  });
}

function groupCounts(rows) {
  return rows.reduce((acc, item) => {
    const key = getDateKey(item);
    if (!key) {
      return acc;
    }
    acc[key] = (acc[key] || 0) + 1;
    return acc;
  }, {});
}

function sortKeys(counts) {
  const keys = Object.keys(counts);
  return keys.sort();
}

function getDateKey(row) {
  const source = row.last_seen || row.last_added || '';
  if (!source) {
    return '';
  }
  return source.slice(0, 10);
}

function buildChartSVG(series) {
  const points = buildPoints(series);
  const area = `${points} 100,40 0,40`;
  return `<svg viewBox="0 0 100 40" preserveAspectRatio="none" class="chart-svg"><polygon class="chart-fill" points="${area}"></polygon><polyline class="chart-line" points="${points}"></polyline></svg>`;
}

function buildPoints(series) {
  if (!series.length) {
    return '';
  }
  const maxValue = series[series.length - 1].value || 1;
  const denom = Math.max(series.length - 1, 1);
  return series.map((entry, index) => {
    const x = (index / denom) * 100;
    const y = 38 - (entry.value / maxValue) * 30;
    return `${x.toFixed(2)},${y.toFixed(2)}`;
  }).join(' ');
}

function buildChartEmpty() {
  const text = escapeHtml(t('vocab.chart_empty'));
  return `<div class="vocab-chart-empty">${text}</div>`;
}


