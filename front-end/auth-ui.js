import { updateCoverage, updateKnownWords, updateTranslation, setTranslateStatus, showError, setStatus } from './ui.js';
import { register, login, logout, isAuthenticated, getCurrentUser } from './auth.js';
import { loadTemplateIntoContainer } from './template-loader.js';
import { initVocabPage } from './vocab.js';
import { initLearnPage } from './learn.js';
import { initMainApp } from './app-init.js';
import { t, translatePage } from './translations.js';

export function updateNavbar() {
  const navbarAuth = document.getElementById('navbarAuth');
  const user = getCurrentUser();
  
  if (user) {
    navbarAuth.innerHTML = `
      <div class="user-info-nav">
        <span class="user-name">${t('nav.welcome', { username: user.username })}</span>
        <button class="nav-btn" id="navVocabBtn">${t('nav.vocab')}</button>
        <button class="nav-btn" id="navLearnBtn">${t('nav.learn')}</button>
        <button class="logout-btn-nav" id="navLogoutBtn">${t('nav.logout')}</button>
      </div>
    `;
    
    const logoutBtn = document.getElementById('navLogoutBtn');
    logoutBtn.addEventListener('click', async () => {
      logout();
      updateNavbar();
      await showLoginForm();
    });
    const vocabBtn = document.getElementById('navVocabBtn');
    vocabBtn.addEventListener('click', () => {
      window.location.href = 'vocab.html';
    });
    const learnBtn = document.getElementById('navLearnBtn');
    learnBtn.addEventListener('click', async () => {
      const container = document.getElementById('mainContainer');
      if (!container) {
        window.location.href = 'base.html';
        return;
      }
      try {
        await loadTemplateIntoContainer('mainContainer', 'learn');
        await initLearnPage();
      } catch (error) {
        console.error('Error loading learn page:', error);
        if (container) {
          container.innerHTML = `<div class="error">Error loading learn page: ${error.message}</div>`;
        }
      }
    });
  } else {
    const selectedLang = localStorage.getItem('selectedLanguage') || 'en';
    navbarAuth.innerHTML = `
      <div class="language-selector">
        <select id="languageSelect" class="language-select">
          <option value="en" ${selectedLang === 'en' ? 'selected' : ''}>🇺🇸 English</option>
          <option value="ru" ${selectedLang === 'ru' ? 'selected' : ''}>🇷🇺 Русский</option>
          <option value="zh" ${selectedLang === 'zh' ? 'selected' : ''}>🇨🇳 中文</option>
          <option value="vi" ${selectedLang === 'vi' ? 'selected' : ''}>🇻🇳 Tiếng Việt</option>
        </select>
      </div>
      <button class="auth-btn-nav login" id="navLoginBtn">${t('nav.login')}</button>
      <button class="auth-btn-nav register" id="navRegisterBtn">${t('nav.register')}</button>
    `;
    
    const languageSelect = document.getElementById('languageSelect');
    if (languageSelect) {
      languageSelect.addEventListener('change', (e) => {
        const lang = e.target.value;
        localStorage.setItem('selectedLanguage', lang);
        translatePage();
        const nativeLangSelect = document.getElementById('registerNativeLang');
        if (nativeLangSelect) {
          nativeLangSelect.value = lang;
        }
        updateNavbar();
      });
    }
    
    const loginBtn = document.getElementById('navLoginBtn');
    const registerBtn = document.getElementById('navRegisterBtn');
    
    if (loginBtn) {
      loginBtn.addEventListener('click', async () => {
        await showLoginForm();
        const loginTab = document.getElementById('loginTab');
        if (loginTab) {
          loginTab.click();
        }
      });
    }
    
    if (registerBtn) {
      registerBtn.addEventListener('click', async () => {
        await showLoginForm();
        const registerTab = document.getElementById('registerTab');
        if (registerTab) {
          registerTab.click();
        }
      });
    }
  }
}

export async function showLoginForm() {
  await loadTemplateIntoContainer('mainContainer', 'auth');
  translatePage();
  setupAuthEvents();
}

export async function showMainApp() {
  await loadTemplateIntoContainer('mainContainer', 'main-app');
  translatePage();
}

