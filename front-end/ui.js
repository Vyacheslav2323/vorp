export function updateTranscript(transcriptEl, final, interim) {
  transcriptEl.innerHTML = '';
  
  if (final) {
    const finalSpan = createFinalSpan(final);
    transcriptEl.appendChild(finalSpan);
  }
  
  if (interim) {
    const interimSpan = createInterimSpan(interim);
    transcriptEl.appendChild(interimSpan);
  }
  
  transcriptEl.scrollTop = transcriptEl.scrollHeight;
}

function createFinalSpan(text) {
  const span = document.createElement('span');
  span.className = 'final';
  span.textContent = text;
  return span;
}

function createInterimSpan(text) {
  const span = document.createElement('span');
  span.className = 'interim';
  span.textContent = text;
  return span;
}

export function updateCoverage(els, coverage) {
  if (!coverage) {
    els.coveragePercent.textContent = '-';
    els.knownCount.textContent = '0';
    els.totalCount.textContent = '0';
    els.unknownWords.textContent = 'No unknown words yet';
    return;
  }
  els.coveragePercent.textContent = coverage.pct + '%';
  els.knownCount.textContent = coverage.known;
  els.totalCount.textContent = coverage.total;
  els.unknownWords.textContent = coverage.unknown.length > 0 ? 
    coverage.unknown.join(', ') : 'All words known!';
}

export function updateKnownWords(knownWordsEl, knownWithCounts) {
  if (!knownWithCounts || knownWithCounts.length === 0) {
    knownWordsEl.textContent = 'No known words yet';
    return;
  }
  const display = knownWithCounts.map(item => `${item.word} (${item.count})`).join(', ');
  knownWordsEl.textContent = display;
}

export function updateTranslation(translationEl, text) {
  translationEl.textContent = text;
}

export function setTranslateStatus(translateStatusEl, text) {
  translateStatusEl.textContent = text;
}

export function showError(statusEl, startBtn) {
  statusEl.textContent = '❌ Your browser doesn\'t support Speech Recognition';
  statusEl.style.color = '#e74c3c';
  startBtn.disabled = true;
}

export function setStatus(statusEl, text, className) {
  statusEl.textContent = text;
  statusEl.className = className || 'status';
}

