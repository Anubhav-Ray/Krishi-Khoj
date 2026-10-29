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