function setupAuthEvents() {
  const loginTab = document.getElementById('loginTab');
  const registerTab = document.getElementById('registerTab');
  const loginForm = document.getElementById('loginForm');
  const registerForm = document.getElementById('registerForm');
  const loginBtn = document.getElementById('loginBtn');
  const registerBtn = document.getElementById('registerBtn');
  const nativeLangSelect = document.getElementById('registerNativeLang');
  const navbarLangSelect = document.getElementById('languageSelect');
  
  if (!loginBtn || !registerBtn) {
    setTimeout(setupAuthEvents, 100);
    return;
  }
  
  loginTab.addEventListener('click', () => {
    loginTab.classList.add('active');
    registerTab.classList.remove('active');
    loginForm.classList.remove('hidden');
    registerForm.classList.add('hidden');
  });
  
  registerTab.addEventListener('click', () => {
    registerTab.classList.add('active');
    loginTab.classList.remove('active');
    registerForm.classList.remove('hidden');
    loginForm.classList.add('hidden');
  });
  
  if (nativeLangSelect) {
    const selectedLang = localStorage.getItem('selectedLanguage') || 'en';
    nativeLangSelect.value = selectedLang;
    
    const updateSelectPlaceholder = () => {
      const placeholderOption = nativeLangSelect.querySelector('option[value=""]');
      if (placeholderOption) {
        placeholderOption.textContent = t('auth.select');
      }
    };
    
    updateSelectPlaceholder();
    
    nativeLangSelect.addEventListener('change', (e) => {
      const lang = e.target.value;
      localStorage.setItem('selectedLanguage', lang);
      const navbarLangSelect = document.getElementById('languageSelect');
      if (navbarLangSelect) {
        navbarLangSelect.value = lang;
      }
      translatePage();
      updateNavbar();
      updateSelectPlaceholder();
    });
  }
  
    const handleLogin = async (e) => {
      if (e) {
        e.preventDefault();
        e.stopPropagation();
      }
      
      const statusEl = document.getElementById('loginAuthStatus');
      if (!statusEl) return;
      
      const usernameEl = document.getElementById('loginUsername');
      const passwordEl = document.getElementById('loginPassword');
      
      if (!usernameEl || !passwordEl) {
        updateAuthStatus({ success: false, error: 'Form elements not found' }, 'login');
        return;
      }
      
      const username = usernameEl.value.trim();
      const password = passwordEl.value;
      
      if (!username || !password) {
        updateAuthStatus({ success: false, error: 'missing_fields' }, 'login');
        return;
      }
      
      loginBtn.disabled = true;
      updateAuthStatus({ success: false, error: 'Connecting...' }, 'login');
      
      try {
        const result = await login(username, password);
        
        console.log('Login result:', result);
        console.log('Result type:', typeof result);
        console.log('Result.success:', result?.success);
        console.log('Result keys:', result ? Object.keys(result) : 'null');
        
        if (result && result.success === true) {
          console.log('Login successful, redirecting...');
          updateAuthStatus({ success: true, error: '' }, 'login');
          await new Promise(resolve => setTimeout(resolve, 300));
          
          console.log('Updating navbar...');
          updateNavbar();
          
          console.log('Loading main app...');
          await showMainApp();
          
          console.log('Checking if main app loaded...');
          const container = document.getElementById('mainContainer');
          console.log('Container innerHTML length:', container?.innerHTML?.length || 0);
          console.log('Container has speakBtn:', !!document.getElementById('speakBtn'));
          
          await new Promise(resolve => setTimeout(resolve, 100));
          
          console.log('Initializing main app...');
          try {
            initMainApp();
            console.log('initMainApp completed');
          } catch (e) {
            console.error('initMainApp error:', e);
          }
          
          console.log('Redirect complete!');
        } else {
          console.log('Login failed, result:', result);
          updateAuthStatus(result || { success: false, error: 'Login failed' }, 'login');
        }
      } catch (e) {
        console.error('Login exception:', e);
        console.error('Stack:', e.stack);
        updateAuthStatus({ success: false, error: `Error: ${e.message || 'Unknown error'}` }, 'login');
      } finally {
        loginBtn.disabled = false;
      }
    };
    
    const directClick = (e) => {
      e.preventDefault();
      e.stopPropagation();
      handleLogin(e);
    };
    
    loginBtn.onclick = directClick;
    loginBtn.ontouchend = directClick;
    loginBtn.addEventListener('click', directClick, { passive: false });
    loginBtn.addEventListener('touchend', directClick, { passive: false });
    
    const loginFormEl = document.getElementById('loginForm');
    if (loginFormEl) {
      loginFormEl.onsubmit = (e) => {
        e.preventDefault();
        e.stopPropagation();
        handleLogin(e);
      };
      loginFormEl.addEventListener('submit', (e) => {
        e.preventDefault();
        e.stopPropagation();
        handleLogin(e);
      }, { passive: false });
    }
    
    const handleRegister = async (e) => {
      if (e) {
        e.preventDefault();
        e.stopPropagation();
      }
      
      const statusEl = document.getElementById('registerAuthStatus');
      if (!statusEl) {
        alert('Register status element not found!');
        return;
      }
      
      statusEl.style.display = 'block';
      statusEl.style.visibility = 'visible';
      statusEl.style.opacity = '1';
      
      const usernameEl = document.getElementById('registerUsername');
      const emailEl = document.getElementById('registerEmail');
      const passwordEl = document.getElementById('registerPassword');
      const nativeLangSelect = document.getElementById('registerNativeLang');
      
      if (!usernameEl || !emailEl || !passwordEl) {
        statusEl.textContent = 'Form elements not found. Please refresh the page.';
        statusEl.className = 'auth-status error';
        return;
      }
      
      const username = usernameEl.value.trim();
      const email = emailEl.value.trim();
      const password = passwordEl.value;
      const selectedLang = localStorage.getItem('selectedLanguage') || 'en';
      const nativeLang = nativeLangSelect?.value || selectedLang;
      const targetLang = 'ko';
      
      if (!username || !email || !password || !nativeLang) {
        updateAuthStatus({ success: false, error: 'missing_fields' }, 'register');
        statusEl.scrollIntoView({ behavior: 'smooth', block: 'center' });
        return;
      }
      
      updateAuthStatus({ success: false, error: 'Connecting...' }, 'register');
      registerBtn.disabled = true;
      const registerSpan = registerBtn.querySelector('span[data-i18n="auth.register"]');
      const originalText = registerSpan ? registerSpan.textContent : registerBtn.textContent;
      if (registerSpan) {
        registerSpan.textContent = 'Registering...';
      } else {
        registerBtn.textContent = 'Registering...';
      }
      
      try {
        updateAuthStatus({ success: false, error: 'Sending request...' }, 'register');
        const result = await register(username, email, password, nativeLang, targetLang);
        updateAuthStatus(result, 'register');
        if (result.success) {
          updateAuthStatus({ success: true, error: '' }, 'register');
          setTimeout(async () => {
            updateNavbar();
            await showMainApp();
            initMainApp();
          }, 500);
        } else {
          statusEl.scrollIntoView({ behavior: 'smooth', block: 'center' });
        }
      } catch (e) {
        const errorMsg = e.message || e.toString() || 'unknown_error';
        updateAuthStatus({ success: false, error: `Error: ${errorMsg}` }, 'register');
        statusEl.scrollIntoView({ behavior: 'smooth', block: 'center' });
      } finally {
        registerBtn.disabled = false;
        if (registerSpan) {
          registerSpan.textContent = originalText;
        } else {
          registerBtn.textContent = originalText;
        }
      }
    };
    
    registerBtn.onclick = handleRegister;
    registerBtn.ontouchend = handleRegister;
}

