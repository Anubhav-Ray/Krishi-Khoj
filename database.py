"""
SQLite database module for Krishi Khoj.
Manages documents, extracted facts, page texts, and users with full CRUD operations.
Uses WAL mode for concurrent reads, foreign keys for referential integrity,
and strict per-user ownership scoping.
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
    """
    Initialize database tables and indexes. Safe to call multiple times.
    Applies incremental migration for user_id ownership on documents.
    """
    conn = get_db_connection()
    try:
        cursor = conn.cursor()

        # Create users table for authentication
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL COLLATE NOCASE,
                password_hash TEXT NOT NULL,
                created_at TEXT NOT NULL
            )
        """)
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_users_username ON users(username)")

        # Create documents table (with user_id ownership column)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS documents (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                filename TEXT NOT NULL,
                file_hash TEXT NOT NULL,
                version INTEGER DEFAULT 1,
                upload_date TEXT NOT NULL,
                page_count INTEGER DEFAULT 0,
                file_path TEXT NOT NULL,
                file_size INTEGER DEFAULT 0,
                FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
            )
        """)

        # Migration check: Ensure user_id column exists on existing documents table
        cursor.execute("PRAGMA table_info(documents)")
        existing_cols = {row['name'] for row in cursor.fetchall()}
        if 'user_id' not in existing_cols:
            cursor.execute("ALTER TABLE documents ADD COLUMN user_id INTEGER REFERENCES users(id)")

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
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_documents_user ON documents(user_id)")

        # Seed MLH Judge demo account if not exists
        cursor.execute("SELECT id FROM users WHERE username = 'mlh_judge'")
        if not cursor.fetchone():
            from werkzeug.security import generate_password_hash
            from provenance import get_timestamp
            cursor.execute(
                """INSERT INTO users (username, password_hash, created_at)
                   VALUES (?, ?, ?)""",
                ('mlh_judge', generate_password_hash('Judge@Krishi2024'), get_timestamp())
            )

        conn.commit()
    finally:
        conn.close()


def create_user(username: str, password_hash: str):
    """
    Create a new user record.
    Returns user id on success, or None if username already exists.
    """
    from provenance import get_timestamp
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        cursor.execute(
            """INSERT INTO users (username, password_hash, created_at)
               VALUES (?, ?, ?)""",
            (username.strip(), password_hash, get_timestamp())
        )
        conn.commit()
        return cursor.lastrowid
    except sqlite3.IntegrityError:
        # Username already exists or constraint violation
        return None
    finally:
        conn.close()


def get_user_by_username(username: str):
    """Fetch user by username (case-insensitive due to COLLATE NOCASE)."""
    if not username:
        return None
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM users WHERE username = ?", (username.strip(),))
        row = cursor.fetchone()
        return dict(row) if row else None
    finally:
        conn.close()


def get_user_by_id(user_id: int):
    """Fetch user by ID (excludes password_hash for safety)."""
    if not user_id:
        return None
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT id, username, created_at FROM users WHERE id = ?", (user_id,))
        row = cursor.fetchone()
        return dict(row) if row else None
    finally:
        conn.close()


def insert_document(filename, file_hash, page_count, file_path, file_size, user_id: int):
    """
    Insert a new document record scoped to user_id.

    Duplicate detection (same file_hash) and versioning are strictly per-user
    so that one user uploading a document does not reveal or conflict with another user.

    Args:
        filename: Original filename of the uploaded PDF
        file_hash: SHA-256 hash of the file contents
        page_count: Number of pages in the PDF
        file_path: Absolute path where the file is stored
        file_size: File size in bytes
        user_id: The authenticated user's ID

    Returns:
        dict with keys: id, version, is_duplicate
    """
    conn = get_db_connection()
    try:
        cursor = conn.cursor()

        # Check if exact same file already exists FOR THIS USER (same hash + same user)
        cursor.execute(
            "SELECT id, version FROM documents WHERE file_hash = ? AND user_id = ?",
            (file_hash, user_id)
        )
        existing = cursor.fetchone()
        if existing:
            return {
                'id': existing['id'],
                'version': existing['version'],
                'is_duplicate': True
            }

        # Check if same filename exists for this user with different hash (new version)
        cursor.execute(
            "SELECT MAX(version) as max_version FROM documents WHERE filename = ? AND user_id = ?",
            (filename, user_id)
        )
        row = cursor.fetchone()
        version = 1
        if row and row['max_version'] is not None:
            version = row['max_version'] + 1

        # Insert new document with user_id
        from provenance import get_timestamp
        upload_date = get_timestamp()

        cursor.execute(
            """INSERT INTO documents (filename, file_hash, version, upload_date,
               page_count, file_path, file_size, user_id)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            (filename, file_hash, version, upload_date, page_count, file_path, file_size, user_id)
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
                 region=None, document_id=None, page=1, per_page=20, user_id: int = None):
    """
    Search facts strictly scoped to the authenticated user's documents.
    """
    if user_id is None:
        return {'facts': [], 'total': 0, 'page': 1, 'per_page': per_page, 'total_pages': 1}

    conn = get_db_connection()
    try:
        # Build WHERE clause - enforce ownership on documents table
        conditions = ["d.user_id = ?"]
        params = [user_id]

        if query:
            query_clean = query.strip()
            if (query_clean.startswith('"') and query_clean.endswith('"')) or (query_clean.startswith("'") and query_clean.endswith("'")):
                exact = query_clean[1:-1].strip()
                conditions.append("(f.fact_text LIKE ? OR f.original_text LIKE ? OR f.crop_name LIKE ? OR f.category LIKE ?)")
                params.extend([f"%{exact}%", f"%{exact}%", f"%{exact}%", f"%{exact}%"])
            else:
                tokens = [t for t in query_clean.split() if t]
                for t in tokens:
                    conditions.append(
                        "(f.fact_text LIKE ? OR f.original_text LIKE ? OR f.crop_name LIKE ? OR f.category LIKE ? OR f.season LIKE ? OR f.region LIKE ?)"
                    )
                    like_t = f"%{t}%"
                    params.extend([like_t, like_t, like_t, like_t, like_t, like_t])

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


