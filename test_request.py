#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import requests
import json
import sys

# Ensure UTF-8 handling
if sys.stdout.encoding != 'utf-8':
    sys.stdout.reconfigure(encoding='utf-8')

# Test queries
test_queries = [
    ("English enrollment", "How can I join the program"),
    ("Tamil registration", "பதிவு செய்ய எப்படி"),
    ("Tamil program join", "நிரல் சேர்க விவரங்கள் என்ன"),
]

backend_url = "http://localhost:8001/ask"

for test_name, question in test_queries:
    print(f"\n{'='*60}")
    print(f"Test: {test_name}")
    print(f"Question: {question}")
    print(f"{'='*60}")

    try:
        # Send request with explicit UTF-8 encoding
        response = requests.post(
            backend_url,
            json={"question": question, "mode": "health"},
            headers={"Content-Type": "application/json; charset=utf-8"}
        )

        if response.status_code == 200:
            result = response.json()
            print(f"Response Type: {result.get('type')}")
            print(f"Answer (first 100 chars): {result.get('answer', '')[:100]}")
        else:
            print(f"Error: {response.status_code}")
            print(f"Response: {response.text}")

    except Exception as e:
        print(f"Exception: {e}")
