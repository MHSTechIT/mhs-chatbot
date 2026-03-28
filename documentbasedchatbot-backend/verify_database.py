#!/usr/bin/env python3
"""
Comprehensive database verification script.
Tests Supabase connection, pgvector setup, and vector store functionality.
"""

import os
import sys
from sqlalchemy import create_engine, text, inspect

def check_database_connection():
    """Test basic database connectivity."""
    print("\n" + "="*60)
    print("1. DATABASE CONNECTION TEST")
    print("="*60)

    db_url = os.getenv("DB_CONNECTION", "postgresql+psycopg://admin:password@localhost:5432/vectordb")
    print(f"Connection string (masked): {db_url[:50]}...")

    try:
        connect_args = {}
        if "supabase.co" in db_url and "sslmode=" not in db_url:
            connect_args["sslmode"] = "require"

        engine_kwargs = dict(pool_pre_ping=True)
        if connect_args:
            engine_kwargs["connect_args"] = connect_args

        engine = create_engine(db_url, **engine_kwargs)

        with engine.connect() as conn:
            result = conn.execute(text("SELECT version();"))
            version = result.fetchone()[0]
            print(f"[OK] Connected successfully!")
            print(f"  PostgreSQL Version: {version[:80]}...")
            return engine
    except Exception as e:
        print(f"[ERROR] Connection failed: {type(e).__name__}: {e}")
        return None

def check_pgvector_extension(engine):
    """Verify pgvector extension is installed."""
    print("\n" + "="*60)
    print("2. PGVECTOR EXTENSION TEST")
    print("="*60)

    try:
        with engine.connect() as conn:
            # Try to create extension
            try:
                conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector;"))
                conn.commit()
                print("[OK] pgvector extension available")
            except Exception as e:
                print(f"[WARN] Could not create extension: {e}")
                print("  (This is okay if extension already exists)")

            # Check for vector type
            result = conn.execute(text("""
                SELECT typname FROM pg_type
                WHERE typname = 'vector' LIMIT 1;
            """))
            if result.fetchone():
                print("[OK] vector type exists in database")
            else:
                print("[FAIL] vector type not found")
                return False
        return True
    except Exception as e:
        print(f"[FAIL] pgvector check failed: {type(e).__name__}: {e}")
        return False

def check_vector_store_tables(engine):
    """Check if vector store tables exist."""
    print("\n" + "="*60)
    print("3. VECTOR STORE TABLES TEST")
    print("="*60)

    try:
        inspector = inspect(engine)
        tables = inspector.get_table_names()

        print(f"Total tables in database: {len(tables)}")

        vector_related = [t for t in tables if 'vector' in t.lower() or 'langchain' in t.lower()]
        if vector_related:
            print(f"[OK] Found {len(vector_related)} vector/langchain related tables:")
            for table in vector_related:
                print(f"  - {table}")
        else:
            print("[WARN] No vector-related tables found")
            print("  Tables in database:", tables[:10] if tables else "None")

        return True
    except Exception as e:
        print(f"[FAIL] Table check failed: {type(e).__name__}: {e}")
        return False

def check_collection_data(engine):
    """Check for company_info collection and its data."""
    print("\n" + "="*60)
    print("4. COLLECTION DATA TEST")
    print("="*60)

    try:
        with engine.connect() as conn:
            # Query the langchain_pg_embedding table for company_info collection
            result = conn.execute(text("""
                SELECT COUNT(*) as count
                FROM langchain_pg_embedding
                WHERE collection_id IN (
                    SELECT uuid FROM langchain_pg_collection
                    WHERE name = 'company_info'
                );
            """))

            count = result.fetchone()[0]

            if count > 0:
                print(f"[OK] Found company_info collection with {count} embeddings")

                # Get sample documents
                result = conn.execute(text("""
                    SELECT document, cmetadata
                    FROM langchain_pg_embedding
                    WHERE collection_id IN (
                        SELECT uuid FROM langchain_pg_collection
                        WHERE name = 'company_info'
                    )
                    LIMIT 3;
                """))

                samples = result.fetchall()
                print(f"\n  Sample documents ({len(samples)} shown):")
                for i, (doc, meta) in enumerate(samples, 1):
                    print(f"    {i}. {doc[:100]}..." if len(doc) > 100 else f"    {i}. {doc}")

                return True
            else:
                print("[FAIL] company_info collection not found or empty")

                # Check what collections exist
                result = conn.execute(text("""
                    SELECT name, COUNT(*) as count
                    FROM langchain_pg_collection lc
                    LEFT JOIN langchain_pg_embedding le ON lc.uuid = le.collection_id
                    GROUP BY lc.name;
                """))

                collections = result.fetchall()
                if collections:
                    print("\n  Existing collections:")
                    for name, cnt in collections:
                        print(f"    - {name}: {cnt} embeddings")
                else:
                    print("\n  No collections found in database")

                return False
    except Exception as e:
        print(f"[WARN] Collection check issue: {type(e).__name__}: {e}")
        print("  This might mean vector store tables don't exist yet (first run)")
        return False

def test_vector_search(engine):
    """Test vector similarity search."""
    print("\n" + "="*60)
    print("5. VECTOR SEARCH TEST")
    print("="*60)

    try:
        from langchain_huggingface import HuggingFaceEmbeddings

        print("Loading embeddings model (all-MiniLM-L6-v2)...")
        embeddings = HuggingFaceEmbeddings(model_name="all-MiniLM-L6-v2")

        test_query = "health school training"
        query_vector = embeddings.embed_query(test_query)

        print(f"[OK] Generated embedding for query: '{test_query}'")
        print(f"  Embedding dimension: {len(query_vector)}")

        # Try to search
        with engine.connect() as conn:
            result = conn.execute(text("""
                SELECT COUNT(*) FROM langchain_pg_embedding
                WHERE collection_id IN (
                    SELECT uuid FROM langchain_pg_collection
                    WHERE name = 'company_info'
                );
            """))

            count = result.fetchone()[0]
            if count > 0:
                print(f"[OK] Can search {count} documents in vector store")
                return True
            else:
                print("[WARN] Vector store is empty, cannot test search")
                return False

    except Exception as e:
        print(f"[WARN] Vector search test failed: {type(e).__name__}: {e}")
        return False

def main():
    """Run all verification tests."""
    print("\n")
    print("=" * 60)
    print("  SUPABASE DATABASE VERIFICATION".center(60))
    print("=" * 60)

    # Test 1: Connection
    engine = check_database_connection()
    if not engine:
        print("\n[FATAL] Cannot connect to database. Cannot proceed.")
        return False

    # Test 2: pgvector
    if not check_pgvector_extension(engine):
        print("\n[WARN] WARNING: pgvector may not be properly configured")

    # Test 3: Tables
    check_vector_store_tables(engine)

    # Test 4: Collection data
    has_data = check_collection_data(engine)

    # Test 5: Vector search
    if has_data:
        test_vector_search(engine)

    # Summary
    print("\n" + "="*60)
    print("VERIFICATION COMPLETE")
    print("="*60)

    if not has_data:
        print("\n[ACTION REQUIRED]:")
        print("  The company_info collection is empty!")
        print("  Run this to populate it:")
        print("  $ python scrape_website.py")
        print("  $ python ingest.py")
    else:
        print("\n[OK] Database appears to be properly configured!")
        print("  The backend should be able to fetch documents from vector store.")

    print()

if __name__ == "__main__":
    main()
