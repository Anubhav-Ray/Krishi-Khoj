"""
SQLite database module for Krishi Khoj.
Manages documents, extracted facts, and page texts with full CRUD operations.
Uses WAL mode for concurrent reads and foreign keys for referential integrity.
"""
import sqlite3
import os
import math
from config import DATABASE_PATH


def get_db_connection():
    """Get a database connection with row factory for dict-like access."""
    conn = sqlite3.connect(DATABASE_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db():
    """Initialize database tables and indexes. Safe to call multiple times."""
    conn = get_db_connection()
    try:
        cursor = conn.cursor()

        # Create documents table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS documents (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                filename TEXT NOT NULL,
                file_hash TEXT NOT NULL,
                version INTEGER DEFAULT 1,
                upload_date TEXT NOT NULL,
                page_count INTEGER DEFAULT 0,
                file_path TEXT NOT NULL,
                file_size INTEGER DEFAULT 0
            )
        """)

        # Create facts table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS facts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                document_id INTEGER NOT NULL,
                crop_name TEXT,
                category TEXT NOT NULL,
                fact_text TEXT NOT NULL,
                value REAL,
                unit TEXT,
                season TEXT,
                region TEXT,
                page_number INTEGER NOT NULL,
                original_text TEXT NOT NULL,
                extraction_date TEXT NOT NULL,
                FOREIGN KEY (document_id) REFERENCES documents(id) ON DELETE CASCADE
            )
        """)

        # Create page_texts table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS page_texts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                document_id INTEGER NOT NULL,
                page_number INTEGER NOT NULL,
                page_text TEXT NOT NULL,
                FOREIGN KEY (document_id) REFERENCES documents(id) ON DELETE CASCADE
            )
        """)

        # Create indexes for efficient querying
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_facts_crop ON facts(crop_name)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_facts_category ON facts(category)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_facts_season ON facts(season)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_facts_document ON facts(document_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_page_texts_document ON page_texts(document_id, page_number)")

        conn.commit()
    finally:
        conn.close()


def insert_document(filename, file_hash, page_count, file_path, file_size):
    """
    Insert a new document record.

    If a document with the same file_hash already exists, returns the existing
    record and marks it as a duplicate. If the same filename exists with a
    different hash, the version number is incremented.

    Args:
        filename: Original filename of the uploaded PDF
        file_hash: SHA-256 hash of the file contents
        page_count: Number of pages in the PDF
        file_path: Absolute path where the file is stored
        file_size: File size in bytes

    Returns:
        dict with keys: id, version, is_duplicate
    """
    conn = get_db_connection()
    try:
        cursor = conn.cursor()

        # Check if exact same file already exists (same hash)
        cursor.execute("SELECT id, version FROM documents WHERE file_hash = ?", (file_hash,))
        existing = cursor.fetchone()
        if existing:
            return {
                'id': existing['id'],
                'version': existing['version'],
                'is_duplicate': True
            }

        # Check if same filename exists with different hash (new version)
        cursor.execute(
            "SELECT MAX(version) as max_version FROM documents WHERE filename = ?",
            (filename,)
        )
        row = cursor.fetchone()
        version = 1
        if row and row['max_version'] is not None:
            version = row['max_version'] + 1

        # Insert new document
        from provenance import get_timestamp
        upload_date = get_timestamp()

        cursor.execute(
            """INSERT INTO documents (filename, file_hash, version, upload_date,
               page_count, file_path, file_size)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (filename, file_hash, version, upload_date, page_count, file_path, file_size)
        )
        conn.commit()

        return {
            'id': cursor.lastrowid,
            'version': version,
            'is_duplicate': False
        }
    finally:
        conn.close()


