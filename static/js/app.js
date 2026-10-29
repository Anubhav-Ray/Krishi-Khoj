/**
 * Krishi Khoj — Frontend JavaScript
 * Handles: file upload UX, drag-drop, search, clipboard, toggles
 */

document.addEventListener('DOMContentLoaded', function() {
    initDropZone();
    initFlashDismiss();
    initCopyButtons();
    initSourceToggles();
    initSearchShortcut();
    initDeleteConfirm();
    initQuickSearch();
    initDetailHighlight();
    initAutocomplete();
    initSearchResultsHighlight();
});

// === Drag & Drop Upload ===
function initDropZone() {
    const dropZone = document.getElementById('drop-zone');
    const fileInput = document.getElementById('pdf-file') || document.querySelector('input[type="file"][name="pdf_file"]') || document.querySelector('input[type="file"]');
    const fileNameDisplay = document.getElementById('file-name');
    const fileNameText = document.getElementById('file-name-text');
    const uploadForm = document.getElementById('upload-form');
    const uploadProgress = document.getElementById('upload-progress');
    
    if (!dropZone || !fileInput) return;
    
    // Click to browse
    dropZone.addEventListener('click', (e) => {
        if (e.target !== fileInput) {
            fileInput.click();
        }
    });
    
    // Drag events
    ['dragenter', 'dragover'].forEach(event => {
        dropZone.addEventListener(event, (e) => {
            e.preventDefault();
            e.stopPropagation();
            dropZone.classList.add('drag-over', 'border-krishi-600', 'bg-krishi-100');
        });
    });
    
    ['dragleave', 'drop'].forEach(event => {
        dropZone.addEventListener(event, (e) => {
            e.preventDefault();
            e.stopPropagation();
            dropZone.classList.remove('drag-over', 'border-krishi-600', 'bg-krishi-100');
        });
    });
    
    dropZone.addEventListener('drop', (e) => {
        const files = e.dataTransfer.files;
        if (files && files.length > 0) {
            const file = files[0];
            if (file.name.toLowerCase().endsWith('.pdf') || file.type === 'application/pdf') {
                try {
                    fileInput.files = files;
                } catch (err) {
                    // Fallback for older browsers
                    const dataTransfer = new DataTransfer();
                    dataTransfer.items.add(file);
                    fileInput.files = dataTransfer.files;
                }
                updateFileName(file);
            } else {
                alert('Please upload a PDF file (.pdf)');
            }
        }
    });
    
    // File selection display
    fileInput.addEventListener('change', (e) => {
        if (e.target.files && e.target.files.length > 0) {
            updateFileName(e.target.files[0]);
        }
    });
    
    // Validation & Progress on submit
    if (uploadForm) {
        uploadForm.addEventListener('submit', (e) => {
            if (!fileInput.files || fileInput.files.length === 0) {
                e.preventDefault();
                alert('Please choose or drop a PDF file first before uploading.');
                fileInput.click();
                return false;
            }
            if (uploadProgress) uploadProgress.classList.remove('hidden');
            const btn = uploadForm.querySelector('button[type="submit"]');
            if (btn) {
                btn.disabled = true;
                btn.innerHTML = '<span class="inline-block animate-spin mr-2">⏳</span> Uploading & Extracting Facts...';
            }
        });
    }
    
    function updateFileName(file) {
        if (!file) return;
        const sizeFormatted = file.size < 1024 * 1024 
            ? `${(file.size / 1024).toFixed(1)} KB` 
            : `${(file.size / (1024 * 1024)).toFixed(1)} MB`;
        
        if (fileNameText) {
            fileNameText.textContent = `${file.name} (${sizeFormatted})`;
        } else if (fileNameDisplay) {
            fileNameDisplay.textContent = `Selected: ${file.name} (${sizeFormatted})`;
        }
        if (fileNameDisplay) {
            fileNameDisplay.classList.remove('hidden');
        }
    }
}

