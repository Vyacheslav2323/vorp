import { updateNavbar } from './auth-ui.js';
import { initVocabPage } from './vocab.js';
import { isAuthenticated } from './auth.js';
import { translatePage } from './translations.js';

async function init() {
  if (!isAuthenticated()) {
    window.location.href = 'base.html';
    return;
  }
  updateNavbar();
  translatePage();
  await initVocabPage();
}

init();

