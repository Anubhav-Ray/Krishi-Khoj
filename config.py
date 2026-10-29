"""Configuration for Krishi Khoj application."""
import os

BASE_DIR = os.path.abspath(os.path.dirname(__file__))

# File storage
UPLOAD_FOLDER = os.path.join(BASE_DIR, 'uploads')
DATABASE_PATH = os.path.join(BASE_DIR, 'krishi_khoj.db')

# Upload limits
MAX_CONTENT_LENGTH = 50 * 1024 * 1024  # 50 MB
ALLOWED_EXTENSIONS = {'pdf'}

# App settings
SECRET_KEY = 'krishi-khoj-dev-key-change-in-production'
DEBUG = True
