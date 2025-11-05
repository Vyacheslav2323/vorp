import { getBase } from './utils.js';

let adminAuth = { username: null, password: null };

const base = getBase();

function showLogin() {
  document.getElementById('loginForm').style.display = 'block';
  document.getElementById('adminPanel').style.display = 'none';
  document.getElementById('logoutBtn').style.display = 'none';
}

function showAdminPanel() {
  document.getElementById('loginForm').style.display = 'none';
  document.getElementById('adminPanel').style.display = 'block';
  document.getElementById('logoutBtn').style.display = 'block';
  loadUsers();
  loadVocab();
}

async function login() {
  const username = document.getElementById('adminUsername').value;
  const password = document.getElementById('adminPassword').value;
  const statusEl = document.getElementById('loginStatus');
  
  try {
    const response = await fetch(base + '/admin/login', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ username, password })
    });
    
    const result = await response.json();
    
    if (result.success) {
      adminAuth = { username, password };
      statusEl.textContent = 'Login successful!';
      statusEl.className = 'success';
      showAdminPanel();
    } else {
      statusEl.textContent = 'Error: ' + (result.error || 'Invalid credentials');
      statusEl.className = 'error';
    }
  } catch (e) {
    statusEl.textContent = 'Error: ' + e.message;
    statusEl.className = 'error';
  }
}

async function loadUsers() {
  try {
    const response = await fetch(base + '/admin/users', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(adminAuth)
    });
    
    const result = await response.json();
    
    if (result.success) {
      renderUsers(result.users || []);
    } else {
      console.error('Failed to load users:', result.error);
    }
  } catch (e) {
    console.error('Error loading users:', e);
  }
}

function renderUsers(users) {
  const tbody = document.getElementById('usersTableBody');
  tbody.innerHTML = users.map(user => `
    <tr>
      <td>${user.id}</td>
      <td>${escapeHtml(user.username)}</td>
      <td>${escapeHtml(user.email)}</td>
      <td>${escapeHtml(user.native_language || '')}</td>
      <td>${escapeHtml(user.target_language || '')}</td>
      <td>${escapeHtml(user.created_at || '')}</td>
      <td>
        <button class="btn-delete" onclick="deleteUser(${user.id})">Delete</button>
      </td>
    </tr>
  `).join('');
}

async function deleteUser(userId) {
  if (!confirm('Are you sure you want to delete this user?')) return;
  
  try {
    const response = await fetch(base + '/admin/users/delete', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        admin_username: adminAuth.username,
        admin_password: adminAuth.password,
        user_id: userId
      })
    });
    
    const result = await response.json();
    
    if (result.success) {
      loadUsers();
    } else {
      alert('Error: ' + (result.error || 'Failed to delete user'));
    }
  } catch (e) {
    alert('Error: ' + e.message);
  }
}

function showAddUserForm() {
  document.getElementById('addUserForm').style.display = 'block';
}

function hideAddUserForm() {
  document.getElementById('addUserForm').style.display = 'none';
  document.getElementById('newUsername').value = '';
  document.getElementById('newEmail').value = '';
  document.getElementById('newPassword').value = '';
  document.getElementById('newNativeLang').value = 'en';
  document.getElementById('addUserStatus').textContent = '';
}

async function addUser() {
  const username = document.getElementById('newUsername').value;
  const email = document.getElementById('newEmail').value;
  const password = document.getElementById('newPassword').value;
  const nativeLang = document.getElementById('newNativeLang').value;
  const statusEl = document.getElementById('addUserStatus');
  
  if (!username || !email || !password) {
    statusEl.textContent = 'Please fill in all fields';
    statusEl.className = 'error';
    return;
  }
  
  try {
    const response = await fetch(base + '/admin/users/add', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        admin_username: adminAuth.username,
        admin_password: adminAuth.password,
        username,
        email,
        password,
        native_language: nativeLang,
        target_language: 'ko'
      })
    });
    
    const result = await response.json();
    
    if (result.success) {
      statusEl.textContent = 'User created successfully!';
      statusEl.className = 'success';
      hideAddUserForm();
      loadUsers();
    } else {
      statusEl.textContent = 'Error: ' + (result.error || 'Failed to create user');
      statusEl.className = 'error';
    }
  } catch (e) {
    statusEl.textContent = 'Error: ' + e.message;
    statusEl.className = 'error';
  }
}