def insert_fact(document_id, crop_name, category, fact_text, value, unit,
                season, region, page_number, original_text, extraction_date):
    """
    Insert a single extracted fact into the database.

    Args:
        document_id: Foreign key to documents table
        crop_name: Detected crop name (may be None)
        category: Fact category (Fertilizer, Seed, Irrigation, etc.)
        fact_text: Cleaned/truncated fact text
        value: Extracted numeric value (may be None)
        unit: Unit of the value (may be None)
        season: Detected season (may be None)
        region: Detected region (may be None)
        page_number: Source page number (1-indexed)
        original_text: Original unmodified text from the PDF
        extraction_date: ISO 8601 timestamp of extraction

    Returns:
        int: The id of the inserted fact
    """
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        cursor.execute(
            """INSERT INTO facts (document_id, crop_name, category, fact_text,
               value, unit, season, region, page_number, original_text, extraction_date)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (document_id, crop_name, category, fact_text, value, unit,
             season, region, page_number, original_text, extraction_date)
        )
        conn.commit()
        return cursor.lastrowid
    finally:
        conn.close()


def insert_page_text(document_id, page_number, page_text):
    """
    Insert the raw text of a page for source viewing and verification.

    Args:
        document_id: Foreign key to documents table
        page_number: Page number (1-indexed)
        page_text: Full extracted text from the page
    """
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        cursor.execute(
            """INSERT INTO page_texts (document_id, page_number, page_text)
               VALUES (?, ?, ?)""",
            (document_id, page_number, page_text)
        )
        conn.commit()
    finally:
        conn.close()


def search_facts(query=None, crop=None, category=None, season=None,
                 region=None, document_id=None, page=1, per_page=20):
    """
    Search facts with optional filters and pagination.

    Args:
        query: Free-text search (LIKE match on fact_text and original_text)
        crop: Filter by crop name
        category: Filter by category
        season: Filter by season
        region: Filter by region
        document_id: Filter by document
        page: Page number (1-indexed, default 1)
        per_page: Results per page (default 20)

    Returns:
        dict with keys:
        - facts: list of fact dicts (joined with document info)
        - total: total matching count
        - page: current page number
        - per_page: results per page
        - total_pages: total number of pages
    """
    conn = get_db_connection()
    try:
        # Build WHERE clause
        conditions = []
        params = []

        if query:
            conditions.append("(f.fact_text LIKE ? OR f.original_text LIKE ?)")
            like_query = f"%{query}%"
            params.extend([like_query, like_query])
        if crop:
            conditions.append("f.crop_name LIKE ?")
            params.append(f"%{crop}%")
        if category:
            conditions.append("f.category = ?")
            params.append(category)
        if season:
            conditions.append("f.season = ?")
            params.append(season)
        if region:
            conditions.append("f.region LIKE ?")
            params.append(f"%{region}%")
        if document_id:
            conditions.append("f.document_id = ?")
            params.append(document_id)

        where_clause = ""
        if conditions:
            where_clause = "WHERE " + " AND ".join(conditions)

        # Count total matching facts
        count_sql = f"""
            SELECT COUNT(*) as total
            FROM facts f
            JOIN documents d ON f.document_id = d.id
            {where_clause}
        """
        cursor = conn.cursor()
        cursor.execute(count_sql, params)
        total = cursor.fetchone()['total']

        # Calculate pagination
        total_pages = max(1, math.ceil(total / per_page))
        page = max(1, min(page, total_pages))
        offset = (page - 1) * per_page

        # Fetch paginated results
        data_sql = f"""
            SELECT f.*, d.filename, d.file_hash, d.version as document_version
            FROM facts f
            JOIN documents d ON f.document_id = d.id
            {where_clause}
            ORDER BY f.id DESC
            LIMIT ? OFFSET ?
        """
        cursor.execute(data_sql, params + [per_page, offset])
        facts = [dict(row) for row in cursor.fetchall()]

        return {
            'facts': facts,
            'total': total,
            'page': page,
            'per_page': per_page,
            'total_pages': total_pages
        }
    finally:
        conn.close()


def get_fact_by_id(fact_id):
    """
    Get a single fact with its document info and the page text for context.

    Args:
        fact_id: The fact's primary key

    Returns:
        dict with fact data, document info, and page_text, or None if not found
    """
    conn = get_db_connection()
    try:
        cursor = conn.cursor()

        # Get fact with document info
        cursor.execute("""
            SELECT f.*, d.filename, d.file_hash, d.version as document_version,
                   d.upload_date
            FROM facts f
            JOIN documents d ON f.document_id = d.id
            WHERE f.id = ?
        """, (fact_id,))
        row = cursor.fetchone()
        if not row:
            return None

        fact = dict(row)

        # Get the page text for context
        cursor.execute("""
            SELECT page_text FROM page_texts
            WHERE document_id = ? AND page_number = ?
        """, (fact['document_id'], fact['page_number']))
        page_row = cursor.fetchone()
        fact['page_text'] = page_row['page_text'] if page_row else ''

        return fact
    finally:
        conn.close()


def get_document_by_id(document_id):
    """
    Get document info with list of all its pages and fact count per page.

    Args:
        document_id: The document's primary key

    Returns:
        dict with document info, pages list, and per-page fact counts,
        or None if not found
    """
    conn = get_db_connection()
    try:
        cursor = conn.cursor()

        # Get document
        cursor.execute("SELECT * FROM documents WHERE id = ?", (document_id,))
        doc_row = cursor.fetchone()
        if not doc_row:
            return None

        doc = dict(doc_row)

        # Get pages
        cursor.execute(
            "SELECT page_number, page_text FROM page_texts WHERE document_id = ? ORDER BY page_number",
            (document_id,)
        )
        doc['pages'] = [dict(row) for row in cursor.fetchall()]

        # Get fact count per page
        cursor.execute("""
            SELECT page_number, COUNT(*) as fact_count
            FROM facts WHERE document_id = ?
            GROUP BY page_number ORDER BY page_number
        """, (document_id,))
        doc['fact_counts'] = {row['page_number']: row['fact_count'] for row in cursor.fetchall()}

        # Get total fact count
        cursor.execute("SELECT COUNT(*) as total FROM facts WHERE document_id = ?", (document_id,))
        doc['total_facts'] = cursor.fetchone()['total']

        return doc
    finally:
        conn.close()


def get_all_documents():
    """
    List all documents with their fact counts.

    Returns:
        list of dicts, each with document info and fact_count
    """
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT d.*, COUNT(f.id) as fact_count
            FROM documents d
            LEFT JOIN facts f ON d.id = f.document_id
            GROUP BY d.id
            ORDER BY d.upload_date DESC
        """)
        return [dict(row) for row in cursor.fetchall()]
    finally:
        conn.close()


