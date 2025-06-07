/**
 * Vorp Vocabulary System with Lemmatization Support
 * A modular system for vocabulary management and display
 */

// Main namespace
const VorpVocabulary = {
    // Shared utility functions
    utils: {
        getCSRFToken() { /* ... */ },
        updateStats() { /* ... */ },
        // Other shared utilities
    },
    
    // Translation tooltip functionality
    translations: {
        init() { /* Initialize translation tooltips */ },
        showTranslation() { /* ... */ },
        hideTranslation() { /* ... */ },
        updateTranslation() { /* ... */ }
    },
    
    // Vocabulary test page functionality
    test: {
        init() { /* Initialize test page features */ },
        setupWordClickHandlers() { /* ... */ },
        handleWordClick() { /* ... */ },
        updateWordStatus() { /* ... */ }
    },
    
    // Vocabulary management functionality
    manage: {
        init() { /* Initialize management features */ },
        setupEditMode() { /* ... */ },
        markWordAsLearned() { /* ... */ },
        markWordAsUnknown() { /* ... */ },
        removeKnownWord() { /* ... */ },
        addToKnownWords() { /* ... */ }
    },
    
    // Initialization - checks the page and sets up appropriate handlers
    init() {
        // Always initialize translation functionality
        this.translations.init();
        
        // Check which page we're on and initialize appropriate modules
        if (document.querySelector('.vocabulary-test-page')) {
            this.test.init();
        } else if (document.querySelector('.vocabulary-manage-page')) {
            this.manage.init();
        }
    }
};

// Initialize when DOM is ready
document.addEventListener('DOMContentLoaded', function() {
    VorpVocabulary.init();
});

/**
 * Vocabulary test word status update functions with OpenAI word processing
 */

document.addEventListener('DOMContentLoaded', function() {
    // Find the text output container with highlighted words
    const textOutputContainer = document.querySelector('.text-output');
    
    if (textOutputContainer) {
        console.log('Found text output container, setting up event handlers');
        // Add click event listener to the container (event delegation)
        textOutputContainer.addEventListener('click', function(event) {
            // Check if clicked element is a word
            if (event.target.classList.contains('word-unknown')) {
                const word = event.target.dataset.word;
                const vocabularyForm = event.target.dataset.vocabularyForm;
                const currentStatus = event.target.dataset.status;
                
                console.log(`Word clicked: ${word}, vocabulary_form: ${vocabularyForm}, status: ${currentStatus}`);
                
                // Call the update function with vocabulary form
                updateWordStatusWithVocabularyForm(word, vocabularyForm, currentStatus, event.target);
            }
        });
    } else {
        console.log('Text output container not found');
    }
});

/**
 * Update word status with OpenAI vocabulary form support
 * @param {string} word - The original word clicked
 * @param {string} vocabularyForm - The vocabulary form of the word from OpenAI
 * @param {string} currentStatus - Current status of the word
 * @param {HTMLElement} element - The DOM element representing the word
 */
function updateWordStatusWithVocabularyForm(word, vocabularyForm, currentStatus, element) {
    // Only update unknown words
    if (currentStatus === 'unknown') {
        // Update UI immediately for this word
        element.classList.remove('word-unknown');
        element.classList.add('word-learning');
        element.dataset.status = 'learning';
        
        // Update all words with the same vocabulary form
        updateAllWordsWithSameVocabularyForm(vocabularyForm, 'learning');
        
        console.log(`Updated word "${word}" (vocabulary_form: ${vocabularyForm}) to learning status`);
        
        // Update statistics if they exist
        updateStats();
        
        // Send to server with vocabulary form information
        updateWordStatusInDatabase(word, vocabularyForm, currentStatus);
    }
}

/**
 * Update all words with the same vocabulary form to have the same status
 * @param {string} vocabularyForm - The vocabulary form to update
 * @param {string} newStatus - The new status to apply
 */
