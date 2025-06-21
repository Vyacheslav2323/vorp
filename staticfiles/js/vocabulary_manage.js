/**
 * Vocabulary management functions with lemmatization support
 */

document.addEventListener('DOMContentLoaded', function() {
    // Find all edit mode toggle buttons
    const editButtons = document.querySelectorAll('.toggle-edit-mode');
    
    if (editButtons.length > 0) {
        editButtons.forEach(button => {
            button.addEventListener('click', function() {
                const targetId = this.dataset.target;
                const container = document.getElementById(targetId);
                const isActive = this.classList.contains('active');
                
                // Toggle active state
                if (isActive) {
                    // Turn off edit mode
                    this.classList.remove('active');
                    this.innerHTML = '<i class="bi bi-pencil"></i> Edit';
                    
                    // Hide all action buttons in this container
                    container.querySelectorAll('.action-buttons').forEach(div => {
                        div.style.display = 'none';
                    });
                } else {
                    // Turn on edit mode
                    this.classList.add('active');
                    this.innerHTML = '<i class="bi bi-x"></i> Done';
                    
                    // Show all action buttons in this container
                    container.querySelectorAll('.action-buttons').forEach(div => {
                        div.style.display = 'block';
                    });
                }
            });
        });
    }
    
    // Setup handlers for the buttons (they will only work when visible)
    setupMarkAsKnownButtons();
    setupMarkAsUnknownButtons();
    setupRemoveKnownWordButtons();
});

/**
 * Set up handlers for "Mark as Known" buttons
 */
function setupMarkAsKnownButtons() {
    const markAsKnownButtons = document.querySelectorAll('.mark-as-learned');
    
    if (markAsKnownButtons.length > 0) {
        markAsKnownButtons.forEach(button => {
            button.addEventListener('click', function() {
                const word = this.dataset.word;
                const lemma = this.dataset.lemma;
                const language = this.dataset.language;
                const listItem = this.closest('.list-group-item');
                
                // Call the update function with lemma data
                markWordAsLearned(word, lemma, language, listItem);
            });
        });
    }
}

/**
 * Set up handlers for "Mark as Unknown" buttons
 */
function setupMarkAsUnknownButtons() {
    const markAsUnknownButtons = document.querySelectorAll('.mark-as-unknown');
    
    if (markAsUnknownButtons.length > 0) {
        markAsUnknownButtons.forEach(button => {
            button.addEventListener('click', function() {
                const word = this.dataset.word;
                const lemma = this.dataset.lemma;
                const language = this.dataset.language;
                const listItem = this.closest('.list-group-item');
                
                // Call the update function with lemma data
                markWordAsUnknown(word, lemma, language, listItem);
            });
        });
    }
}

/**
 * Set up handlers for "Remove Known Word" buttons
 */
function setupRemoveKnownWordButtons() {
    const removeKnownWordButtons = document.querySelectorAll('.remove-known-word');
    
    if (removeKnownWordButtons.length > 0) {
        removeKnownWordButtons.forEach(button => {
            button.addEventListener('click', function() {
                const word = this.dataset.word;
                const lemma = this.dataset.lemma;
                const language = this.dataset.language;
                const listItem = this.closest('.list-group-item');
                
                // Call the update function with lemma data
                removeKnownWord(word, lemma, language, listItem);
            });
        });
    }
}

/**
 * Mark a word as learned via AJAX with lemma support
 * @param {string} word - The word to update
 * @param {string} lemma - The lemma of the word
 * @param {string} language - The language of the word
 * @param {HTMLElement} listItem - The list item element containing the word
 */
function markWordAsLearned(word, lemma, language, listItem) {
    // Get CSRF token for Django
    const csrfToken = document.querySelector('[name=csrfmiddlewaretoken]').value;
    
    // Show loading state
    const button = listItem.querySelector('.mark-as-learned');
    const originalText = button.innerHTML;
    button.innerHTML = '<i class="bi bi-hourglass-split"></i> Updating...';
    button.disabled = true;
    
    // Send AJAX request to update the word status
    fetch('/classification/mark-as-learned/', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'X-CSRFToken': csrfToken
        },
        body: JSON.stringify({
            word: word,
            lemma: lemma,
            language: language
        })
    })
    .then(response => {
        if (!response.ok) {
            throw new Error('Network response was not ok');
        }
        return response.json();
    })
    .then(data => {
        if (data.success) {
            console.log(`Successfully updated word "${word}" (lemma: ${data.lemma}) to learned status`);
            
            // Animate the removal of the list item from learning words
            listItem.style.transition = 'opacity 0.5s, transform 0.5s';
            listItem.style.opacity = '0';
            listItem.style.transform = 'translateX(100%)';
            
            // Wait for animation to complete then remove the item
            setTimeout(() => {
                listItem.remove();
                
                // Update counter in the learning words badge
                const learningBadge = document.querySelector('.col-md-6:nth-child(1) .card-header .badge');
                let learningCount = parseInt(learningBadge.textContent) - 1;
                learningBadge.textContent = learningCount;
                
                // Add to known words section
                addToKnownWords(word, lemma, language, data.translation || '', data.vocabulary_form || lemma);
                
                // Check if no more learning words
                const listGroup = document.querySelector('.col-md-6:nth-child(1) .list-group');
                if (listGroup && listGroup.children.length === 0) {
                    listGroup.innerHTML = '<p class="text-muted fst-italic">No learning words yet.</p>';
                }
                
                // Update vocabulary statistics
                if (data.stats) {
                    updateStatistics(data.stats);
                }
            }, 500);
        } else {
            // Error occurred
            console.error('Error updating word status:', data.error);
            button.innerHTML = originalText;
            button.disabled = false;
        }
    })
    .catch(error => {
        console.error('Error updating word status:', error);
        button.innerHTML = originalText;
        button.disabled = false;
    });
}

