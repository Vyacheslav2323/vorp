/**
 * Word Translations - Manages displaying translations on hover
 * VERSION: 2024-06-02
 */

console.log('📋 word_translations.js loaded');

// Global tooltip state
let tooltipElement = null;

// Create tooltip element once
function createTooltipElement() {
    if (!tooltipElement) {
        tooltipElement = document.createElement('div');
        tooltipElement.id = 'translation-tooltip';
        document.body.appendChild(tooltipElement);
    }
    return tooltipElement;
}

// Initialize translation tooltips for a specific element
function initializeElementTooltips(element) {
    if (!element) return;
    
    const translation = element.dataset.translation;
    if (translation && translation.trim()) {
        element.addEventListener('mouseenter', showTranslation);
        element.addEventListener('mouseleave', hideTranslation);
        return true;
    }
    return false;
}

// Show translation tooltip
function showTranslation(event) {
    const word = event.currentTarget;
    const translation = word.dataset.translation;
    
    if (!translation) return;
    
    const tooltip = createTooltipElement();
    const rect = word.getBoundingClientRect();
    
    tooltip.textContent = translation;
    tooltip.style.top = (window.scrollY + rect.bottom + 5) + 'px';
    tooltip.style.left = (window.scrollX + rect.left) + 'px';
    tooltip.classList.add('visible');
}

// Hide translation tooltip
function hideTranslation() {
    if (tooltipElement) {
        tooltipElement.classList.remove('visible');
    }
}

// Initialize tooltips for all matching elements in a container
function initializeContainerTooltips(container = document) {
    const wordElements = container.querySelectorAll('[data-word]');
    let tooltipCount = 0;
    
    wordElements.forEach(element => {
        if (initializeElementTooltips(element)) {
            tooltipCount++;
        }
    });
    
    return tooltipCount;
}

// Watch for dynamically added content
const observer = new MutationObserver((mutations) => {
    mutations.forEach(mutation => {
        mutation.addedNodes.forEach(node => {
            if (node.nodeType === 1) { // Element node
                if (node.matches('[data-word]')) {
                    initializeElementTooltips(node);
                } else if (node.querySelector('[data-word]')) {
                    initializeContainerTooltips(node);
                }
            }
        });
    });
});

// Start observing the document
observer.observe(document.body, {
    childList: true,
    subtree: true
});

// Initialize tooltips when DOM is ready
document.addEventListener('DOMContentLoaded', () => {
    initializeContainerTooltips();
});

// Make reinitialization function available globally
window.reinitializeTooltips = initializeContainerTooltips;

/**
 * Get CSRF token for Django requests
 */
function getCSRFToken() {
    return document.querySelector('[name=csrfmiddlewaretoken]').value;
}

/**
 * Fetch translations for words that need them
 */
async function fetchAllTranslations(text, sourceLang = 'ko', targetLang = 'en') {
    const wordElements = document.querySelectorAll('[data-word]');
    const wordsToTranslate = new Set();
    
    // Collect words needing translation
    wordElements.forEach(element => {
        const wordText = element.dataset.word || element.textContent.trim();
        if (!element.dataset.translation) {
            wordsToTranslate.add(wordText);
        }
    });
    
    if (wordsToTranslate.size === 0) {
        hideAnalysisProgress();
        return;
    }
    
    // Show progress indicator
    showAnalysisProgress('Translating...', 0, wordsToTranslate.size);
    
    // Get full text context
    const textOutput = document.querySelector('.text-output');
    const fullTextContext = textOutput ? textOutput.textContent.trim() : text;
    
    // Translate each word
    const translations = {};
    let current = 0;
    
    for (const word of wordsToTranslate) {
        try {
            const response = await fetch('/translation/translate-word/', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': getCSRFToken()
                },
                body: JSON.stringify({
                    word,
                    context: fullTextContext,
                    source_lang: sourceLang,
                    target_lang: targetLang
                })
            });
            
            const data = await response.json();
            if (data.success && data.translation) {
                translations[word] = data.translation;
            }
            
            current++;
            showAnalysisProgress('Translating...', current, wordsToTranslate.size);
            
        } catch (error) {
            console.error(`Translation error for "${word}":`, error);
        }
    }
    
    // Apply translations and clean up
    applyTranslationsToWords(translations);
    hideAnalysisProgress();
}

/**
 * Apply translations to word elements
 */
function applyTranslationsToWords(translations) {
    // Select all word elements regardless of status
    const wordElements = document.querySelectorAll('[data-word]');
    
    wordElements.forEach(element => {
        const wordText = element.dataset.word || element.textContent.trim();
        if (translations[wordText] && !element.dataset.translation) {
            element.dataset.translation = translations[wordText];
            initializeElementTooltips(element);
        }
    });
}

/**
 * Show analysis progress indicator
 */