// === Flash Message Dismiss ===
function initFlashDismiss() {
    document.querySelectorAll('.flash-dismiss').forEach(btn => {
        btn.addEventListener('click', () => {
            const container = btn.closest('.flash-message') || btn.parentElement;
            if (container) container.remove();
        });
    });
}

// === Copy to Clipboard ===
function initCopyButtons() {
    document.querySelectorAll('[data-copy]').forEach(btn => {
        btn.addEventListener('click', (e) => {
            e.preventDefault();
            const text = btn.getAttribute('data-copy');
            if (!text) return;
            navigator.clipboard.writeText(text).then(() => {
                const originalText = btn.innerHTML;
                btn.innerHTML = '✓ Copied!';
                btn.classList.add('bg-green-700', 'text-white');
                setTimeout(() => {
                    btn.innerHTML = originalText;
                    btn.classList.remove('bg-green-700', 'text-white');
                }, 2000);
            }).catch(err => {
                console.error('Failed to copy text: ', err);
            });
        });
    });
}

// === Source Text Toggles ===
function initSourceToggles() {
    document.querySelectorAll('.source-toggle').forEach(btn => {
        btn.addEventListener('click', () => {
            const targetId = btn.getAttribute('data-target');
            const target = document.getElementById(targetId);
            if (target) {
                target.classList.toggle('hidden');
                const isHidden = target.classList.contains('hidden');
                btn.innerHTML = isHidden 
                    ? '👁️ Show Source Text' 
                    : '🙈 Hide Source Text';
            }
        });
    });
}

// === Keyboard Shortcut: / to focus search ===
function initSearchShortcut() {
    document.addEventListener('keydown', (e) => {
        if (e.key === '/' && !['INPUT', 'TEXTAREA', 'SELECT'].includes(document.activeElement.tagName)) {
            e.preventDefault();
            const searchInput = document.querySelector('input[name="q"]');
            if (searchInput) {
                searchInput.focus();
                searchInput.select();
            }
        }
    });
}

// === Delete Confirmation ===
function initDeleteConfirm() {
    document.querySelectorAll('.delete-btn').forEach(btn => {
        btn.addEventListener('click', (e) => {
            if (!confirm('Are you sure you want to delete this document and all its extracted facts? This action cannot be undone.')) {
                e.preventDefault();
            }
        });
    });
}

// === Quick Search from Home ===
function initQuickSearch() {
    const quickSearchForm = document.getElementById('quick-search-form');
    if (quickSearchForm) {
        quickSearchForm.addEventListener('submit', (e) => {
            e.preventDefault();
            const input = quickSearchForm.querySelector('input[name="q"]');
            const q = input ? input.value.trim() : '';
            window.location.href = `/search?q=${encodeURIComponent(q)}`;
        });
    }
}

// === Auto-highlight fact on fact detail page ===
function initDetailHighlight() {
    const sourceEl = document.getElementById('source-text-content');
    const factOriginalEl = document.getElementById('fact-original-text');
    if (sourceEl && factOriginalEl) {
        const factText = factOriginalEl.textContent.trim();
        if (factText) {
            highlightFactInSource(factText, sourceEl);
        }
    }
}

function highlightFactInSource(factText, sourceElement) {
    if (!sourceElement || !factText) return;
    const rawText = sourceElement.textContent;
    
    // Attempt exact match first
    const cleanFact = factText.trim();
    if (rawText.includes(cleanFact)) {
        const parts = rawText.split(cleanFact);
        sourceElement.innerHTML = parts.map(escapeHtml).join(`<span class="fact-highlight">${escapeHtml(cleanFact)}</span>`);
        return;
    }
    
    // Fallback: match first 30 chars
    const prefix = cleanFact.substring(0, Math.min(30, cleanFact.length));
    if (prefix && rawText.includes(prefix)) {
        const index = rawText.indexOf(prefix);
        const matchEnd = Math.min(rawText.length, index + cleanFact.length);
        const matched = rawText.substring(index, matchEnd);
        sourceElement.innerHTML = 
            escapeHtml(rawText.substring(0, index)) +
            `<span class="fact-highlight">${escapeHtml(matched)}</span>` +
            escapeHtml(rawText.substring(matchEnd));
    }
}