/**
 * Mark a word as unknown via AJAX with lemma support
 * @param {string} word - The word to update
 * @param {string} lemma - The lemma of the word
 * @param {string} language - The language of the word
 * @param {HTMLElement} listItem - The list item element containing the word
 */
function markWordAsUnknown(word, lemma, language, listItem) {
    // Get CSRF token for Django
    const csrfToken = document.querySelector('[name=csrfmiddlewaretoken]').value;
    
    // Show loading state
    const button = listItem.querySelector('.mark-as-unknown');
    const originalText = button.innerHTML;
    button.innerHTML = '<i class="bi bi-hourglass-split"></i> Removing...';
    button.disabled = true;
    
    // Send AJAX request to update the word status
    fetch('/classification/mark-as-unknown/', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'X-CSRFToken': csrfToken
        },
        body: JSON.stringify({
            word: word,
            lemma: lemma,
            language: language
        })
    })
    .then(response => {
        if (!response.ok) {
            throw new Error('Network response was not ok');
        }
        return response.json();
    })
    .then(data => {
        if (data.success) {
            console.log(`Successfully removed word "${word}" (lemma: ${data.lemma}) from learning status`);
            
            // Animate the removal of the list item
            listItem.style.transition = 'opacity 0.5s, transform 0.5s';
            listItem.style.opacity = '0';
            listItem.style.transform = 'translateX(-100%)';
            
            // Wait for animation to complete then remove the item
            setTimeout(() => {
                listItem.remove();
                
                // Update counter in the learning words badge
                const learningBadge = document.querySelector('.col-md-6:nth-child(1) .card-header .badge');
                let learningCount = parseInt(learningBadge.textContent) - 1;
                learningBadge.textContent = learningCount;
                
                // Check if no more learning words
                const listGroup = document.querySelector('.col-md-6:nth-child(1) .list-group');
                if (listGroup && listGroup.children.length === 0) {
                    listGroup.innerHTML = '<p class="text-muted fst-italic">No learning words yet.</p>';
                }
                
                // Update vocabulary statistics
                if (data.stats) {
                    updateStatistics(data.stats);
                }
            }, 500);
        } else {
            // Error occurred
            console.error(`Error updating word status for "${word}" (lemma: ${lemma}):`, data.error);
            alert(`Failed to remove word "${word}": ${data.error}`);
            button.innerHTML = originalText;
            button.disabled = false;
        }
    })
    .catch(error => {
        console.error(`Error updating word status for "${word}" (lemma: ${lemma}):`, error);
        alert(`Failed to remove word "${word}": ${error.message}`);
        button.innerHTML = originalText;
        button.disabled = false;
    });
}

/**
 * Add a word to the known words list with vocabulary form information
 * @param {string} word - The word to add
 * @param {string} lemma - The lemma of the word
 * @param {string} language - The language of the word
 * @param {string} translation - The translation of the word
 * @param {string} vocabularyForm - The vocabulary form of the word
 */
function addToKnownWords(word, lemma, language, translation, vocabularyForm) {
    const knownWordsContainer = document.querySelector('.col-md-6:nth-child(2) .list-group');
    
    // Check if the "No known words yet" message is shown and remove it
    const noWordsMessage = knownWordsContainer.querySelector('p.fst-italic');
    if (noWordsMessage) {
        noWordsMessage.remove();
    }
    
    // Create the new list item with vocabulary form information
    const currentDate = new Date().toLocaleDateString('en-US', { 
        year: 'numeric', 
        month: 'short', 
        day: 'numeric' 
    });
    
    const listItem = document.createElement('div');
    listItem.className = 'list-group-item';
    listItem.innerHTML = `
        <div class="d-flex justify-content-between align-items-start">
            <div class="flex-grow-1">
                <div class="d-flex align-items-center mb-1">
                    <span class="badge bg-light text-dark p-2 word-display fw-bold">${vocabularyForm}</span>
                    <small class="text-muted ms-2">(${language})</small>
                    ${translation ? `<span class="translation ms-2 text-muted">→ ${translation}</span>` : ''}
                </div>
                <div class="meta-info mt-1">
                    <small class="text-muted">
                        Added: ${currentDate}
                    </small>
                </div>
            </div>
            <div class="action-buttons" style="display: none;">
                <button class="btn btn-sm btn-outline-danger remove-known-word" 
                        data-word="${word}"
                        data-lemma="${lemma}"
                        data-language="${language}">
                    <i class="bi bi-x-circle"></i> Remove
                </button>
            </div>
            </div>
        `;
        
    // Add to the beginning of the list
    knownWordsContainer.insertBefore(listItem, knownWordsContainer.firstChild);
    
    // Set up event handler for the new remove button
    const removeButton = listItem.querySelector('.remove-known-word');
    removeButton.addEventListener('click', function() {
        const word = this.dataset.word;
        const lemma = this.dataset.lemma;
        const language = this.dataset.language;
        const listItem = this.closest('.list-group-item');
        
        removeKnownWord(word, lemma, language, listItem);
    });
        
        // Update counter in the known words badge
    const knownBadge = document.querySelector('.col-md-6:nth-child(2) .card-header .badge');
    let knownCount = parseInt(knownBadge.textContent) + 1;
    knownBadge.textContent = knownCount;
}

