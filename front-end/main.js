import { isAuthenticated } from './auth.js';
import { showLoginForm, showMainApp, updateNavbar } from './auth-ui.js';
import { initMainApp } from './app-init.js';
import { translatePage } from './translations.js';

async function init() {
  updateNavbar();
  translatePage();
  const authenticated = isAuthenticated();
  if (authenticated) {
    await showMainApp();
    initMainApp();
  } else {
    await showLoginForm();
  }
}

init();