async function loadVocab() {
  try {
    const response = await fetch(base + '/admin/vocab', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(adminAuth)
    });
    
    const result = await response.json();
    
    if (result.success) {
      renderVocab(result.vocab || []);
    } else {
      console.error('Failed to load vocab:', result.error);
    }
  } catch (e) {
    console.error('Error loading vocab:', e);
  }
}

function renderVocab(vocab) {
  const tbody = document.getElementById('vocabTableBody');
  tbody.innerHTML = vocab.map(item => `
    <tr>
      <td>${escapeHtml(item.base || '')}</td>
      <td>${escapeHtml(item.pos || '')}</td>
      <td><input type="text" value="${escapeHtml(item.translation_en || '')}" 
          onchange="updateTranslation(${JSON.stringify(item.base || '')}, ${JSON.stringify(item.pos || '')}, 'en', this.value)" 
          style="width: 100%; padding: 5px;"></td>
      <td><input type="text" value="${escapeHtml(item.translation_ru || '')}" 
          onchange="updateTranslation(${JSON.stringify(item.base || '')}, ${JSON.stringify(item.pos || '')}, 'ru', this.value)" 
          style="width: 100%; padding: 5px;"></td>
      <td><input type="text" value="${escapeHtml(item.translation_zh || '')}" 
          onchange="updateTranslation(${JSON.stringify(item.base || '')}, ${JSON.stringify(item.pos || '')}, 'zh', this.value)" 
          style="width: 100%; padding: 5px;"></td>
      <td><input type="text" value="${escapeHtml(item.translation_vi || '')}" 
          onchange="updateTranslation(${JSON.stringify(item.base || '')}, ${JSON.stringify(item.pos || '')}, 'vi', this.value)" 
          style="width: 100%; padding: 5px;"></td>
      <td>${item.count || 0}</td>
      <td>
        <button class="btn-delete" onclick="deleteVocab(${JSON.stringify(item.base || '')}, ${JSON.stringify(item.pos || '')})">Delete</button>
      </td>
    </tr>
  `).join('');
}

async function updateTranslation(wordBase, pos, targetLang, translation) {
  try {
    const response = await fetch(base + '/admin/translations/update', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        admin_username: adminAuth.username,
        admin_password: adminAuth.password,
        base: wordBase,
        pos,
        translation,
        target_lang: targetLang
      })
    });
    
    const result = await response.json();
    
    if (!result.success) {
      alert('Error updating translation: ' + (result.error || 'Unknown error'));
    }
  } catch (e) {
    alert('Error: ' + e.message);
  }
}

async function deleteVocab(wordBase, pos) {
  if (!confirm('Are you sure you want to delete this vocabulary item?')) return;
  
  try {
    const response = await fetch(base + '/admin/vocab/delete', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        admin_username: adminAuth.username,
        admin_password: adminAuth.password,
        base: wordBase,
        pos
      })
    });
    
    const result = await response.json();
    
    if (result.success) {
      loadVocab();
    } else {
      alert('Error: ' + (result.error || 'Failed to delete vocab'));
    }
  } catch (e) {
    alert('Error: ' + e.message);
  }
}

function escapeHtml(text) {
  const div = document.createElement('div');
  div.textContent = text;
  return div.innerHTML;
}

window.deleteUser = deleteUser;
window.deleteVocab = deleteVocab;
window.updateTranslation = updateTranslation;
window.showAddUserForm = showAddUserForm;
window.hideAddUserForm = hideAddUserForm;
window.addUser = addUser;

document.getElementById('loginBtn').addEventListener('click', login);
document.getElementById('adminPassword').addEventListener('keypress', (e) => {
  if (e.key === 'Enter') login();
});
document.getElementById('logoutBtn').addEventListener('click', () => {
  adminAuth = { username: null, password: null };
  showLogin();
});