function updateAllWordsWithSameVocabularyForm(vocabularyForm, newStatus) {
    const wordsWithSameVocabForm = document.querySelectorAll(`[data-vocabulary-form="${vocabularyForm}"]`);
    
    wordsWithSameVocabForm.forEach(wordElement => {
        // Remove old status classes
        wordElement.classList.remove('word-unknown', 'word-learning', 'word-learned');
        
        // Add new status class
        wordElement.classList.add(`word-${newStatus}`);
        wordElement.dataset.status = newStatus;
    });
    
    console.log(`Updated ${wordsWithSameVocabForm.length} words with vocabulary_form "${vocabularyForm}" to status "${newStatus}"`);
}

/**
 * Update the word status in the database via AJAX with vocabulary form support
 * @param {string} word - The original word clicked
 * @param {string} vocabularyForm - The vocabulary form of the word
 * @param {string} currentStatus - Current status of the word
 */
function updateWordStatusInDatabase(word, vocabularyForm, currentStatus) {
    // Enable real AJAX requests
    const isDemoEnvironment = false;
    
    if (isDemoEnvironment) {
        console.log(`Demo mode: Would send AJAX to update "${word}" (vocabulary_form: ${vocabularyForm}) from ${currentStatus} to learning`);
        return;
    }
    
    // Always use Korean language
    const language = 'ko';
    
    // Real implementation using fetch API with vocabulary form support
    fetch('/classification/update-word-status/', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'X-CSRFToken': getCSRFToken()
        },
        body: JSON.stringify({
            word: word,
            vocabulary_form: vocabularyForm,
            current_status: currentStatus,
            language: language
        })
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            console.log(`Successfully updated word "${word}" (vocabulary_form: ${data.vocabulary_form}) to status: ${data.new_status}`);
            
            // Update all words with the same vocabulary form
            updateAllWordsWithSameVocabularyForm(data.vocabulary_form, data.new_status);
            
            // Update stats if provided
            if (data.stats) {
                updateStatsFromServer(data.stats);
            }
        } else {
            console.error(`Error updating word status: ${data.error}`);
            // Revert the UI change on error
            updateAllWordsWithSameVocabularyForm(vocabularyForm, currentStatus);
        }
    })
    .catch(error => {
        console.error('Error updating word status:', error);
        // Revert the UI change on error
        updateAllWordsWithSameVocabularyForm(vocabularyForm, currentStatus);
    });
}

/**
 * Get CSRF token for Django
 */
function getCSRFToken() {
    return document.querySelector('[name=csrfmiddlewaretoken]').value;
}

/**
 * Update statistics display
 */
function updateStats() {
    // Simple stats update - count words by status
    const unknownCount = document.querySelectorAll('.word-unknown').length;
    const learningCount = document.querySelectorAll('.word-learning').length;
    const learnedCount = document.querySelectorAll('.word-learned').length;
    
    // Update the stats display if it exists
    const unknownStats = document.querySelector('.bg-success .card-body h3');
    const learningStats = document.querySelector('.bg-warning .card-body h3');
    const learnedStats = document.querySelector('.bg-light .card-body h3');
    
    if (unknownStats) unknownStats.textContent = unknownCount;
    if (learningStats) learningStats.textContent = learningCount;
    if (learnedStats) learnedStats.textContent = learnedCount;
}

/**
 * Update statistics from server response
 */
function updateStatsFromServer(stats) {
    const unknownStats = document.querySelector('.bg-success .card-body h3');
    const learningStats = document.querySelector('.bg-warning .card-body h3');
    const learnedStats = document.querySelector('.bg-light .card-body h3');
    
    if (unknownStats && stats.unknown !== undefined) unknownStats.textContent = stats.unknown;
    if (learningStats && stats.learning !== undefined) learningStats.textContent = stats.learning;
    if (learnedStats && stats.learned !== undefined) learnedStats.textContent = stats.learned;
}

/**
 * Legacy function for backward compatibility
 */
function updateWordStatus(word, currentStatus, element) {
    const vocabularyForm = element.dataset.vocabularyForm || word;
    updateWordStatusWithVocabularyForm(word, vocabularyForm, currentStatus, element);
} 