"""
Configuration settings for the application.
"""

import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# File Upload Settings
MAX_FILE_SIZE_MB = 50  # Maximum file size in MB
MAX_FILE_SIZE_BYTES = MAX_FILE_SIZE_MB * 1024 * 1024
ALLOWED_UPLOAD_EXTENSIONS = ['pdf', 'docx', 'txt', 'doc']

# Database Settings
DATABASE_URL = os.getenv('DATABASE_URL')

# API Settings
API_TITLE = "Document-Based Q&A Voice Chatbot API"
API_VERSION = "1.0.0"
API_DESCRIPTION = "A FastAPI backend leveraging LangChain to answer questions purely based on uploaded documents."

# CORS Settings
ALLOWED_ORIGINS = [
    "http://localhost:5175",
    "http://localhost:5173",
    "http://127.0.0.1:5175",
    "http://127.0.0.1:5173",
]

# Security Settings
MIN_QUESTION_LENGTH = 3
MAX_QUESTION_LENGTH = 5000
MAX_DOCUMENT_CHUNK_SIZE = 10000

# LLM Settings
GEMINI_MODEL = "gemini-2.5-flash-lite"
TEMPERATURE = 0.7
MAX_TOKENS = 2000

# Rate Limiting (requests per minute)
RATE_LIMIT_ENABLED = True
RATE_LIMIT_PER_MINUTE = 60  # Default: 60 requests per minute per IP

# Logging
LOG_LEVEL = os.getenv('LOG_LEVEL', 'INFO')
