"""
Provenance tracking for Krishi Khoj.
Ensures every extracted fact can be traced back to its exact source.
Uses SHA-256 hashing for tamper-evident document versioning.
"""
import hashlib
from datetime import datetime


def compute_file_hash(file_path: str) -> str:
    """Compute SHA-256 hash of a file for version tracking."""
    sha256 = hashlib.sha256()
    with open(file_path, 'rb') as f:
        for chunk in iter(lambda: f.read(8192), b''):
            sha256.update(chunk)
    return sha256.hexdigest()


def compute_bytes_hash(data: bytes) -> str:
    """Compute SHA-256 hash of raw bytes."""
    return hashlib.sha256(data).hexdigest()


def get_timestamp() -> str:
    """Get current ISO 8601 timestamp for extraction records."""
    return datetime.now().isoformat()


def create_provenance_record(document_name: str, document_hash: str,
                              version: int, page_number: int) -> dict:
    """Create a provenance metadata dict for a fact."""
    return {
        'document_name': document_name,
        'document_hash': document_hash,
        'document_version': version,
        'page_number': page_number,
        'extraction_date': get_timestamp()
    }


def format_provenance_citation(document_name: str, version: int,
                                page_number: int) -> str:
    """Format a human-readable provenance citation string."""
    return f"[{document_name} v{version}, Page {page_number}]"
