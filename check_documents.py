#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import sys
import os
from dotenv import load_dotenv

# Load .env file first
env_path = "E:\\new downloads\\Documentbasedchatbot\\documentbasedchatbot-backend\\.env"
load_dotenv(env_path)

# Add backend to path
sys.path.insert(0, "E:\\new downloads\\Documentbasedchatbot\\documentbasedchatbot-backend")

# Set UTF-8 encoding
if sys.stdout.encoding != 'utf-8':
    sys.stdout.reconfigure(encoding='utf-8')

try:
    from src.repository.admin_repo import AdminRepository

    print("Creating repository...")
    repo = AdminRepository()

    print(f"[INFO] Loaded documents count: {len(repo.documents)}")

    for doc_id, doc in repo.documents.items():
        print(f"\n[INFO] Document: {doc['title']}")
        print(f"[INFO] File path: {doc.get('file_path')}")

        if doc.get("file_path"):
            import os
            exists = os.path.exists(doc['file_path'])
            print(f"[INFO] File exists: {exists}")

    print("\nGetting documents content...")
    content = repo.get_documents_content()

    if content:
        print("[OK] Documents found!")
        print(f"Content length: {len(content)} characters")
        print(f"\nFirst 500 characters:\n{content[:500]}")
    else:
        print("[FAIL] No documents found in repository")
        print(f"Total documents in dict: {len(repo.documents)}")

except Exception as e:
    print(f"[ERROR] {str(e)}")
    import traceback
    traceback.print_exc()
