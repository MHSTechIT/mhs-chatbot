#!/usr/bin/env python3
"""
Migration script to add missing file_path column to documents table.
This script runs before loading sample documents.
"""

import os
import sys

# Fix Unicode encoding for Windows console
if sys.platform == 'win32':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

# Add backend directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Load environment variables
from dotenv import load_dotenv
env_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env")
load_dotenv(env_path, override=True)

from sqlalchemy import inspect, Column, String, text
from src.database import _get_engine
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def add_missing_columns():
    """Add missing columns to documents table if they don't exist."""

    engine = _get_engine()
    if not engine:
        print("Failed to connect to database")
        return False

    try:
        # Check if file_path column exists
        with engine.connect() as connection:
            inspector = inspect(connection)

            # Get existing columns
            columns = [col['name'] for col in inspector.get_columns('documents')]
            print(f"Existing columns in documents table: {columns}")

            # Add file_path column if missing
            if 'file_path' not in columns:
                print("Adding file_path column...")
                connection.execute(text("""
                    ALTER TABLE documents
                    ADD COLUMN file_path VARCHAR(500) NULL
                """))
                connection.commit()
                print("OK - file_path column added")
            else:
                print("OK - file_path column already exists")

            # Add url column if missing
            if 'url' not in columns:
                print("Adding url column...")
                connection.execute(text("""
                    ALTER TABLE documents
                    ADD COLUMN url VARCHAR(500) NULL
                """))
                connection.commit()
                print("OK - url column added")
            else:
                print("OK - url column already exists")

            # Add content column if missing
            if 'content' not in columns:
                print("Adding content column...")
                connection.execute(text("""
                    ALTER TABLE documents
                    ADD COLUMN content TEXT NULL
                """))
                connection.commit()
                print("OK - content column added")
            else:
                print("OK - content column already exists")

        print("\nMigration complete!")
        return True

    except Exception as e:
        print(f"Migration error: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = add_missing_columns()
    sys.exit(0 if success else 1)
