#!/usr/bin/env python3
"""
Cleanup script to remove test documents from vector store.
Keeps only user-uploaded documents.
"""

import os
import logging
from sqlalchemy import text

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def cleanup_vector_store():
    """Remove test/sample documents from vector store"""

    # Document titles to delete (test documents)
    test_titles = [
        "checking ",  # MyHealthSchool_ChatbotKnowledgeBase.docx
        "My Health School Knowledge Base"  # sample_health_info.txt
    ]

    try:
        from src.repository.vector_db import get_vector_store

        vector_store = get_vector_store()
        logger.info("🧹 Starting vector store cleanup...")
        logger.info(f"Removing {len(test_titles)} test documents...")

        for title in test_titles:
            try:
                logger.info(f"\n   Removing: '{title}'")

                # Get the connection
                conn = vector_store.connection

                # Delete documents where source metadata matches the title
                delete_query = text("""
                    DELETE FROM langchain_pg_embedding
                    WHERE collection_id = (SELECT id FROM langchain_pg_collection WHERE name = :collection)
                    AND metadata->>'source' = :source
                """)

                with conn.connect() as connection:
                    result = connection.execute(delete_query, {
                        "collection": "company_info",
                        "source": title
                    })
                    connection.commit()
                    logger.info(f"   ✅ Removed from vector store")

            except Exception as e:
                logger.warning(f"   ⚠️  Could not delete '{title}': {str(e)}")

        logger.info(f"\n✨ Vector store cleanup complete!")
        logger.info("✅ System cleaned up - ready for user documents")

    except Exception as e:
        logger.error(f"Error connecting to vector store: {str(e)}")
        logger.info("Make sure backend is running with database connection")

if __name__ == "__main__":
    cleanup_vector_store()
