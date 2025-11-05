const translations = {
  en: {
    'app.title': 'LexiPark',
    'vocab.title': 'Your Vocabulary',
    'vocab.word': 'Word',
    'vocab.translation': 'Translation',
    'nav.welcome': 'Welcome, {username}!',
    'nav.vocab': 'Vocab',
    'nav.learn': 'Learn',
    'nav.logout': 'Logout',
    'nav.login': 'Login',
    'nav.register': 'Register',
    'auth.login': 'Login',
    'auth.register': 'Register',
    'auth.username': 'Username',
    'auth.email': 'Email',
    'auth.password': 'Password',
    'auth.native_language': 'Native Language',
    'auth.select': 'Select...',
    'auth.title': 'Korean Live Transcription',
    'button.speak': 'Speak',
    'button.listen': 'Listen',
    'button.voice_translation': 'Voice Translation',
    'status.ready': 'Ready',
    'status.recording': 'Recording {language}...',
    'status.not_supported': 'Speech recognition not supported',
    'learn.title': 'Learning Mode',
    'learn.no_items': 'No vocabulary items',
    'learn.swipe_remember': 'Remember →',
    'learn.swipe_dont_remember': '← Don\'t Remember',
    'learn.loading': 'Loading...',
    'learn.translation': 'Translation',
    'learn.login_required': 'Please log in to use learning mode'
  },
  ru: {
    'app.title': 'Лексипарк',
    'vocab.title': 'Ваш словарь',
    'vocab.word': 'Слово',
    'vocab.translation': 'Перевод',
    'nav.welcome': 'Добро пожаловать, {username}!',
    'nav.vocab': 'Словарь',
    'nav.learn': 'Учить',
    'nav.logout': 'Выйти',
    'nav.login': 'Войти',
    'nav.register': 'Регистрация',
    'auth.login': 'Войти',
    'auth.register': 'Регистрация',
    'auth.username': 'Имя пользователя',
    'auth.email': 'Email',
    'auth.password': 'Пароль',
    'auth.native_language': 'Родной язык',
    'auth.select': 'Выбрать...',
    'auth.title': 'Корейская транскрипция в реальном времени',
    'button.speak': 'Говорить',
    'button.listen': 'Слушать',
    'button.voice_translation': 'Голосовой перевод',
    'status.ready': 'Готов',
    'status.recording': 'Запись {language}...',
    'status.not_supported': 'Распознавание речи не поддерживается',
    'learn.title': 'Режим обучения',
    'learn.no_items': 'Нет слов в словаре',
    'learn.swipe_remember': 'Помню →',
    'learn.swipe_dont_remember': '← Не помню',
    'learn.loading': 'Загрузка...',
    'learn.translation': 'Перевод',
    'learn.login_required': 'Пожалуйста, войдите, чтобы использовать режим обучения'
  },
  zh: {
    'app.title': '韩语实时转录',
    'vocab.title': '您的词汇',
    'vocab.word': '单词',
    'vocab.translation': '翻译',
    'nav.welcome': '欢迎，{username}！',
    'nav.vocab': '词汇',
    'nav.learn': '学习',
    'nav.logout': '登出',
    'nav.login': '登录',
    'nav.register': '注册',
    'auth.login': '登录',
    'auth.register': '注册',
    'auth.username': '用户名',
    'auth.email': '邮箱',
    'auth.password': '密码',
    'auth.native_language': '母语',
    'auth.select': '选择...',
    'auth.title': '韩语实时转录',
    'button.speak': '说话',
    'button.listen': '听',
    'button.voice_translation': '语音翻译',
    'status.ready': '就绪',
    'status.recording': '正在录制 {language}...',
    'status.not_supported': '不支持语音识别',
    'learn.title': '学习模式',
    'learn.no_items': '没有词汇',
    'learn.swipe_remember': '记住 →',
    'learn.swipe_dont_remember': '← 不记得',
    'learn.loading': '加载中...',
    'learn.translation': '翻译',
    'learn.login_required': '请登录以使用学习模式'
  },
  vi: {
    'app.title': 'Phiên âm tiếng Hàn trực tiếp',
    'vocab.title': 'Từ vựng của bạn',
    'vocab.word': 'Từ',
    'vocab.translation': 'Bản dịch',
    'nav.welcome': 'Chào mừng, {username}!',
    'nav.vocab': 'Từ vựng',
    'nav.learn': 'Học',
    'nav.logout': 'Đăng xuất',
    'nav.login': 'Đăng nhập',
    'nav.register': 'Đăng ký',
    'auth.login': 'Đăng nhập',
    'auth.register': 'Đăng ký',
    'auth.username': 'Tên người dùng',
    'auth.email': 'Email',
    'auth.password': 'Mật khẩu',
    'auth.native_language': 'Ngôn ngữ mẹ đẻ',
    'auth.select': 'Chọn...',
    'auth.title': 'Phiên âm tiếng Hàn trực tiếp',
    'button.speak': 'Nói',
    'button.listen': 'Nghe',
    'button.voice_translation': 'Dịch giọng nói',
    'status.ready': 'Sẵn sàng',
    'status.recording': 'Đang ghi {language}...',
    'status.not_supported': 'Nhận dạng giọng nói không được hỗ trợ',
    'learn.title': 'Chế độ học tập',
    'learn.no_items': 'Không có từ vựng',
    'learn.swipe_remember': 'Nhớ →',
    'learn.swipe_dont_remember': '← Không nhớ',
    'learn.loading': 'Đang tải...',
    'learn.translation': 'Bản dịch',
    'learn.login_required': 'Vui lòng đăng nhập để sử dụng chế độ học tập'
  }
};

import { getCurrentUser } from './auth.js';

export function t(key, params = {}) {
  const user = getCurrentUser();
  const lang = user?.native_language || localStorage.getItem('selectedLanguage') || 'en';
  const langMap = translations[lang] || translations.en;
  let text = langMap[key] || translations.en[key] || key;
  
  Object.keys(params).forEach(param => {
    text = text.replace(`{${param}}`, params[param]);
  });
  
  return text;
}

export function translatePage() {
  document.querySelectorAll('[data-i18n]').forEach(el => {
    const key = el.getAttribute('data-i18n');
    const params = {};
    el.querySelectorAll('[data-i18n-param]').forEach(paramEl => {
      const paramName = paramEl.getAttribute('data-i18n-param');
      const paramValue = paramEl.textContent || paramEl.value;
      params[paramName] = paramValue;
    });
    el.textContent = t(key, params);
  });
  
  document.querySelectorAll('[data-i18n-placeholder]').forEach(el => {
    const key = el.getAttribute('data-i18n-placeholder');
    el.placeholder = t(key);
  });
  
  document.querySelectorAll('[data-i18n-title]').forEach(el => {
    const key = el.getAttribute('data-i18n-title');
    el.title = t(key);
  });
}