function escapeHtml(str) {
    const div = document.createElement('div');
    div.textContent = str;
    return div.innerHTML;
}

// === Autocomplete for Search Inputs (activates on 2 or more words) ===
function initAutocomplete() {
    const searchInputs = document.querySelectorAll('input[name="q"]');
    if (!searchInputs.length) return;

    searchInputs.forEach(input => {
        // Disable native browser autocomplete to prevent menu overlap
        input.setAttribute('autocomplete', 'off');

        const container = input.closest('.search-bar-container') || input.parentElement;
        if (!container) return;

        if (window.getComputedStyle(container).position === 'static') {
            container.style.position = 'relative';
        }

        // Locate or create in-search-bar elements
        const ghostTyped = container.querySelector('.ghost-typed');
        const ghostSuffix = container.querySelector('.ghost-suffix');
        const tabPill = container.querySelector('.search-tab-pill');
        const datalistId = input.getAttribute('list');
        const datalist = datalistId ? document.getElementById(datalistId) : null;

        // Create dropdown container
        let dropdown = container.querySelector('.autocomplete-dropdown');
        if (!dropdown) {
            dropdown = document.createElement('div');
            dropdown.className = 'autocomplete-dropdown hidden absolute left-0 right-0 top-full mt-1.5 bg-white rounded-xl shadow-2xl border border-gray-100 z-50 overflow-hidden divide-y divide-gray-50';
            container.appendChild(dropdown);
        }

        let debounceTimer = null;
        let activeIndex = -1;
        let currentSuggestions = [];

        input.addEventListener('input', () => {
            clearTimeout(debounceTimer);
            const val = input.value;
            const trimmed = val.trim();

            if (!trimmed) {
                clearInBarAutocomplete();
                hideDropdown();
                return;
            }

            debounceTimer = setTimeout(() => {
                fetchSuggestions(trimmed);
            }, 120);
        });

        input.addEventListener('keydown', (e) => {
            // Tab key: completes the in-bar suggestion or selected dropdown item
            if (e.key === 'Tab') {
                if (currentSuggestions.length > 0) {
                    const target = (activeIndex >= 0 && activeIndex < currentSuggestions.length)
                        ? currentSuggestions[activeIndex]
                        : currentSuggestions[0];
                    if (target && target.toLowerCase() !== input.value.trim().toLowerCase()) {
                        e.preventDefault();
                        selectSuggestion(target);
                        return;
                    }
                }
            }

            // ArrowRight: complete suggestion if cursor is at the very end of typed text
            if (e.key === 'ArrowRight') {
                if (input.selectionStart === input.value.length && currentSuggestions.length > 0) {
                    const target = currentSuggestions[0];
                    if (target && target.toLowerCase().startsWith(input.value.trim().toLowerCase())) {
                        e.preventDefault();
                        selectSuggestion(target);
                        return;
                    }
                }
            }

            // Dropdown navigation
            if (!dropdown.classList.contains('hidden') && currentSuggestions.length > 0) {
                if (e.key === 'ArrowDown') {
                    e.preventDefault();
                    activeIndex = (activeIndex + 1) % currentSuggestions.length;
                    updateActiveItem();
                    updateInBarWithActive();
                } else if (e.key === 'ArrowUp') {
                    e.preventDefault();
                    activeIndex = (activeIndex - 1 + currentSuggestions.length) % currentSuggestions.length;
                    updateActiveItem();
                    updateInBarWithActive();
                } else if (e.key === 'Enter') {
                    if (activeIndex >= 0 && activeIndex < currentSuggestions.length) {
                        e.preventDefault();
                        selectSuggestion(currentSuggestions[activeIndex]);
                    }
                } else if (e.key === 'Escape') {
                    clearInBarAutocomplete();
                    hideDropdown();
                }
            }
        });

        // Tab Pill click
        if (tabPill) {
            tabPill.addEventListener('click', (e) => {
                e.preventDefault();
                e.stopPropagation();
                if (currentSuggestions.length > 0) {
                    const target = (activeIndex >= 0) ? currentSuggestions[activeIndex] : currentSuggestions[0];
                    selectSuggestion(target);
                }
            });
        }

        // Close dropdown when clicking outside
        document.addEventListener('click', (e) => {
            if (!container.contains(e.target)) {
                clearInBarAutocomplete();
                hideDropdown();
            }
        });

        async function fetchSuggestions(query) {
            try {
                const res = await fetch(`/api/autocomplete?q=${encodeURIComponent(query)}`);
                if (!res.ok) return;
                const data = await res.json();
                
                // Re-verify that user input is still not empty
                const currentText = input.value.trim();
                if (!currentText) {
                    clearInBarAutocomplete();
                    hideDropdown();
                    return;
                }

                if (data.suggestions && data.suggestions.length > 0) {
                    currentSuggestions = data.suggestions;
                    updateInBarAutocomplete(input.value, currentSuggestions[0]);
                    updateDatalist(currentSuggestions);
                    renderDropdown(currentSuggestions, query);
                } else {
                    clearInBarAutocomplete();
                    hideDropdown();
                }
            } catch (err) {
                console.error('Autocomplete fetch error:', err);
                clearInBarAutocomplete();
                hideDropdown();
            }
        }

        function updateInBarAutocomplete(typedValue, suggestion) {
            if (!ghostTyped || !ghostSuffix || !suggestion) {
                clearInBarAutocomplete();
                return;
            }
            const typedTrimmed = typedValue.trim();
            const typedLower = typedTrimmed.toLowerCase();
            const suggLower = suggestion.toLowerCase().trim();

            if (suggLower.startsWith(typedLower) && suggLower !== typedLower) {
                // Suffix matches prefix directly
                const prefix = typedValue;
                const remainder = suggestion.slice(prefix.trim().length);
                ghostTyped.textContent = prefix;
                ghostSuffix.textContent = remainder;

                if (tabPill) {
                    tabPill.innerHTML = `<span>Tab ⇥</span>`;
                    tabPill.title = `Press Tab to complete "${suggestion}"`;
                    tabPill.classList.remove('hidden');
                }
            } else if (suggLower !== typedLower) {
                // Related suggestion
                ghostTyped.textContent = typedValue;
                ghostSuffix.textContent = '';
                if (tabPill) {
                    const shortText = suggestion.length > 20 ? suggestion.substring(0, 19) + '…' : suggestion;
                    tabPill.innerHTML = `<span>↳ ${escapeHtml(shortText)} [Tab ⇥]</span>`;
                    tabPill.title = `Press Tab to complete "${suggestion}"`;
                    tabPill.classList.remove('hidden');
                }
            } else {
                clearInBarAutocomplete();
            }
        }

        function updateInBarWithActive() {
            if (activeIndex >= 0 && activeIndex < currentSuggestions.length) {
                updateInBarAutocomplete(input.value, currentSuggestions[activeIndex]);
            }
        }

        function clearInBarAutocomplete() {
            if (ghostTyped) ghostTyped.textContent = '';
            if (ghostSuffix) ghostSuffix.textContent = '';
            if (tabPill) tabPill.classList.add('hidden');
        }

        function updateDatalist(suggestions) {
            if (!datalist) return;
            datalist.innerHTML = '';
            suggestions.forEach(s => {
                const opt = document.createElement('option');
                opt.value = s;
                datalist.appendChild(opt);
            });
        }

        function renderDropdown(suggestions, query) {
            dropdown.innerHTML = '';
            activeIndex = -1;

            // Header banner
            const header = document.createElement('div');
            header.className = 'px-4 py-2 bg-gray-50 text-[11px] font-semibold text-gray-500 uppercase tracking-wider flex items-center justify-between border-b border-gray-100';
            header.innerHTML = `
                <span class="flex items-center space-x-1">
                    <span>💡</span><span>Search Suggestions</span>
                </span>
                <span class="text-[10px] font-normal text-gray-400">Tab to complete in bar, ↑↓ to pick</span>
            `;
            dropdown.appendChild(header);

            const words = query.toLowerCase().split(/\s+/).filter(Boolean);

            suggestions.forEach((itemText, idx) => {
                const item = document.createElement('div');
                item.className = 'suggestion-item px-4 py-2.5 text-sm text-gray-700 hover:bg-krishi-50 cursor-pointer flex items-center justify-between transition-colors';
                item.dataset.index = idx;

                const highlighted = highlightMatches(itemText, words);

                item.innerHTML = `
                    <div class="flex items-center space-x-2.5 min-w-0">
                        <span class="text-krishi-600 shrink-0 text-xs">🔍</span>
                        <span class="truncate text-gray-800">${highlighted}</span>
                    </div>
                    <span class="text-xs text-gray-400 opacity-60 ml-2 shrink-0">↳</span>
                `;

                item.addEventListener('mouseenter', () => {
                    activeIndex = idx;
                    updateActiveItem();
                    updateInBarWithActive();
                });

                item.addEventListener('click', (e) => {
                    e.preventDefault();
                    e.stopPropagation();
                    selectSuggestion(itemText);
                });

                dropdown.appendChild(item);
            });

            dropdown.classList.remove('hidden');
        }

        function highlightMatches(text, words) {
            let escaped = escapeHtml(text);
            words.forEach(w => {
                if (w.length > 1) {
                    const regex = new RegExp(`(${w.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')})`, 'gi');
                    escaped = escaped.replace(regex, '<strong class="text-krishi-700 font-bold">$1</strong>');
                }
            });
            return escaped;
        }

        function updateActiveItem() {
            const items = dropdown.querySelectorAll('.suggestion-item');
            items.forEach((item, idx) => {
                if (idx === activeIndex) {
                    item.classList.add('bg-krishi-100', 'text-krishi-900');
                    item.classList.remove('text-gray-700');
                } else {
                    item.classList.remove('bg-krishi-100', 'text-krishi-900');
                    item.classList.add('text-gray-700');
                }
            });
        }

        function selectSuggestion(suggestion) {
            input.value = suggestion;
            clearInBarAutocomplete();
            hideDropdown();
            const form = input.closest('form');
            if (form) {
                if (form.id === 'quick-search-form') {
                    window.location.href = `/search?q=${encodeURIComponent(suggestion)}`;
                } else {
                    form.submit();
                }
            }
        }

        function hideDropdown() {
            dropdown.classList.add('hidden');
            dropdown.innerHTML = '';
            currentSuggestions = [];
            activeIndex = -1;
        }
    });
}

// === Highlight Searched Terms in Search Result Cards ===
function initSearchResultsHighlight() {
    const urlParams = new URLSearchParams(window.location.search);
    const q = urlParams.get('q');
    if (!q) return;

    const words = q.trim().split(/\s+/).filter(w => w.length > 1);
    if (!words.length) return;

    document.querySelectorAll('.fact-card-text').forEach(el => {
        let text = el.textContent;
        words.forEach(w => {
            const regex = new RegExp(`(${w.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')})`, 'gi');
            text = text.replace(regex, '<mark class="bg-yellow-200 text-yellow-900 px-1 py-0.5 rounded font-semibold">$1</mark>');
        });
        el.innerHTML = text;
    });
}

