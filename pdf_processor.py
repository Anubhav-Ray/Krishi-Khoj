"""
PDF text extraction for Krishi Khoj.
Uses PyMuPDF (fitz) for fast, accurate page-level text extraction.
"""
import fitz  # PyMuPDF
import os
from provenance import compute_file_hash, get_timestamp


class PDFProcessor:
    """Extracts text from PDF files with page-level granularity."""
    
    def __init__(self, file_path: str):
        """
        Initialize with path to a PDF file.
        
        Args:
            file_path: Absolute path to the PDF file
            
        Raises:
            FileNotFoundError: If file doesn't exist
            ValueError: If file is not a PDF
        """
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"PDF not found: {file_path}")
        if not file_path.lower().endswith('.pdf'):
            raise ValueError(f"Not a PDF file: {file_path}")
            
        self.file_path = file_path
        self.filename = os.path.basename(file_path)
        self.file_hash = compute_file_hash(file_path)
        self.file_size = os.path.getsize(file_path)
        self._doc = None
    
    def open(self):
        """Open the PDF document."""
        self._doc = fitz.open(self.file_path)
        return self
    
    def close(self):
        """Close the PDF document."""
        if self._doc:
            self._doc.close()
            self._doc = None
    
    def __enter__(self):
        self.open()
        return self
    
    def __exit__(self, *args):
        self.close()
    
    @property
    def page_count(self) -> int:
        """Number of pages in the PDF."""
        if not self._doc:
            raise RuntimeError("PDF not opened. Use 'with' statement or call open().")
        return len(self._doc)
    
    def extract_page_text(self, page_number: int) -> str:
        """
        Extract text from a specific page (1-indexed).
        
        Args:
            page_number: Page number (1-indexed)
            
        Returns:
            Extracted text from the page
        """
        if not self._doc:
            raise RuntimeError("PDF not opened.")
        if page_number < 1 or page_number > self.page_count:
            raise ValueError(f"Page {page_number} out of range (1-{self.page_count})")
        
        page = self._doc[page_number - 1]  # fitz uses 0-indexed
        text = page.get_text("text")
        return text.strip()
    
    def extract_all_pages(self) -> list:
        """
        Extract text from all pages.
        
        Returns:
            List of dicts: [{'page_number': 1, 'text': '...'}, ...]
        """
        if not self._doc:
            raise RuntimeError("PDF not opened.")
        
        pages = []
        for i in range(self.page_count):
            page = self._doc[i]
            text = page.get_text("text").strip()
            if text:  # Only include pages with text
                pages.append({
                    'page_number': i + 1,
                    'text': text
                })
        return pages
    
    def get_metadata(self) -> dict:
        """Get PDF metadata."""
        if not self._doc:
            raise RuntimeError("PDF not opened.")
        
        meta = self._doc.metadata
        return {
            'title': meta.get('title', ''),
            'author': meta.get('author', ''),
            'subject': meta.get('subject', ''),
            'creator': meta.get('creator', ''),
            'producer': meta.get('producer', ''),
            'page_count': self.page_count,
            'file_hash': self.file_hash,
            'file_size': self.file_size,
            'filename': self.filename
        }
    
    def get_document_info(self) -> dict:
        """Get comprehensive document info for database storage."""
        return {
            'filename': self.filename,
            'file_hash': self.file_hash,
            'page_count': self.page_count if self._doc else 0,
            'file_path': self.file_path,
            'file_size': self.file_size,
            'extraction_date': get_timestamp()
        }
