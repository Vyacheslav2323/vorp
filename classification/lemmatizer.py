"""
Lemmatization Service using spaCy
Provides word lemmatization for vocabulary classification
"""

import spacy
import logging
from typing import Optional, Dict, List
from functools import lru_cache

# Set up logging
logger = logging.getLogger(__name__)

class LemmatizationService:
    """Service for word lemmatization using spaCy"""
    
    def __init__(self):
        self.nlp_en = None
        self.nlp_ko = None
        self._load_models()
    
    def _load_models(self):
        """Load spaCy language models"""
        try:
            # Load English model
            self.nlp_en = spacy.load('en_core_web_sm')
            logger.info("English spaCy model loaded successfully")
        except OSError:
            logger.error("English spaCy model not found. Please install with: python -m spacy download en_core_web_sm")
            self.nlp_en = None
        
        try:
            # Try to load Korean model (optional)
            self.nlp_ko = spacy.load('ko_core_news_sm')
            logger.info("Korean spaCy model loaded successfully")
        except OSError:
            logger.warning("Korean spaCy model not found. Korean lemmatization will be limited.")
            self.nlp_ko = None
    
    @lru_cache(maxsize=1000)
    def get_lemma(self, word: str, language: str = 'en') -> str:
        """
        Get the lemma (base form) of a word
        
        Args:
            word (str): The word to lemmatize
            language (str): Language code ('en' or 'ko')
            
        Returns:
            str: The lemma of the word
        """
        if not word or not word.strip():
            return word
        
        word = word.strip().lower()
        
        try:
            if language == 'en' and self.nlp_en:
                doc = self.nlp_en(word)
                if doc and len(doc) > 0:
                    lemma = doc[0].lemma_.lower()
                    logger.debug(f"Lemmatized '{word}' -> '{lemma}' (EN)")
                    return lemma
            elif language == 'ko' and self.nlp_ko:
                doc = self.nlp_ko(word)
                if doc and len(doc) > 0:
                    lemma = doc[0].lemma_.lower()
                    # Clean up Korean lemmas - extract root before "+"
                    if '+' in lemma:
                        lemma = lemma.split('+')[0]
                    logger.debug(f"Lemmatized '{word}' -> '{lemma}' (KO)")
                    return lemma
            else:
                logger.warning(f"No model available for language: {language}")
                
        except Exception as e:
            logger.error(f"Error lemmatizing '{word}': {str(e)}")
        
        # Fallback: return the original word
        return word
    
    def get_lemmas_from_text(self, text: str, language: str = 'en') -> Dict[str, str]:
        """
        Extract all words and their lemmas from a text
        
        Args:
            text (str): The text to process
            language (str): Language code ('en' or 'ko')
            
        Returns:
            Dict[str, str]: Mapping of original words to their lemmas
        """
        if not text or not text.strip():
            return {}
        
        word_lemma_map = {}
        
        try:
            if language == 'en' and self.nlp_en:
                doc = self.nlp_en(text)
            elif language == 'ko' and self.nlp_ko:
                doc = self.nlp_ko(text)
            else:
                logger.warning(f"No model available for language: {language}")
                return {}
            
            for token in doc:
                if token.is_alpha and len(token.text) > 1:  # Only process alphabetic words longer than 1 char
                    original = token.text.lower()
                    lemma = token.lemma_.lower()
                    # Clean up Korean lemmas - extract root before "+"
                    if language == 'ko' and '+' in lemma:
                        lemma = lemma.split('+')[0]
                    word_lemma_map[original] = lemma
                    
        except Exception as e:
            logger.error(f"Error processing text for lemmas: {str(e)}")
        
        return word_lemma_map
    
    def get_word_variations(self, lemma: str, language: str = 'en') -> List[str]:
        """
        Get possible variations of a lemma (this is a simplified approach)
        Note: This is basic functionality. For full morphological generation,
        you'd need additional tools.
        
        Args:
            lemma (str): The base form of the word
            language (str): Language code
            
        Returns:
            List[str]: List of possible word variations
        """
        variations = [lemma]
        
        if language == 'en':
            # Basic English inflections (this is simplified)
            if lemma.endswith('e'):
                variations.extend([lemma + 'd', lemma + 's', lemma[:-1] + 'ing'])
            elif lemma.endswith('y'):
                variations.extend([lemma[:-1] + 'ied', lemma[:-1] + 'ies', lemma + 'ing'])
            else:
                variations.extend([lemma + 'ed', lemma + 's', lemma + 'ing'])
                
            # Handle common irregular forms (basic set)
            irregular_forms = {
                'be': ['am', 'is', 'are', 'was', 'were', 'being', 'been'],
                'have': ['has', 'had', 'having'],
                'do': ['does', 'did', 'doing', 'done'],
                'go': ['goes', 'went', 'going', 'gone'],
                'run': ['runs', 'ran', 'running'],
                'get': ['gets', 'got', 'getting', 'gotten'],
                'make': ['makes', 'made', 'making'],
                'take': ['takes', 'took', 'taking', 'taken'],
            }
            
            if lemma in irregular_forms:
                variations.extend(irregular_forms[lemma])
        
        return list(set(variations))  # Remove duplicates
    
    def is_same_lemma(self, word1: str, word2: str, language: str = 'en') -> bool:
        """
        Check if two words have the same lemma
        
        Args:
            word1 (str): First word
            word2 (str): Second word
            language (str): Language code
            
        Returns:
            bool: True if words have the same lemma
        """
        lemma1 = self.get_lemma(word1, language)
        lemma2 = self.get_lemma(word2, language)
        return lemma1 == lemma2


# Global instance
lemmatizer = LemmatizationService() 