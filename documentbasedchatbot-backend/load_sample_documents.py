#!/usr/bin/env python3
"""
Load sample documents into the database for the chatbot.
Run this script to populate the database with health information documents.
"""

import os
import sys
import uuid
from datetime import datetime
from pathlib import Path

# Fix Unicode encoding for Windows console
if sys.platform == 'win32':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

# Add the backend directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Load environment variables
from dotenv import load_dotenv
env_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env")
load_dotenv(env_path, override=True)

from src.database import SessionLocal, init_db
from src.models.document import Document


def load_sample_documents():
    """Load sample documents from the uploads directory into the database."""

    # Initialize database
    print("Initializing database...")
    init_db()

    # Get database session
    db = SessionLocal()

    try:
        # Document files to load
        documents_to_load = [
            {
                "path": "uploads/MyHealthSchool_KnowledgeBase.txt",
                "title": "My Health School - Type 2 Diabetes Reversal Program",
                "type": "document"
            },
            {
                "path": "uploads/sample_health_info.txt",
                "title": "Sample Health Information",
                "type": "document"
            }
        ]

        # Check if backend directory needs to be changed
        backend_dir = os.path.dirname(os.path.abspath(__file__))

        for doc_info in documents_to_load:
            doc_path = os.path.join(backend_dir, doc_info["path"])

            # Check if file exists
            if not os.path.exists(doc_path):
                print(f"Warning: File not found: {doc_path}")
                continue

            print(f"\nLoading document: {doc_info['title']}")
            print(f"   Path: {doc_path}")

            # Read file content
            try:
                with open(doc_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                print(f"   Size: {len(content)} characters")
            except Exception as e:
                print(f"   Error reading file: {e}")
                continue

            # Check if document already exists
            existing = db.query(Document).filter(
                Document.title == doc_info['title']
            ).first()

            if existing:
                # Update existing document
                print(f"   Updating existing document...")
                try:
                    existing.content = content
                    if hasattr(existing, 'file_path'):
                        existing.file_path = doc_path
                    if hasattr(existing, 'storage_path'):
                        existing.storage_path = doc_path
                    existing.file_name = os.path.basename(doc_path)
                    db.commit()
                    print(f"   Updated document ID: {existing.id}")
                except Exception as e:
                    print(f"   Error updating: {e}")
                    db.rollback()
            else:
                # Create new document
                doc_id = str(uuid.uuid4())
                try:
                    new_doc = Document(
                        id=doc_id,
                        title=doc_info['title'],
                        type=doc_info['type'],
                        file_name=os.path.basename(doc_path),
                        content=content
                    )
                    # Set file_path if column exists, otherwise storage_path
                    if hasattr(new_doc, 'file_path'):
                        new_doc.file_path = doc_path
                    if hasattr(new_doc, 'storage_path'):
                        new_doc.storage_path = doc_path

                    db.add(new_doc)
                    db.commit()
                    print(f"   Created document ID: {doc_id}")
                except Exception as e:
                    print(f"   Error creating: {e}")
                    db.rollback()

        # List all documents in database
        print("\n" + "="*60)
        print("Documents in Database:")
        print("="*60)

        all_docs = db.query(Document).all()

        if all_docs:
            for doc in all_docs:
                content_preview = doc.content[:100].replace('\n', ' ') if doc.content else "(no content)"
                print(f"\n  {doc.title}")
                print(f"     ID: {doc.id}")
                print(f"     Type: {doc.type}")
                print(f"     Content size: {len(doc.content) if doc.content else 0} chars")
                print(f"     Content preview: {content_preview}...")
        else:
            print("\n  No documents in database")

        print("\nDocument loading complete!")

    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        db.close()


if __name__ == "__main__":
    load_sample_documents()
