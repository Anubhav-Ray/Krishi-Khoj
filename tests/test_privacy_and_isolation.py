"""
Focused test suite for Strict Per-User Privacy & Document Isolation.
Verifies that:
1. Unauthenticated users cannot access any private pages or APIs.
2. User A's documents, facts, page texts, and search results are strictly inaccessible to User B.
3. Direct Object Reference (IDOR) attempts on /document/<id>, /fact/<id>, and /document/<id>/delete return safe 404s.
4. Search, stats, autocomplete, and exports never leak data across users.
5. Old legacy documents with NULL user_id are preserved in DB but inaccessible to ordinary accounts.
"""
import os
import sys
import tempfile
import unittest

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

import database
from app import app
from database import (
    init_db, get_db_connection, create_user,
    insert_document, insert_fact, insert_page_text
)
from werkzeug.security import generate_password_hash


class TestPrivacyAndIsolation(unittest.TestCase):
    def setUp(self):
        """Set up an isolated test database and test client for each test."""
        self.db_fd, self.db_path = tempfile.mkstemp(suffix='.db')
        os.close(self.db_fd)

        self.original_db = database.DATABASE_PATH
        database.DATABASE_PATH = self.db_path

        app.config['TESTING'] = True
        app.config['SECRET_KEY'] = 'test-secret-key-for-privacy-tests-12345'
        app.config['WTF_CSRF_ENABLED'] = False

        init_db()
        self.client = app.test_client()

        # Create two distinct test users
        self.user_a_id = create_user('farmer_a', generate_password_hash('PasswordA123'))
        self.user_b_id = create_user('farmer_b', generate_password_hash('PasswordB123'))

    def tearDown(self):
        """Clean up isolated database file."""
        database.DATABASE_PATH = self.original_db
        if os.path.exists(self.db_path):
            try:
                os.remove(self.db_path)
            except Exception:
                pass

    def login_as(self, username, password):
        """Helper to log in as a specific user."""
        return self.client.post('/login', data={
            'username': username,
            'password': password
        }, follow_redirects=True)

    def logout(self):
        """Helper to log out."""
        return self.client.get('/logout', follow_redirects=True)

    def test_unauthenticated_access_blocked(self):
        """Verify all private views and APIs require login."""
        # HTML routes redirect to login
        for path in ['/', '/search', '/documents', '/document/1', '/fact/1']:
            res = self.client.get(path)
            self.assertEqual(res.status_code, 302, f"{path} did not redirect unauthenticated user")
            self.assertIn('/login', res.headers.get('Location', ''))

        # API routes return 401 Unauthorized
        for api_path in ['/api/autocomplete?q=wh', '/api/search', '/api/stats', '/api/documents', '/api/export']:
            res = self.client.get(api_path)
            self.assertEqual(res.status_code, 401, f"{api_path} did not return 401 for unauthenticated user")

    def test_user_a_document_isolation_from_user_b(self):
        """Verify User A's uploaded document and stats are invisible to User B."""
        # Insert a document owned by User A
        doc_a = insert_document(
            filename='Wheat_Advisory_UserA.pdf',
            file_hash='sha256_hash_user_a_001',
            page_count=2,
            file_path='/tmp/fake_a.pdf',
            file_size=1024,
            user_id=self.user_a_id
        )
        insert_fact(
            document_id=doc_a['id'],
            crop_name='Wheat',
            category='Fertilizer',
            fact_text='Apply 120 kg N per hectare for HD-2967.',
            value=120.0,
            unit='kg',
            season='Rabi',
            region='Punjab',
            page_number=1,
            original_text='Apply 120 kg N per hectare for HD-2967.',
            extraction_date='2026-10-29T10:00:00Z'
        )

        # Log in as User A: sees 1 document and 1 fact
        self.login_as('farmer_a', 'PasswordA123')
        res_a_docs = self.client.get('/documents')
        self.assertIn(b'Wheat_Advisory_UserA.pdf', res_a_docs.data)
        res_a_stats = self.client.get('/api/stats')
        self.assertEqual(res_a_stats.get_json()['total_documents'], 1)
        self.assertEqual(res_a_stats.get_json()['total_facts'], 1)
        self.logout()

        # Log in as User B: must see 0 documents and 0 facts
        self.login_as('farmer_b', 'PasswordB123')
        res_b_docs = self.client.get('/documents')
        self.assertNotIn(b'Wheat_Advisory_UserA.pdf', res_b_docs.data)
        self.assertIn(b'No documents yet', res_b_docs.data)

        res_b_stats = self.client.get('/api/stats')
        self.assertEqual(res_b_stats.get_json()['total_documents'], 0)
        self.assertEqual(res_b_stats.get_json()['total_facts'], 0)
        self.assertEqual(res_b_stats.get_json()['categories'], [])
        self.logout()

    def test_user_b_cannot_read_user_a_document_idor(self):
        """Verify User B receives safe 404 when directly requesting User A's document ID."""
        doc_a = insert_document(
            filename='Secret_Wheat_A.pdf',
            file_hash='hash_secret_a',
            page_count=1,
            file_path='/tmp/secret_a.pdf',
            file_size=2048,
            user_id=self.user_a_id
        )

        self.login_as('farmer_b', 'PasswordB123')
        # Attempt to access User A's document by ID
        res = self.client.get(f'/document/{doc_a["id"]}')
        self.assertEqual(res.status_code, 404, "User B was able to view User A's document or received non-404")
        self.assertIn(b"Resource Not Found", res.data)
        self.assertNotIn(b"Secret_Wheat_A.pdf", res.data)
        self.logout()

    def test_user_b_cannot_read_user_a_fact_idor(self):
        """Verify User B receives safe 404 when directly requesting User A's fact ID."""
        doc_a = insert_document(
            filename='Secret_Pest_A.pdf',
            file_hash='hash_pest_a',
            page_count=1,
            file_path='/tmp/pest_a.pdf',
            file_size=1024,
            user_id=self.user_a_id
        )
        insert_page_text(doc_a['id'], 1, "Page 1: Proprietary pesticide spray advice for Yellow Rust.")
        fact_id = insert_fact(
            document_id=doc_a['id'],
            crop_name='Wheat',
            category='Pest',
            fact_text='Secret yellow rust spray formula 50ml/l',
            value=50.0,
            unit='ml',
            season='Rabi',
            region='Haryana',
            page_number=1,
            original_text='Secret yellow rust spray formula 50ml/l',
            extraction_date='2026-10-29T10:00:00Z'
        )

        self.login_as('farmer_b', 'PasswordB123')
        res = self.client.get(f'/fact/{fact_id}')
        self.assertEqual(res.status_code, 404, "User B accessed User A's fact details")
        self.assertIn(b"Resource Not Found", res.data)
        self.assertNotIn(b"Secret yellow rust spray", res.data)
        self.logout()

    def test_user_b_cannot_delete_user_a_document(self):
        """Verify User B cannot delete User A's document."""
        doc_a = insert_document(
            filename='Preserve_Me.pdf',
            file_hash='hash_preserve_a',
            page_count=1,
            file_path='/tmp/preserve.pdf',
            file_size=1024,
            user_id=self.user_a_id
        )

        self.login_as('farmer_b', 'PasswordB123')
        # Attempt deletion
        res = self.client.post(f'/document/{doc_a["id"]}/delete')
        self.assertEqual(res.status_code, 404, "Deletion by non-owner did not return 404")
        self.logout()

        # Verify User A's document still exists in DB
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT id FROM documents WHERE id = ?", (doc_a['id'],))
        self.assertIsNotNone(cursor.fetchone(), "Document was deleted by unauthorized user!")
        conn.close()

    def test_search_and_export_strict_isolation(self):
        """Verify User B cannot search or export User A's facts."""
        doc_a = insert_document(
            filename='Rice_UserA.pdf',
            file_hash='hash_rice_a',
            page_count=1,
            file_path='/tmp/rice.pdf',
            file_size=512,
            user_id=self.user_a_id
        )
        insert_fact(
            document_id=doc_a['id'],
            crop_name='Rice',
            category='Seed',
            fact_text='Farmer A SRI seed rate is 6 kg/ha',
            value=6.0,
            unit='kg',
            season='Kharif',
            region='West Bengal',
            page_number=1,
            original_text='Farmer A SRI seed rate is 6 kg/ha',
            extraction_date='2026-10-29T10:00:00Z'
        )

        self.login_as('farmer_b', 'PasswordB123')

        # 1. HTML Search page
        res_search_html = self.client.get('/search?q=Farmer+A')
        self.assertNotIn(b'Farmer A SRI seed rate', res_search_html.data)

        # 2. JSON Search API
        res_search_json = self.client.get('/api/search?q=SRI').get_json()
        self.assertEqual(res_search_json['total'], 0)
        self.assertEqual(len(res_search_json['facts']), 0)

        # 3. Autocomplete API
        res_auto = self.client.get('/api/autocomplete?q=SRI').get_json()
        for suggestion in res_auto['suggestions']:
            self.assertNotIn('Farmer A', suggestion)

        # 4. CSV Export
        res_export = self.client.get('/api/export?format=csv')
        self.assertNotIn(b'Farmer A SRI seed rate', res_export.data)

        self.logout()

    def test_legacy_documents_inaccessible_to_ordinary_users(self):
        """Verify that legacy documents with user_id NULL remain intact in DB but inaccessible to users."""
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute(
            """INSERT INTO documents (filename, file_hash, version, upload_date, page_count, file_path, file_size, user_id)
               VALUES (?, ?, ?, ?, ?, ?, ?, NULL)""",
            ('Legacy_Document_Unassigned.pdf', 'hash_legacy_999', 1, '2024-01-01T00:00:00Z', 1, '/tmp/legacy.pdf', 100)
        )
        legacy_id = cursor.lastrowid
        conn.commit()
        conn.close()

        # Log in as User A
        self.login_as('farmer_a', 'PasswordA123')
        # Attempt to access legacy doc
        res_detail = self.client.get(f'/document/{legacy_id}')
        self.assertEqual(res_detail.status_code, 404, "Ordinary user accessed unassigned legacy document")

        res_docs = self.client.get('/documents')
        self.assertNotIn(b'Legacy_Document_Unassigned.pdf', res_docs.data)

        # Legacy document must still be intact in DB
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT id, filename FROM documents WHERE id = ?", (legacy_id,))
        legacy_row = cursor.fetchone()
        self.assertIsNotNone(legacy_row)
        self.assertEqual(legacy_row['filename'], 'Legacy_Document_Unassigned.pdf')
        conn.close()


if __name__ == '__main__':
    unittest.main()
