import { getBase } from './utils.js';

const TOKEN_KEY = 'jwt_token';
const USER_KEY = 'current_user';

function safeGetItem(key) {
  try {
    return localStorage.getItem(key);
  } catch (e) {
    console.warn('localStorage not available:', e);
    return null;
  }
}

function safeSetItem(key, value) {
  try {
    localStorage.setItem(key, value);
    return true;
  } catch (e) {
    console.warn('localStorage set failed:', e);
    return false;
  }
}

function safeRemoveItem(key) {
  try {
    localStorage.removeItem(key);
  } catch (e) {
    console.warn('localStorage remove failed:', e);
  }
}

let authToken = safeGetItem(TOKEN_KEY);
let currentUser = null;
try {
  const userStr = safeGetItem(USER_KEY);
  if (userStr) {
    currentUser = JSON.parse(userStr);
  }
} catch (e) {
  console.warn('Failed to parse user from localStorage:', e);
  safeRemoveItem(USER_KEY);
}

export function getAuthToken() {
  return authToken;
}

export function getCurrentUser() {
  return currentUser;
}

export function setAuthToken(token) {
  authToken = token;
  if (token) {
    safeSetItem(TOKEN_KEY, token);
  } else {
    safeRemoveItem(TOKEN_KEY);
  }
}

export function setCurrentUser(user) {
  currentUser = user;
  if (user) {
    try {
      safeSetItem(USER_KEY, JSON.stringify(user));
    } catch (e) {
      console.error('Failed to save user to localStorage:', e);
    }
  } else {
    safeRemoveItem(USER_KEY);
  }
}

export async function register(username, email, password, nativeLanguage, targetLanguage) {
  const base = getBase();
  try {
    const response = await fetch(base + '/register', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ username, email, password, native_language: nativeLanguage, target_language: targetLanguage })
    });
    
    if (!response.ok) {
      const errorText = await response.text();
      let errorData;
      try {
        errorData = JSON.parse(errorText);
      } catch {
        errorData = { success: false, error: `HTTP ${response.status}: ${errorText}` };
      }
      return errorData;
    }
    
    const result = await response.json();
    if (result.success) {
      setAuthToken(result.token);
      setCurrentUser(result.user);
    }
    return result;
  } catch (e) {
    console.error('Register error:', e);
    return { success: false, error: e.message || 'network_error' };
  }
}

export async function login(username, password) {
  const base = getBase();
  const url = base + '/login';
  
  console.log('Login request URL:', url);
  console.log('Login request base:', base);
  
  try {
    const requestBody = JSON.stringify({ username, password });
    console.log('Sending login request...');
    
    const response = await fetch(url, {
      method: 'POST',
      headers: { 
        'Content-Type': 'application/json',
        'Accept': 'application/json'
      },
      body: requestBody,
      credentials: 'omit',
      cache: 'no-cache'
    });
    
    console.log('Login response received:', response.status, response.statusText);
    
    if (!response) {
      return { success: false, error: 'No response from server' };
    }
    
    let result;
    const contentType = response.headers.get('content-type') || '';
    
    if (contentType.includes('application/json')) {
      try {
        result = await response.json();
      } catch (jsonError) {
        const text = await response.text();
        return { success: false, error: `Invalid JSON response: ${text.substring(0, 100)}` };
      }
    } else {
      const text = await response.text();
      return { success: false, error: `Server error (${response.status}): ${text.substring(0, 100)}` };
    }
    
    if (!response.ok) {
      return { success: false, error: result.error || `HTTP ${response.status}` };
    }
    
    if (result && result.success) {
      if (result.token) {
        setAuthToken(result.token);
      }
      if (result.user) {
        setCurrentUser(result.user);
      }
    }
    
    return result || { success: false, error: 'Empty response' };
  } catch (e) {
    const errorMsg = e.message || e.toString() || 'network_error';
    return { success: false, error: `Network error: ${errorMsg}` };
  }
}

export function logout() {
  setAuthToken(null);
  setCurrentUser(null);
}

export function isAuthenticated() {
  return !!authToken && !!currentUser;
}
