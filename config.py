"""Configuration for Krishi Khoj application."""
import os
import sys
import secrets

BASE_DIR = os.path.abspath(os.path.dirname(__file__))

# File storage
UPLOAD_FOLDER = os.path.join(BASE_DIR, 'uploads')
DATABASE_PATH = os.path.join(BASE_DIR, 'krishi_khoj.db')

# Upload limits
MAX_CONTENT_LENGTH = 50 * 1024 * 1024  # 50 MB
ALLOWED_EXTENSIONS = {'pdf'}

# Environment & Debug settings
ENV = os.environ.get('FLASK_ENV', 'development').lower()
DEBUG = False  # Debug mode disabled for prototype safety

# Secret Key Configuration
# Fails safely with a clear error if running in production without SECRET_KEY.
# In development, avoids known static secrets by generating an ephemeral cryptographically strong key
# and printing an explicit notice to stderr.
SECRET_KEY = os.environ.get('SECRET_KEY')
if not SECRET_KEY:
    if ENV == 'production' or os.environ.get('ENVIRONMENT', '').lower() == 'production':
        raise RuntimeError(
            "CRITICAL STARTUP ERROR: The SECRET_KEY environment variable is not set. "
            "Krishi Khoj will not start in production mode without an explicit, secure SECRET_KEY."
        )
    else:
        SECRET_KEY = secrets.token_hex(32)
        print(
            "⚠️ [Krishi Khoj Security Notice] SECRET_KEY environment variable not set. "
            "Generated an ephemeral 256-bit random secret for this session. "
            "Set SECRET_KEY in your environment for persistent user sessions across restarts.",
            file=sys.stderr
        )

# Session Security Settings
SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_SAMESITE = 'Lax'
SESSION_COOKIE_SECURE = os.environ.get('SESSION_COOKIE_SECURE', 'False').lower() in ('true', '1')
PERMANENT_SESSION_LIFETIME = 86400 * 7  # 7 days in seconds
