# Translation System Guide

## Overview
The website automatically translates all labels to the user's native language (set during registration). The translation system uses the `translations.js` module and data attributes in HTML.

## How It Works

1. **Translation File**: `front-end/translations.js` contains all translations for:
   - English (en)
   - Russian (ru)
   - Chinese (zh)
   - Vietnamese (vi)

2. **User's Native Language**: Automatically detected from the logged-in user's profile.

3. **Translation Functions**:
   - `t(key, params)` - Returns translated text for a key
   - `translatePage()` - Automatically translates all elements with `data-i18n` attributes

## Usage Examples

### In JavaScript:
```javascript
import { t } from './translations.js';

// Simple translation
const text = t('vocab.title'); // Returns "Your Vocabulary" (or translated version)

// Translation with parameters
const welcome = t('nav.welcome', { username: 'John' }); 
// Returns "Welcome, John!" (or translated version)
```

### In HTML:
```html
<!-- Translate text content -->
<h2 data-i18n="vocab.title">Your Vocabulary</h2>

<!-- Translate placeholder -->
<input data-i18n-placeholder="auth.username" />

<!-- Translate title attribute -->
<button data-i18n-title="nav.vocab">Vocab</button>
```

### In Dynamic Content:
```javascript
// When creating elements dynamically
const button = document.createElement('button');
button.textContent = t('nav.vocab');
```

## Adding New Translations

1. Add the translation key to all language objects in `translations.js`:
```javascript
en: {
  'new.key': 'English text',
  // ...
},
ru: {
  'new.key': 'Русский текст',
  // ...
},
// ... etc
```

2. Use it in your code:
```javascript
t('new.key')
```

Or in HTML:
```html
<span data-i18n="new.key">Default text</span>
```

## Calling translatePage()

Call `translatePage()` after:
- Page load
- User login
- Content updates
- Any time the page content changes

Example:
```javascript
import { translatePage } from './translations.js';

async function init() {
  updateNavbar();
  translatePage(); // Translate all data-i18n elements
  // ... rest of initialization
}
```

## Translation Keys

Current translation keys follow this pattern:
- `app.*` - Application-wide labels
- `vocab.*` - Vocabulary page
- `nav.*` - Navigation elements
- `auth.*` - Authentication forms
- `status.*` - Status messages
- `learn.*` - Learning mode

## Supported Languages

- English (en) - Default fallback
- Russian (ru)
- Chinese (zh)
- Vietnamese (vi)

To add more languages, add a new object to the `translations` object in `translations.js`.

