#!/usr/bin/env python3
"""
Diagnostic script to test backend connectivity and identify failing components.
"""

import sys
import asyncio
from dotenv import load_dotenv
import os

load_dotenv()

def test_environment_variables():
    """Test if required environment variables are set."""
    print("=" * 60)
    print("TEST 1: Environment Variables")
    print("=" * 60)

    groq_key = os.getenv("GROQ_API_KEY")
    db_connection = os.getenv("DB_CONNECTION")

    print(f"[OK] GROQ_API_KEY is set: {bool(groq_key)}")
    if groq_key:
        print(f"  Key starts with: {groq_key[:10]}...")

    print(f"[OK] DB_CONNECTION is set: {bool(db_connection)}")
    if db_connection:
        print(f"  Connection string: {db_connection[:50]}...")

    return groq_key and db_connection

def test_database_connection():
    """Test database connectivity."""
    print("\n" + "=" * 60)
    print("TEST 2: Database Connection")
    print("=" * 60)

    try:
        from sqlalchemy import create_engine, text
        from src.repository.vector_db import _create_db_engine

        engine = _create_db_engine()
        with engine.connect() as conn:
            result = conn.execute(text("SELECT 1"))
            print("[OK] Database connection successful")
            return True
    except Exception as e:
        print(f"[FAIL] Database connection failed: {e}")
        return False

def test_vector_store():
    """Test vector store initialization."""
    print("\n" + "=" * 60)
    print("TEST 3: Vector Store Initialization")
    print("=" * 60)

    try:
        from src.repository.vector_db import get_vector_store

        vector_store = get_vector_store()
        print("[OK] Vector store initialized successfully")
        return True
    except Exception as e:
        print(f"[FAIL] Vector store initialization failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_chat_service():
    """Test ChatService initialization."""
    print("\n" + "=" * 60)
    print("TEST 4: ChatService Initialization")
    print("=" * 60)

    try:
        from src.services.ChatService.ChatService import ChatServiceImpl

        service = ChatServiceImpl()
        print("[OK] ChatService initialized successfully")
        return True
    except Exception as e:
        print(f"[FAIL] ChatService initialization failed: {e}")
        import traceback
        traceback.print_exc()
        return False

async def test_chat_ask():
    """Test asking a question through the chat service."""
    print("\n" + "=" * 60)
    print("TEST 5: Chat Ask Question")
    print("=" * 60)

    try:
        from src.services.ChatService.ChatService import ChatServiceImpl

        service = ChatServiceImpl()
        result = await service.ask_question("What is the company about?")

        print(f"[OK] Question processed successfully")
        print(f"  Answer type: {result.get('type')}")
        print(f"  Answer preview: {result.get('answer')[:100]}...")
        return True
    except Exception as e:
        print(f"[FAIL] Chat question failed: {e}")
        import traceback
        traceback.print_exc()
        return False

async def main():
    """Run all diagnostic tests."""
    print("\n" + "=" * 60)
    print("DOCUMENT-BASED CHATBOT BACKEND DIAGNOSTIC")
    print("=" * 60)

    results = []

    # Test 1: Environment
    results.append(("Environment Variables", test_environment_variables()))

    # Test 2: Database
    results.append(("Database Connection", test_database_connection()))

    # Test 3: Vector Store
    results.append(("Vector Store", test_vector_store()))

    # Test 4: Chat Service
    results.append(("ChatService", test_chat_service()))

    # Test 5: Chat Ask
    results.append(("Chat Ask", await test_chat_ask()))

    # Summary
    print("\n" + "=" * 60)
    print("DIAGNOSTIC SUMMARY")
    print("=" * 60)

    passed = sum(1 for _, result in results if result)
    total = len(results)

    for test_name, result in results:
        status = "[OK] PASS" if result else "[FAIL] FAIL"
        print(f"{status}: {test_name}")

    print(f"\nPassed: {passed}/{total}")

    if passed == total:
        print("\n[OK] All tests passed! Backend is ready.")
        return 0
    else:
        print("\n[FAIL] Some tests failed. Check the error messages above.")
        return 1

if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
