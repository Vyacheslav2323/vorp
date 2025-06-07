"""
Text processing utilities for vocabulary management
"""

import re
from typing import Dict, List, Tuple, Optional

# Constants
UNKNOWN = 'unknown'
LEARNING = 'learning'
LEARNED = 'learned'

def tokenize_text(text: str) -> List[str]:
    """
    Tokenize text into words and non-words
    
    Args:
        text: Input text to tokenize
        
    Returns:
        List of tokens
    """
    pattern = r'([가-힣]+|[a-zA-Z]+|\d+|[^\w\s]|\s+)'
    return re.findall(pattern, text)

def get_word_status(word: str, user_vocabulary: Dict[str, dict]) -> str:
    """
    Get the status of a word from the user's vocabulary
    
    Args:
        word: Word to check
        user_vocabulary: Dictionary mapping words to their status
        
    Returns:
        Status of the word (unknown, learning, or learned)
    """
    if word in user_vocabulary:
        return user_vocabulary[word]['status']
    return UNKNOWN

def process_text_with_lemmas(text: str, user_vocabulary: Dict[str, dict], language: str = 'en') -> List[Tuple[str, str, str, Optional[str]]]:
    """
    Process text and mark words with their status using lemmatization
    
    Args:
        text: Input text to process
        user_vocabulary: Dictionary mapping lemmas to their status and translation
        language: Language of the text
        
    Returns:
        List of tuples (token, status, lemma, translation)
    """
    tokens = tokenize_text(text)
    result = []
    
    for token in tokens:
        # Skip whitespace and punctuation
        if not re.match(r'\b\w+\b', token):
            result.append((token, '', '', None))
            continue
        
        status, lemma = get_word_status_by_lemma(token, user_vocabulary, language)
        
        # Get translation if available
        translation = None
        if lemma in user_vocabulary and 'translation' in user_vocabulary[lemma]:
            translation = user_vocabulary[lemma]['translation']
            
        result.append((token, status, lemma, translation))
        
    return result

def process_text_with_status(text: str, user_vocabulary: Dict[str, dict]) -> List[Tuple[str, str, Optional[str]]]:
    """
    Process text and mark words with their status from user's vocabulary (legacy function)
    
    Args:
        text: Input text to process
        user_vocabulary: Dictionary mapping words to their status and translation
        
    Returns:
        List of tuples (token, status, translation)
    """
    tokens = tokenize_text(text)
    result = []
    
    for token in tokens:
        # Skip whitespace and punctuation
        if not re.match(r'\b\w+\b', token):
            result.append((token, '', None))
            continue
        
        word_lower = token.lower()
        status = get_word_status(word_lower, user_vocabulary)
        
        # Get translation if available
        translation = None
        if word_lower in user_vocabulary and 'translation' in user_vocabulary[word_lower]:
            translation = user_vocabulary[word_lower]['translation']
            
        result.append((token, status, translation))
        
    return result

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

def highlight_text_html(text: str, user_vocabulary: Dict[str, dict]) -> str:
    """
    Process text and return HTML with appropriate highlights (legacy function)
    
    Args:
        text: Input text to process
        user_vocabulary: Dictionary mapping words to their status and translation
        
    Returns:
        HTML with words highlighted according to their status
    """
    processed_tokens = process_text_with_status(text, user_vocabulary)
    html_parts = []
    
    for token, status, translation in processed_tokens:
        if status:
            word_id = f"word_{hash(token)}"
            translation_attr = f' data-translation="{translation}"' if translation else ''
            html_parts.append(f'<span class="word-{status}" data-word-id="{word_id}" data-word="{token}" data-status="{status}"{translation_attr}>{token}</span>')
        else:
            html_parts.append(token)
    
    return ''.join(html_parts)

def update_word_status(word: str, current_status: str, user_vocabulary: Dict[str, str]) -> Dict[str, str]:
    """
    Update the status of a word in the user's vocabulary based on current status.
    
    Status transitions:
    - unknown -> learning
    - learning -> stays as learning (no direct transition to learned)
    - learned -> (stays learned)
    
    Args:
        word: The word to update
        current_status: Current status of the word
        user_vocabulary: Dictionary mapping words to their status
        
    Returns:
        Updated user vocabulary dictionary
    """
    word_lower = word.lower()
    
    if current_status == UNKNOWN:
        user_vocabulary[word_lower] = LEARNING
    # Removed learning -> learned transition
    # Learning words stay as learning until manually marked as learned
    
    return user_vocabulary

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