def get_fact_by_id(fact_id: int, user_id: int = None):
    """
    Get a single fact with its document info and page text, enforcing ownership.
    Returns None if fact does not exist or does not belong to user_id.
    """
    if user_id is None:
        return None

    conn = get_db_connection()
    try:
        cursor = conn.cursor()

        # Get fact with document info, strictly scoped to user_id
        cursor.execute("""
            SELECT f.*, d.filename, d.file_hash, d.version as document_version,
                   d.upload_date, d.user_id
            FROM facts f
            JOIN documents d ON f.document_id = d.id
            WHERE f.id = ? AND d.user_id = ?
        """, (fact_id, user_id))
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


def get_document_by_id(document_id: int, user_id: int = None):
    """
    Get document info with list of its pages and fact counts, enforcing ownership.
    Returns None if document does not exist or does not belong to user_id.
    """
    if user_id is None:
        return None

    conn = get_db_connection()
    try:
        cursor = conn.cursor()

        # Get document strictly scoped to user_id
        cursor.execute("SELECT * FROM documents WHERE id = ? AND user_id = ?", (document_id, user_id))
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


def get_all_documents(user_id: int = None):
    """
    List all documents belonging strictly to the authenticated user.
    """
    if user_id is None:
        return []

    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT d.*, COUNT(f.id) as fact_count
            FROM documents d
            LEFT JOIN facts f ON d.id = f.document_id
            WHERE d.user_id = ?
            GROUP BY d.id
            ORDER BY d.upload_date DESC
        """, (user_id,))
        return [dict(row) for row in cursor.fetchall()]
    finally:
        conn.close()


def get_page_text(document_id: int, page_number: int, user_id: int = None):
    """
    Get raw text of a specific page, verifying document ownership if user_id is provided.
    """
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        if user_id is not None:
            cursor.execute("SELECT id FROM documents WHERE id = ? AND user_id = ?", (document_id, user_id))
            if not cursor.fetchone():
                return ''

        cursor.execute(
            "SELECT page_text FROM page_texts WHERE document_id = ? AND page_number = ?",
            (document_id, page_number)
        )
        row = cursor.fetchone()
        return row['page_text'] if row else ''
    finally:
        conn.close()


def get_stats(user_id: int = None):
    """
    Get statistics scoped strictly to the authenticated user's documents.
    """
    if user_id is None:
        return {
            'total_documents': 0,
            'total_facts': 0,
            'total_pages': 0,
            'categories': [],
            'crops': [],
            'seasons': [],
        }

    conn = get_db_connection()
    try:
        cursor = conn.cursor()

        cursor.execute("SELECT COUNT(*) as c FROM documents WHERE user_id = ?", (user_id,))
        total_documents = cursor.fetchone()['c']

        cursor.execute(
            "SELECT COUNT(*) as c FROM facts f JOIN documents d ON f.document_id = d.id WHERE d.user_id = ?",
            (user_id,)
        )
        total_facts = cursor.fetchone()['c']

        cursor.execute(
            "SELECT COUNT(*) as c FROM page_texts pt JOIN documents d ON pt.document_id = d.id WHERE d.user_id = ?",
            (user_id,)
        )
        total_pages = cursor.fetchone()['c']

        categories = get_distinct_values('category', user_id=user_id)
        crops = get_distinct_values('crop_name', user_id=user_id)
        seasons = get_distinct_values('season', user_id=user_id)

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


def get_distinct_values(column: str, user_id: int = None):
    """
    Get distinct non-null values for a column, scoped strictly to the authenticated user.
    """
    allowed_columns = {'crop_name', 'category', 'season', 'region', 'unit'}
    if column not in allowed_columns:
        raise ValueError(f"Column '{column}' not allowed. Must be one of {allowed_columns}")

    if user_id is None:
        return []

    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        cursor.execute(
            f"""SELECT DISTINCT f.{column}
                FROM facts f
                JOIN documents d ON f.document_id = d.id
                WHERE f.{column} IS NOT NULL AND d.user_id = ?
                ORDER BY f.{column}""",
            (user_id,)
        )
        return [row[0] for row in cursor.fetchall()]
    finally:
        conn.close()


def delete_document(document_id: int, user_id: int = None):
    """
    Delete a document and all its associated facts and page texts, strictly enforcing ownership.
    Returns (True, file_path) if deleted, or (False, None) if not found or unauthorized.
    """
    if user_id is None:
        return False, None

    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        # Find document owned by user_id
        cursor.execute("SELECT id, file_path FROM documents WHERE id = ? AND user_id = ?", (document_id, user_id))
        row = cursor.fetchone()
        if not row:
            return False, None

        file_path = row['file_path']
        cursor.execute("DELETE FROM documents WHERE id = ? AND user_id = ?", (document_id, user_id))
        conn.commit()
        return True, file_path
    finally:
        conn.close()


def get_document_facts(document_id: int, category=None, page_number=None, user_id: int = None):
    """
    Get facts for a document, enforcing ownership if user_id is provided.
    """
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        if user_id is not None:
            cursor.execute("SELECT id FROM documents WHERE id = ? AND user_id = ?", (document_id, user_id))
            if not cursor.fetchone():
                return []

        conditions = ["document_id = ?"]
        params = [document_id]

        if category:
            conditions.append("category = ?")
            params.append(category)
        if page_number:
            conditions.append("page_number = ?")
            params.append(page_number)

        where_clause = " AND ".join(conditions)
        cursor.execute(
            f"SELECT * FROM facts WHERE {where_clause} ORDER BY page_number, id",
            params
        )
        return [dict(row) for row in cursor.fetchall()]
    finally:
        conn.close()


def get_search_autocomplete(query: str, user_id: int = None, limit: int = 8) -> list:
    """
    Generate autocomplete suggestions scoped strictly to the authenticated user.
    Standard agronomic catalog keywords are suggested, but database-derived suggestions
    only query the user's private documents.
    """
    import re

    if not query or not query.strip() or user_id is None:
        return []

    raw_tokens = [w.strip() for w in query.split() if w.strip()]
    if not raw_tokens:
        return []

    tokens = [t.lower() for t in raw_tokens]
    query_lower = query.strip().lower()

    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        suggestions = []
        seen = set()
        stopwords = {
            'and', 'to', 'for', 'of', 'in', 'on', 'at', 'with', 'by', 'from',
            'is', 'are', 'the', 'a', 'an', 'or', 'as', 'into', 'than', 'this'
        }

        def add_suggestion(phrase, score=0):
            if not phrase:
                return
            clean = re.sub(r'^[•\-\*\d\.\:\s]+', '', phrase).strip()
            clean = re.sub(r'\s+', ' ', clean)
            clean = re.sub(r'[,;:\.\-]+$', '', clean).strip()

            words = clean.split()
            while words and words[0].lower() in stopwords:
                words.pop(0)
            while words and words[-1].lower() in stopwords:
                words.pop()

            if not words or len(words) > 7:
                return

            clean = ' '.join(words)
            if len(clean) < 3 or len(clean) > 55:
                return
            if clean.lower() == query_lower and len(words) == 1:
                return

            title = ' '.join(w.capitalize() if not (w.isupper() and len(w) > 1) else w for w in words)
            key = title.lower()
            if key not in seen:
                seen.add(key)
                if key.startswith(query_lower):
                    score += 150
                elif query_lower in key:
                    score += 50
                suggestions.append((score, title))

        # Core standard agricultural entities for instant accurate suggestions
        agri_catalog = [
            'Wheat', 'Rice', 'Paddy', 'Maize', 'Bajra', 'Jowar', 'Barley', 'Ragi',
            'Gram', 'Chickpea', 'Moong', 'Urad', 'Arhar', 'Pigeon Pea', 'Lentil', 'Pea',
            'Mustard', 'Groundnut', 'Soybean', 'Sunflower', 'Sesame',
            'Cotton', 'Sugarcane', 'Jute', 'Tobacco', 'Tea', 'Coffee',
            'Potato', 'Tomato', 'Onion', 'Okra', 'Brinjal', 'Cauliflower', 'Carrot',
            'Fertilizer', 'Fertilizer Dose', 'Fertilizer Management',
            'Irrigation', 'Irrigation Stages', 'Water Management',
            'Pest Control', 'Pest Management', 'Disease Management',
            'Seed Rate', 'Seed Treatment', 'Varieties',
            'Soil Preparation', 'Soil pH Range', 'Expected Yield', 'Sowing Time',
            'Urea', 'DAP', 'MOP', 'NPK Ratio', 'Zinc Sulphate', 'Nitrogen Dose',
            'FYM', 'Compost', 'Vermicompost', 'Propiconazole', 'Imidacloprid',
            'Yellow Rust', 'Leaf Rust', 'Karnal Bunt', 'Loose Smut',
            'Stem Borer', 'Blast Disease', 'Sheath Blight', 'Brown Plant Hopper',
            'Rabi Season', 'Kharif Season', 'Zaid Season'
        ]

        # ── Case A: Single-word / Prefix search ──────────────────────────────
        if len(raw_tokens) == 1:
            prefix = raw_tokens[0].lower()

            for item in agri_catalog:
                if item.lower().startswith(prefix):
                    add_suggestion(item, score=120)
                elif prefix in item.lower():
                    add_suggestion(item, score=30)

            # Match from user's distinct crops in DB
            cursor.execute(
                """SELECT DISTINCT f.crop_name
                   FROM facts f JOIN documents d ON f.document_id = d.id
                   WHERE LOWER(f.crop_name) LIKE ? AND d.user_id = ?
                   LIMIT 10""",
                (f"{prefix}%", user_id)
            )
            for row in cursor.fetchall():
                crop = row['crop_name']
                if crop:
                    add_suggestion(crop, score=140)
                    for topic in ['Fertilizer', 'Varieties', 'Irrigation', 'Seed Rate']:
                        add_suggestion(f"{crop} {topic}", score=80)

            # Match from user's distinct categories in DB
            cursor.execute(
                """SELECT DISTINCT f.category
                   FROM facts f JOIN documents d ON f.document_id = d.id
                   WHERE LOWER(f.category) LIKE ? AND d.user_id = ?
                   LIMIT 10""",
                (f"{prefix}%", user_id)
            )
            for row in cursor.fetchall():
                cat = row['category']
                if cat:
                    add_suggestion(cat, score=110)

            # Search distinct matching words from user's facts in DB
            cursor.execute(
                """SELECT f.fact_text
                   FROM facts f JOIN documents d ON f.document_id = d.id
                   WHERE LOWER(f.fact_text) LIKE ? AND d.user_id = ?
                   LIMIT 30""",
                (f"%{prefix}%", user_id)
            )
            for row in cursor.fetchall():
                words = re.sub(r'[^\w\s-]', ' ', row['fact_text']).split()
                for i, w in enumerate(words):
                    if w.lower().startswith(prefix) and len(w) > len(prefix):
                        add_suggestion(w, score=70)
                        if i + 1 < len(words):
                            add_suggestion(f"{w} {words[i+1]}", score=60)

        # ── Case B: Multi-word search ────────────────────────────────────────
        else:
            clauses = []
            params = []
            for t in tokens:
                clauses.append("(f.fact_text LIKE ? OR f.crop_name LIKE ? OR f.category LIKE ? OR f.original_text LIKE ?)")
                params.extend([f"%{t}%", f"%{t}%", f"%{t}%", f"%{t}%"])

            sql = f"""
                SELECT DISTINCT f.crop_name, f.category, f.fact_text, f.season, f.region
                FROM facts f
                JOIN documents d ON f.document_id = d.id
                WHERE {' AND '.join(clauses)} AND d.user_id = ?
                LIMIT 80
            """
            cursor.execute(sql, params + [user_id])
            rows = cursor.fetchall()

            for item in agri_catalog:
                item_lower = item.lower()
                if all(t in item_lower for t in tokens):
                    add_suggestion(item, score=110)

            for row in rows:
                crop = row['crop_name']
                cat = row['category']
                season = row['season']
                if crop and cat:
                    combo = f"{crop} {cat}"
                    if all(t in combo.lower() for t in tokens):
                        add_suggestion(combo, score=100)
                if crop and season:
                    combo = f"{crop} {season} Season"
                    if all(t in combo.lower() for t in tokens):
                        add_suggestion(combo, score=90)

        suggestions.sort(key=lambda x: (-x[0], len(x[1])))
        return [s[1] for s in suggestions[:limit]]
    finally:
        conn.close()
