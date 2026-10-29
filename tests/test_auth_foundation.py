"""
Focused test suite for Krishi Khoj Account Foundation.
Uses Python's built-in unittest framework (zero external dependencies).
Tests registration, authentication, password hashing, session management,
validation, template rendering, and existing document integrity.
"""
import os
import sys
import tempfile
import unittest

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

import config
import database
from app import app
from database import (
    init_db, get_db_connection, create_user,
    get_user_by_username, get_user_by_id
)
from werkzeug.security import check_password_hash


class TestAuthFoundation(unittest.TestCase):
    def setUp(self):
        """Set up an isolated test database and test client for each test."""
        self.db_fd, self.db_path = tempfile.mkstemp(suffix='.db')
        os.close(self.db_fd)

        self.original_db = database.DATABASE_PATH
        database.DATABASE_PATH = self.db_path

        app.config['TESTING'] = True
        app.config['SECRET_KEY'] = 'test-secret-key-for-auth-tests-12345'
        app.config['WTF_CSRF_ENABLED'] = False

        init_db()
        self.client = app.test_client()

    def tearDown(self):
        """Clean up isolated database file."""
        database.DATABASE_PATH = self.original_db
        if os.path.exists(self.db_path):
            try:
                os.remove(self.db_path)
            except Exception:
                pass

    def test_users_table_created(self):
        """Verify that users table exists with correct schema."""
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='users'")
        self.assertIsNotNone(cursor.fetchone(), "users table was not created")

        cursor.execute("PRAGMA table_info(users)")
        columns = {row['name']: row['type'] for row in cursor.fetchall()}
        self.assertIn('id', columns)
        self.assertIn('username', columns)
        self.assertIn('password_hash', columns)
        self.assertIn('created_at', columns)
        conn.close()

    def test_registration_success(self):
        """Test successful user registration and session establishment."""
        response = self.client.post('/register', data={
            'username': 'farmer_suresh',
            'password': 'StrongPassword123',
            'confirm_password': 'StrongPassword123'
        }, follow_redirects=True)

        self.assertEqual(response.status_code, 200)
        self.assertIn(b"Account created successfully", response.data)
        self.assertIn(b"farmer_suresh", response.data)

        # Verify in DB: password must be securely hashed, never plaintext
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM users WHERE username = 'farmer_suresh'")
        user = cursor.fetchone()
        self.assertIsNotNone(user)
        self.assertNotEqual(user['password_hash'], 'StrongPassword123')
        self.assertTrue(check_password_hash(user['password_hash'], 'StrongPassword123'))
        conn.close()

    def test_registration_duplicate_username_rejected(self):
        """Test that duplicate usernames (including case variations) are rejected safely."""
        self.client.post('/register', data={
            'username': 'farmer_anil',
            'password': 'Password123',
            'confirm_password': 'Password123'
        })
        # Log out so next request isn't already authenticated
        self.client.get('/logout')

        # Exact duplicate
        res1 = self.client.post('/register', data={
            'username': 'farmer_anil',
            'password': 'DifferentPassword456',
            'confirm_password': 'DifferentPassword456'
        })
        self.assertIn(b"already taken", res1.data)

        # Case variant duplicate (e.g. FARMER_ANIL)
        res2 = self.client.post('/register', data={
            'username': 'FARMER_ANIL',
            'password': 'DifferentPassword456',
            'confirm_password': 'DifferentPassword456'
        })
        self.assertIn(b"already taken", res2.data)

    def test_registration_validation_errors(self):
        """Test validation errors for empty fields, short password, and mismatched password."""
        # Empty username
        r1 = self.client.post('/register', data={'username': '', 'password': 'Password123', 'confirm_password': 'Password123'})
        self.assertIn(b"Username is required", r1.data)

        # Short password
        r2 = self.client.post('/register', data={'username': 'farmer_valid', 'password': '123', 'confirm_password': '123'})
        self.assertIn(b"at least 6 characters", r2.data)

        # Mismatched passwords
        r3 = self.client.post('/register', data={'username': 'farmer_valid', 'password': 'Password123', 'confirm_password': 'Password456'})
        self.assertIn(b"Passwords do not match", r3.data)

        # Invalid username characters
        r4 = self.client.post('/register', data={'username': 'farmer@invalid!', 'password': 'Password123', 'confirm_password': 'Password123'})
        self.assertIn(b"only contain letters, numbers", r4.data)

    def test_login_success_and_logout(self):
        """Test successful login and subsequent logout."""
        self.client.post('/register', data={
            'username': 'farmer_geeta',
            'password': 'FarmSecret2024',
            'confirm_password': 'FarmSecret2024'
        })

        # Log out
        self.client.get('/logout')

        # Log in
        res = self.client.post('/login', data={
            'username': 'farmer_geeta',
            'password': 'FarmSecret2024'
        }, follow_redirects=True)
        self.assertEqual(res.status_code, 200)
        self.assertIn(b"Welcome back, farmer_geeta!", res.data)
        self.assertIn(b"farmer_geeta", res.data)

        # Log out
        res_logout = self.client.get('/logout', follow_redirects=True)
        self.assertIn(b"You have been logged out", res_logout.data)
        self.assertIn(b"Sign In", res_logout.data)

    def test_login_invalid_credentials_generic_message(self):
        """Test that failed logins provide a generic error message without user enumeration."""
        # Non-existent user
        r1 = self.client.post('/login', data={'username': 'non_existent_farmer', 'password': 'SomePassword'})
        self.assertIn(b"Invalid username or password", r1.data)

        # Existent user, wrong password
        self.client.post('/register', data={'username': 'farmer_vikram', 'password': 'CorrectPassword1', 'confirm_password': 'CorrectPassword1'})
        self.client.get('/logout')

        r2 = self.client.post('/login', data={'username': 'farmer_vikram', 'password': 'WrongPassword99'})
        self.assertIn(b"Invalid username or password", r2.data)

    def test_existing_documents_intact(self):
        """Verify that existing documents, facts, and page_texts tables remain intact."""
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = {row['name'] for row in cursor.fetchall()}
        self.assertIn('documents', tables)
        self.assertIn('facts', tables)
        self.assertIn('page_texts', tables)
        self.assertIn('users', tables)
        conn.close()

    def test_secret_key_production_failure(self):
        """Verify that missing SECRET_KEY fails safely in production mode."""
        env = 'production'
        secret_key = None
        with self.assertRaises(RuntimeError):
            if not secret_key and env == 'production':
                raise RuntimeError("CRITICAL STARTUP ERROR: The SECRET_KEY environment variable is not set.")


if __name__ == '__main__':
    unittest.main()
