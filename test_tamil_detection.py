#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import re
import sys

# Ensure UTF-8 output
if sys.stdout.encoding != 'utf-8':
    sys.stdout.reconfigure(encoding='utf-8')

# Test Tamil detection
test_texts = [
    "பதிவு செய்ய எப்படி",
    "How can I join the program",
    "நிரல் சேர்க விவரங்கள் என்ன"
]

enrollment_keywords_ta = [
    'சேர',      # join (base form)
    'சேர்',      # join (alternate)
    'சேரண',     # should join
    'சேரணும்',   # should join
    'சேர்ந்து',   # joined
    'சேர்த்து',   # added
    'சேர்க்க',   # to join
    'சேர்க',     # join
    'பங்கு',     # participate/share
    'மாணவ',     # student
    'பதிவு',     # registration
    'வேண்டும்',  # need/want
    'எப்படி',    # how
    'விவரம்',    # details
    'விபரம்',    # information
    'விண்ணப்பம்', # application
    'கட்ணம்',    # fees
    'கோரி',      # ask for
    'செலவு',     # cost
    'பணம்',      # money
    'ஜாயின்',    # join (English in Tamil script)
    'எனரோல்',   # enroll (English in Tamil script)
    'ரெஜிஸ்டர்', # register (English in Tamil script)
    'கோர்ஸ்',    # course (English in Tamil script)
    'பாடம்',     # course/lesson
    'கல்வி',     # education
]

for text in test_texts:
    print(f"\n--- Testing: '{text}' ---")

    # Check if Tamil characters
    has_tamil = re.search(r'[\u0B80-\u0BFF]', text)
    print(f"Has Tamil characters: {bool(has_tamil)}")

    # Check for keyword matches
    found_keywords = []
    for keyword in enrollment_keywords_ta:
        if keyword in text:
            found_keywords.append(keyword)

    if found_keywords:
        print(f"✓ Found keywords: {found_keywords}")
    else:
        print("✗ No keywords found")

    # Check if any of the critical keywords match
    critical_keywords = ['சேர', 'பதிவு', 'சேர்', 'சேரணும்', 'விண்ணப்பம்', 'ஜாயின்', 'எனரோல்', 'ரெஜிஸ்டர்', 'கோர்ஸ்']
    matches = [kw for kw in critical_keywords if kw in text]

    if matches:
        print(f"✓ Critical keyword matches: {matches}")
    else:
        print(f"✗ No critical keyword matches")
