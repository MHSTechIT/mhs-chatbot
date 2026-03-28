import os
import sys
sys.path.insert(0, str(os.getcwd()))
from dotenv import load_dotenv

load_dotenv(".env")
google_api_key = os.getenv("GOOGLE_API_KEY")
print(f"API Key: {google_api_key[:20]}")

import google.generativeai as genai
genai.configure(api_key=google_api_key)

try:
    print("Testing gemini-2.0-flash...")
    model = genai.GenerativeModel("gemini-2.0-flash")
    response = model.generate_content("Say 'test'")
    print(f"✅ Success! {response.text[:60]}")
except Exception as e:
    print(f"❌ {type(e).__name__}: {str(e)[:200]}")