def get_page_text(document_id, page_number):
    """
    Get the raw text of a specific page.

    Args:
        document_id: The document's primary key
        page_number: Page number (1-indexed)

    Returns:
        str: The page text, or empty string if not found
    """
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT page_text FROM page_texts WHERE document_id = ? AND page_number = ?",
            (document_id, page_number)
        )
        row = cursor.fetchone()
        return row['page_text'] if row else ''
    finally:
        conn.close()


def get_stats():
    """
    Get overall statistics for the Krishi Khoj database.

    Returns:
        dict with keys: total_documents, total_facts, total_pages,
        categories (list), crops (list), seasons (list)
    """
    conn = get_db_connection()
    try:
        cursor = conn.cursor()

        cursor.execute("SELECT COUNT(*) as c FROM documents")
        total_documents = cursor.fetchone()['c']

        cursor.execute("SELECT COUNT(*) as c FROM facts")
        total_facts = cursor.fetchone()['c']

        cursor.execute("SELECT COUNT(*) as c FROM page_texts")
        total_pages = cursor.fetchone()['c']

        categories = get_distinct_values('category')
        crops = get_distinct_values('crop_name')
        seasons = get_distinct_values('season')

        return {
            'total_documents': total_documents,
            'total_facts': total_facts,
            'total_pages': total_pages,
            'categories': categories,
            'crops': crops,
            'seasons': seasons,
        }
    finally:
        conn.close()


def get_distinct_values(column):
    """
    Get distinct non-null values for a given column from the facts table.

    Args:
        column: Column name (must be one of the allowed columns)

    Returns:
        list of distinct string values, sorted alphabetically
    """
    allowed_columns = {'crop_name', 'category', 'season', 'region', 'unit'}
    if column not in allowed_columns:
        raise ValueError(f"Column '{column}' not allowed. Must be one of {allowed_columns}")

    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        cursor.execute(
            f"SELECT DISTINCT {column} FROM facts WHERE {column} IS NOT NULL ORDER BY {column}"
        )
        return [row[0] for row in cursor.fetchall()]
    finally:
        conn.close()


def delete_document(document_id):
    """
    Delete a document and all its associated facts and page texts.

    Relies on ON DELETE CASCADE for related records.

    Args:
        document_id: The document's primary key

    Returns:
        bool: True if a document was deleted, False if not found
    """
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM documents WHERE id = ?", (document_id,))
        conn.commit()
        return cursor.rowcount > 0
    finally:
        conn.close()


def get_document_facts(document_id, category=None, page_number=None):
    """
    Get all facts for a document, optionally filtered by category or page.

    Args:
        document_id: The document's primary key
        category: Optional category filter
        page_number: Optional page number filter

    Returns:
        list of fact dicts
    """
    conn = get_db_connection()
    try:
        conditions = ["document_id = ?"]
        params = [document_id]

        if category:
            conditions.append("category = ?")
            params.append(category)
        if page_number:
            conditions.append("page_number = ?")
            params.append(page_number)

        where_clause = " AND ".join(conditions)
        cursor = conn.cursor()
        cursor.execute(
            f"SELECT * FROM facts WHERE {where_clause} ORDER BY page_number, id",
            params
        )
        return [dict(row) for row in cursor.fetchall()]
    finally:
        conn.close()