function showAnalysisProgress(message, current, total) {
    let container = document.getElementById('analysis-progress');
    
    if (!container) {
        container = document.createElement('div');
        container.id = 'analysis-progress';
        container.className = 'alert alert-info position-fixed';
        container.style.cssText = 'top: 20px; right: 20px; z-index: 1000; min-width: 300px;';
        document.body.appendChild(container);
    }
    
    const percentage = Math.round((current / total) * 100);
    
    container.innerHTML = `
        <div class="d-flex align-items-center">
            <div class="spinner-border spinner-border-sm me-2" role="status"></div>
            <div class="flex-grow-1">
                <div>${message}</div>
                <div class="progress mt-1" style="height: 4px;">
                    <div class="progress-bar" style="width: ${percentage}%"></div>
                </div>
                <small class="text-muted">${current}/${total}</small>
            </div>
        </div>
    `;
}

/**
 * Hide analysis progress indicator
 */
function hideAnalysisProgress() {
    const container = document.getElementById('analysis-progress');
    if (container) {
        container.remove();
    }
}

/**
 * Update translation for a word
 */
function updateTranslation(wordId, translation) {
    const element = document.querySelector(`[data-word-id="${wordId}"]`);
    if (element) {
        element.dataset.translation = translation;
        initializeElementTooltips(element);
    }
}

function handleAnalyzeResponse(response) {
    if (response.success) {
        // Update the output container with the new HTML
        const outputContainer = document.querySelector('.text-output');
        if (outputContainer) {
            outputContainer.innerHTML = response.html;
        }
        
        // Update stats if they exist
        if (response.stats) {
            updateStats(response.stats);
        }
        
        // Update the analyses counter if provided
        if (response.analyses_remaining !== undefined) {
            updateAnalysisCounter(
                response.analyses_remaining,
                response.analyses_used,
                response.reset_in
            );
        }
    } else {
        // Handle error
        if (response.limit_reached) {
            // Show limit reached message with countdown
            updateAnalysisCounter(0, 5, response.reset_in);
        }
        if (response.error) {
            alert(response.error);
        }
    }
}

function updateAnalysisCounter(remaining, used, resetIn) {
    const alertDiv = document.querySelector('.alert');
    if (!alertDiv) return;

    // Update alert class
    alertDiv.className = `alert ${remaining > 0 ? 'alert-info' : 'alert-warning'} mb-3`;

    // Format the time string
    const timeStr = formatTimeRemaining(resetIn);

    // Update alert content
    if (remaining > 0) {
        alertDiv.innerHTML = `
            <strong>Daily Analysis Usage:</strong> 
            You have ${remaining} analyses remaining today.
            <br>
            <small class="text-muted">
                Used ${used} out of 5 daily analyses
                • Resets in <span class="reset-countdown">${timeStr}</span>
            </small>
        `;
    } else {
        alertDiv.innerHTML = `
            <strong>Daily Analysis Usage:</strong> 
            You've reached your daily limit. The limit will reset in <span class="reset-countdown">${timeStr}</span>.
            <br>
            <small class="text-muted">Used ${used} out of 5 daily analyses</small>
        `;
    }

    // Disable/enable the analyze button
    const analyzeBtn = document.getElementById('analyze-btn');
    if (analyzeBtn) {
        analyzeBtn.disabled = remaining === 0;
    }

    // Start countdown timer
    startCountdown(resetIn);
}

function formatTimeRemaining(resetIn) {
    if (!resetIn) return '00:00:00';
    const { hours, minutes, seconds } = resetIn;
    return `${String(hours).padStart(2, '0')}:${String(minutes).padStart(2, '0')}:${String(seconds).padStart(2, '0')}`;
}

let countdownInterval;
function startCountdown(resetIn) {
    // Clear any existing countdown
    if (countdownInterval) {
        clearInterval(countdownInterval);
    }

    if (!resetIn) return;

    let totalSeconds = resetIn.hours * 3600 + resetIn.minutes * 60 + resetIn.seconds;

    countdownInterval = setInterval(() => {
        totalSeconds--;
        if (totalSeconds <= 0) {
            clearInterval(countdownInterval);
            // Reload the page when the countdown reaches zero
            window.location.reload();
            return;
        }

        const hours = Math.floor(totalSeconds / 3600);
        const minutes = Math.floor((totalSeconds % 3600) / 60);
        const seconds = totalSeconds % 60;

        const timeStr = `${String(hours).padStart(2, '0')}:${String(minutes).padStart(2, '0')}:${String(seconds).padStart(2, '0')}`;
        
        // Update all countdown spans
        document.querySelectorAll('.reset-countdown').forEach(span => {
            span.textContent = timeStr;
        });
    }, 1000);
}

// Initialize countdown on page load
document.addEventListener('DOMContentLoaded', () => {
    const alertDiv = document.querySelector('.alert');
    if (alertDiv) {
        const countdownSpan = alertDiv.querySelector('.reset-countdown');
        if (countdownSpan) {
            const timeStr = countdownSpan.textContent;
            const [hours, minutes, seconds] = timeStr.split(':').map(Number);
            startCountdown({ hours, minutes, seconds });
        }
    }
}); 