#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os

# Test paths
paths = [
    "E:\\new downloads\\Documentbasedchatbot\\documentbasedchatbot-backend\\uploads\\MyHealthSchool_KnowledgeBase.txt",
    "E:/new downloads/Documentbasedchatbot/documentbasedchatbot-backend/uploads/MyHealthSchool_KnowledgeBase.txt",
    os.path.join("E:", "new downloads", "Documentbasedchatbot", "documentbasedchatbot-backend", "uploads", "MyHealthSchool_KnowledgeBase.txt"),
]

for i, path in enumerate(paths, 1):
    print(f"\n--- Path {i} ---")
    print(f"Path: {path}")

    if os.path.exists(path):
        print("[OK] File exists")
        try:
            with open(path, 'r', encoding='utf-8') as f:
                content = f.read()
                print(f"[OK] File readable - {len(content)} characters")
        except Exception as e:
            print(f"[ERROR] {e}")
    else:
        print("[FAIL] File NOT found")
        parent = os.path.dirname(path)
        print(f"[INFO] Parent exists: {os.path.exists(parent)}")
        if os.path.exists(parent):
            print(f"[INFO] Files in parent: {os.listdir(parent)[:5]}")
