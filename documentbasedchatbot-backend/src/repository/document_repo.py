import logging
from sqlalchemy.orm import Session
from src.models.document import Document

logger = logging.getLogger(__name__)

class DocumentRepository:
    """Repository for managing documents from Supabase."""

    @staticmethod
    def get_all_documents(db: Session) -> list:
        """Retrieve all uploaded documents."""
        try:
            documents = db.query(Document).order_by(Document.uploaded_at.desc()).all()
            logger.info(f"Retrieved {len(documents)} documents from database")
            return documents
        except Exception as e:
            logger.error(f"Error retrieving documents: {str(e)}")
            return []

    @staticmethod
    def get_document_by_id(db: Session, doc_id: str) -> Document:
        """Retrieve document by ID."""
        try:
            return db.query(Document).filter(Document.id == doc_id).first()
        except Exception as e:
            logger.error(f"Error retrieving document {doc_id}: {str(e)}")
            return None

    @staticmethod
    def get_documents_by_type(db: Session, doc_type: str) -> list:
        """Retrieve documents by type (document or link)."""
        try:
            documents = db.query(Document).filter(Document.type == doc_type).all()
            return documents
        except Exception as e:
            logger.error(f"Error retrieving documents of type {doc_type}: {str(e)}")
            return []

    @staticmethod
    def get_documents_content(db: Session) -> str:
        """Get all document content as formatted string for RAG."""
        try:
            documents = DocumentRepository.get_all_documents(db)
            content = ""

            for doc in documents:
                content += f"\n\n=== {doc.title} ===\n"

                # Add link URLs
                if doc.type == "link" and doc.url:
                    content += f"Source: {doc.url}\n"

                # Add document content
                if doc.type == "document" and doc.content:
                    content += doc.content

            return content
        except Exception as e:
            logger.error(f"Error getting documents content: {str(e)}")
            return ""

    @staticmethod
    def search_documents(db: Session, query: str) -> list:
        """Search documents by title or content."""
        try:
            query_lower = query.lower()
            documents = db.query(Document).filter(
                (Document.title.ilike(f"%{query}%")) |
                (Document.content.ilike(f"%{query}%"))
            ).all()
            return documents
        except Exception as e:
            logger.error(f"Error searching documents: {str(e)}")
            return []
