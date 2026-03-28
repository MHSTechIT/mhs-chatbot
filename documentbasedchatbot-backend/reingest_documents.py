#!/usr/bin/env python3
"""Re-ingest all uploaded documents into the vector store"""

import logging
import os
from src.repository.admin_repo import AdminRepository
from src.services.DocumentIngestionService import DocumentIngestionService

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def reingest_all_documents():
    """Re-ingest all documents from the database into the vector store"""

    logger.info("Starting document re-ingestion...")

    try:
        admin_repo = AdminRepository()
        ingestion_service = DocumentIngestionService()

        # Get all documents from database
        documents = admin_repo.get_documents()
        logger.info(f"Found {len(documents)} documents in database")

        if not documents:
            logger.warning("No documents found to ingest")
            return

        success_count = 0
        error_count = 0

        for doc in documents:
            logger.info(f"\nProcessing: {doc.title} ({doc.file_name})")

            # Build file path
            file_path = doc.file_path if hasattr(doc, 'file_path') and doc.file_path else f"uploads/{doc.file_name}"

            # Check if file exists
            if not os.path.exists(file_path):
                logger.warning(f"  File not found: {file_path}")
                error_count += 1
                continue

            # Re-ingest the document
            try:
                success = ingestion_service.ingest_document(
                    file_path=file_path,
                    file_name=doc.file_name,
                    title=doc.title,
                    doc_type="document"
                )
                if success:
                    logger.info(f"  ✅ Successfully ingested")
                    success_count += 1
                else:
                    logger.error(f"  ❌ Ingestion failed")
                    error_count += 1
            except Exception as e:
                logger.error(f"  ❌ Error: {str(e)}")
                error_count += 1

        logger.info(f"\n{'='*50}")
        logger.info(f"Re-ingestion complete!")
        logger.info(f"Success: {success_count}")
        logger.info(f"Failed: {error_count}")
        logger.info(f"{'='*50}")

    except Exception as e:
        logger.error(f"Fatal error: {str(e)}")
        raise

if __name__ == "__main__":
    reingest_all_documents()