function updateAuthStatus(result, formType = 'login') {
  const statusId = formType === 'login' ? 'loginAuthStatus' : 'registerAuthStatus';
  const statusEl = document.getElementById(statusId);
  
  if (!statusEl) {
    console.error(`Status element not found: ${statusId}`);
    return;
  }
  
  statusEl.style.cssText = 'display: block !important; visibility: visible !important; opacity: 1 !important; position: relative; z-index: 1000;';
  
  if (result && result.success) {
    statusEl.textContent = 'Success! Logging you in...';
    statusEl.className = 'auth-status success';
    statusEl.style.background = '#d4edda';
    statusEl.style.color = '#155724';
    statusEl.style.border = '2px solid #c3e6cb';
  } else {
    const errorMsg = (result && result.error) || 'Error occurred';
    
    const errorMap = {
      'user_not_found': 'User not found',
      'invalid_password': 'Invalid password',
      'user_exists': 'Username already exists',
      'missing_fields': 'Please fill in all fields',
      'network_error': 'Network error. Please check your connection.',
      'db_connection_failed': 'Server error. Please try again later.',
      'invalid_json': 'Invalid request format',
      'unknown_error': 'An unexpected error occurred',
      'Connecting...': 'Connecting to server...',
      'Sending request...': 'Sending request to server...',
      'Connecting to server...': 'Connecting to server...'
    };
    
    const displayMsg = errorMap[errorMsg] || errorMsg;
    statusEl.textContent = displayMsg;
    statusEl.className = 'auth-status error';
    statusEl.style.background = '#f8d7da';
    statusEl.style.color = '#721c24';
    statusEl.style.border = '2px solid #f5c6cb';
    statusEl.style.fontWeight = '600';
    
    setTimeout(() => {
      statusEl.scrollIntoView({ behavior: 'smooth', block: 'center' });
    }, 50);
  }
}

