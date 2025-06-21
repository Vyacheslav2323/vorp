"""
Text processing utilities for vocabulary management
"""

import re
from typing import Dict, List, Tuple, Optional

# Constants
UNKNOWN = 'unknown'
LEARNING = 'learning'
LEARNED = 'learned'

def highlight_text_html_with_lemmas(text: str, user_vocabulary: Dict[str, dict], language: str = 'en') -> str:
    """
    Process text and return HTML with appropriate highlights using lemmatization
    
    Args:
        text: Input text to process
        user_vocabulary: Dictionary mapping lemmas to their status and translation
        language: Language of the text
        
    Returns:
        HTML with words highlighted according to their status
    """
    processed_tokens = process_text_with_lemmas(text, user_vocabulary, language)
    html_parts = []
    
    for token, status, lemma, translation in processed_tokens:
        if status:
            word_id = f"word_{hash(token)}"
            translation_attr = f' data-translation="{translation}"' if translation else ''
            lemma_attr = f' data-lemma="{lemma}"' if lemma else ''
            html_parts.append(f'<span class="word-{status}" data-word-id="{word_id}" data-word="{token}" data-status="{status}"{lemma_attr}{translation_attr}>{token}</span>')
        else:
            html_parts.append(token)
    
    return ''.join(html_parts)

def demo_highlight_text(text: str, user_vocabulary: Dict[str, dict] = None, language: str = 'en') -> Dict:
    """
    Demonstrate text highlighting with a sample vocabulary using lemmatization
    
    Args:
        text: Input text to process
        user_vocabulary: Optional user vocabulary
        language: Language of the text
        
    Returns:
        Dictionary with original text, highlighted HTML, and word stats
    """
    if user_vocabulary is None:
        # Sample vocabulary for demonstration using lemmas
        user_vocabulary = {
            'hello': {'status': 'learned', 'translation': 'Hola'},
            'world': {'status': 'learning', 'translation': 'Mundo'},
            'example': {'status': 'unknown', 'translation': 'Ejemplo'},
            'text': {'status': 'learning', 'translation': 'Texto'},
            'process': {'status': 'unknown', 'translation': 'Procesamiento'},  # lemma of 'processing'
            'run': {'status': 'learning', 'translation': 'Correr'},  # covers 'running', 'runs', 'ran'
        }
    
    # Process the text with lemmatization
    processed_tokens = process_text_with_lemmas(text, user_vocabulary, language)
    
    # Count words by status
    stats = {'learned': 0, 'learning': 0, 'unknown': 0, 'total_words': 0}
    for token, status, lemma, _ in processed_tokens:
        if status:
            stats[status] += 1
            stats['total_words'] += 1
    
    # Generate highlighted HTML with lemmas
    highlighted_html = highlight_text_html_with_lemmas(text, user_vocabulary, language)
    
    return {
        'original_text': text,
        'highlighted_html': highlighted_html,
        'stats': stats
    } 