/**
 * Remove a known word via AJAX with lemma support
 * @param {string} word - The word to remove
 * @param {string} lemma - The lemma of the word
 * @param {string} language - The language of the word
 * @param {HTMLElement} listItem - The list item element containing the word
 */
function removeKnownWord(word, lemma, language, listItem) {
    // Get CSRF token for Django
    const csrfToken = document.querySelector('[name=csrfmiddlewaretoken]').value;
    
    // Show loading state
    const button = listItem.querySelector('.remove-known-word');
    const originalText = button.innerHTML;
    button.innerHTML = '<i class="bi bi-hourglass-split"></i> Removing...';
    button.disabled = true;
    
    // Send AJAX request to remove the word
    fetch('/classification/remove-known-word/', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'X-CSRFToken': csrfToken
        },
        body: JSON.stringify({
            word: word,
            lemma: lemma,
            language: language
        })
    })
    .then(response => {
        if (!response.ok) {
            throw new Error('Network response was not ok');
        }
        return response.json();
    })
    .then(data => {
        if (data.success) {
            console.log(`Successfully removed word "${word}" (lemma: ${data.lemma}) from known words`);
            
            // Animate the removal of the list item
            listItem.style.transition = 'opacity 0.5s, transform 0.5s';
            listItem.style.opacity = '0';
            listItem.style.transform = 'translateX(-100%)';
            
            // Wait for animation to complete then remove the item
            setTimeout(() => {
                listItem.remove();
                
                // Update counter in the known words badge
                const knownBadge = document.querySelector('.col-md-6:nth-child(2) .card-header .badge');
                let knownCount = parseInt(knownBadge.textContent) - 1;
                knownBadge.textContent = knownCount;
                
                // Check if no more known words
                const listGroup = document.querySelector('.col-md-6:nth-child(2) .list-group');
                if (listGroup && listGroup.children.length === 0) {
                    listGroup.innerHTML = '<p class="text-muted fst-italic">No known words yet.</p>';
                }
                
                // Update vocabulary statistics
                if (data.stats) {
                    updateStatistics(data.stats);
                }
            }, 500);
        } else {
            // Error occurred
            console.error(`Error removing word "${word}" (lemma: ${lemma}):`, data.error);
            alert(`Failed to remove word "${word}": ${data.error}`);
            button.innerHTML = originalText;
            button.disabled = false;
        }
    })
    .catch(error => {
        console.error(`Error removing word "${word}" (lemma: ${lemma}):`, error);
        alert(`Failed to remove word "${word}": ${error.message}`);
        button.innerHTML = originalText;
        button.disabled = false;
    });
}

/**
 * Update the statistics display
 * @param {Object} stats - The statistics object
 */
function updateStatistics(stats) {
    // Update progress bars and percentages
    const learnedBar = document.querySelector('.progress-bar.bg-success');
    const learningBar = document.querySelector('.progress-bar.bg-warning');
    
    if (learnedBar && stats.learned_percent !== undefined) {
        learnedBar.style.width = stats.learned_percent + '%';
        learnedBar.textContent = `Known: ${stats.learned_percent}%`;
    }
    
    if (learningBar && stats.learning_percent !== undefined) {
        learningBar.style.width = stats.learning_percent + '%';
        learningBar.textContent = `Learning: ${stats.learning_percent}%`;
    }
    
    // Update count displays
    const learnedCountEl = document.querySelector('.bg-success.bg-opacity-10 .display-4');
    const learningCountEl = document.querySelector('.bg-warning.bg-opacity-10 .display-4');
    
    if (learnedCountEl && stats.learned_count !== undefined) {
        learnedCountEl.textContent = stats.learned_count;
    }
    
    if (learningCountEl && stats.learning_count !== undefined) {
        learningCountEl.textContent = stats.learning_count;
    }
    
    console.log('Updated statistics:', stats);
} 