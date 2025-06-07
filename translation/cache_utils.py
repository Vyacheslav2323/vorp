"""
Cache utilities for word analysis and translations
"""

import hashlib
import json
from django.core.cache import cache

# Cache timeout (in seconds)
WORD_CACHE_TIMEOUT = 60 * 60 * 24 * 7  # 1 week

def get_cache_key(word: str) -> str:
    """Generate a cache key for a word"""
    word_hash = hashlib.md5(word.encode('utf-8')).hexdigest()
    return f"korean_vocab_word_{word_hash}"

def get_cached_word_analysis(word: str) -> tuple:
    """Get cached word analysis"""
    cache_key = get_cache_key(word)
    cached = cache.get(cache_key)
    if cached:
        try:
            data = json.loads(cached)
            return data.get('vocabulary_form'), data.get('translation')
        except:
            pass
    return None, None

def set_cached_word_analysis(word: str, vocabulary_form: str, translation: str) -> None:
    """Cache word analysis"""
    cache_key = get_cache_key(word)
    data = {
        'vocabulary_form': vocabulary_form,
        'translation': translation
    }
    cache.set(cache_key, json.dumps(data), WORD_CACHE_TIMEOUT)

def invalidate_word_cache(word: str) -> None:
    """Invalidate cache for a word"""
    cache_key = get_cache_key(word)
    cache.delete(cache_key) 