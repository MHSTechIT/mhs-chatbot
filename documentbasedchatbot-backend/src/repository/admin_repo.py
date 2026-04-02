import os
import time
import logging
import uuid
from datetime import datetime
from typing import List, Dict, Optional

logger = logging.getLogger(__name__)

# Module-level singleton — shared across admin_controller and HealthChatService
_shared_instance = None

def get_admin_repository() -> "AdminRepository":
    global _shared_instance
    if _shared_instance is None:
        _shared_instance = AdminRepository()
        logger.info("AdminRepository shared singleton created")
    return _shared_instance


class AdminRepository:
    """Manage documents and links for RAG - reads from DATABASE not JSON"""

    def __init__(self):
        """Initialize with database storage"""
        self.documents = {}
        self._last_loaded: float = 0.0
        self._cache_ttl: float = 60.0  # Reload from DB at most once per 60 seconds
        self._content_cache: str = ""   # Assembled RAG string cache
        self.load_documents()

    def load_documents(self):
        """Load documents from DATABASE (cached — reloads at most every 60s)"""
        now = time.monotonic()
        if self.documents and (now - self._last_loaded) < self._cache_ttl:
            return  # Cache is fresh — skip DB hit
        try:
            from src.database import SessionLocal
            from src.models.document import Document

            session = SessionLocal()
            try:
                # Load ALL documents from database
                db_documents = session.query(Document).all()
                self.documents = {}

                for doc in db_documents:
                    doc_id_str = str(doc.id)  # Always use string keys
                    self.documents[doc_id_str] = {
                        "id": doc_id_str,
                        "title": doc.title,
                        "type": doc.type,
                        "file_name": doc.file_name,
                        "file_path": doc.file_path,
                        "url": doc.url,
                        "content": doc.content,  # Document content from database
                        "uploaded_at": doc.created_at.isoformat() if doc.created_at else None
                    }

                self._last_loaded = time.monotonic()
                self._content_cache = ""  # Invalidate content cache on fresh load
                logger.info(f"✅ Loaded {len(self.documents)} documents from database")

            finally:
                session.close()

        except Exception as e:
            logger.warning(f"Could not load from database: {str(e)}. Falling back to JSON.")
            self._load_from_json()

    def _load_from_json(self):
        """Fallback: load from JSON file if database unavailable"""
        db_file = "data/documents.json"
        if os.path.exists(db_file):
            import json
            try:
                with open(db_file, 'r') as f:
                    self.documents = json.load(f)
                logger.info(f"Loaded {len(self.documents)} documents from JSON fallback")
            except Exception as e:
                logger.warning(f"Could not load JSON: {str(e)}")
                self.documents = {}

    def save_documents(self):
        """Save documents to database (primary) and JSON (fallback)"""
        try:
            from src.database import SessionLocal
            from src.models.document import Document

            session = SessionLocal()
            try:
                # Update database with in-memory documents
                import uuid as _uuid_mod
                for doc_id, doc_data in self.documents.items():
                    # Convert string id to UUID object for Supabase
                    try:
                        uuid_id = _uuid_mod.UUID(str(doc_id))
                    except Exception:
                        uuid_id = _uuid_mod.uuid4()
                    existing = session.query(Document).filter(Document.id == uuid_id).first()
                    if not existing:
                        new_doc = Document(
                            id=uuid_id,
                            title=doc_data.get("title"),
                            type=doc_data.get("type"),
                            file_name=doc_data.get("file_name"),
                            file_path=doc_data.get("file_path"),
                            url=doc_data.get("url"),
                            content=doc_data.get("content")
                        )
                        session.add(new_doc)

                session.commit()
                logger.info("✅ Documents saved to database")

            finally:
                session.close()

        except Exception as e:
            logger.warning(f"Could not save to database: {str(e)}. Using JSON fallback.")

        # Also save to JSON as backup
        os.makedirs("data", exist_ok=True)
        import json
        with open("data/documents.json", 'w') as f:
            json.dump(self.documents, f, indent=2)

    def add_document(
        self,
        title: str,
        type: str = "document",
        file_name: str = None,
        file_path: str = None,
        url: str = None
    ) -> str:
        """Add document or link"""
        doc_id = str(uuid.uuid4())

        self.documents[doc_id] = {
            "id": doc_id,
            "title": title,
            "type": type,
            "file_name": file_name,
            "file_path": file_path,
            "url": url,
            "uploaded_at": datetime.now().isoformat()
        }

        # Invalidate caches so next request reads fresh content from DB
        self._content_cache = ""
        self._last_loaded = 0.0

        self.save_documents()
        logger.info(f"Document added: {doc_id} - {title}")
        return doc_id

    def get_all_documents(self) -> List[Dict]:
        """Get all documents"""
        docs = []
        for doc in self.documents.values():
            docs.append({
                "id": doc["id"],
                "title": doc["title"],
                "type": doc["type"],
                "file_name": doc.get("file_name"),
                "url": doc.get("url"),
                "uploaded_at": doc["uploaded_at"]
            })
        return docs

    def get_document_by_id(self, doc_id: str) -> Optional[Dict]:
        """Get document by ID"""
        return self.documents.get(doc_id)

    def delete_document(self, doc_id: str) -> bool:
        """Delete document from memory and DATABASE"""
        if doc_id not in self.documents:
            return False

        doc = self.documents[doc_id]

        # Delete file if exists
        if doc.get("file_path") and os.path.exists(doc["file_path"]):
            try:
                os.remove(doc["file_path"])
            except Exception:
                pass

        # Delete from DATABASE
        try:
            import uuid as _uuid_mod
            from src.database import SessionLocal
            from src.models.document import Document as DocModel
            try:
                uuid_id = _uuid_mod.UUID(str(doc_id))
            except Exception:
                uuid_id = doc_id
            session = SessionLocal()
            try:
                db_doc = session.query(DocModel).filter(DocModel.id == uuid_id).first()
                if db_doc:
                    session.delete(db_doc)
                    session.commit()
                    logger.info(f"✅ Deleted document from database: {doc_id}")
            finally:
                session.close()
        except Exception as e:
            logger.warning(f"Could not delete from database: {e}")

        del self.documents[doc_id]

        # Invalidate caches immediately so the deleted doc is never served again
        self._content_cache = ""
        self._last_loaded = 0.0

        self.save_documents()
        logger.info(f"Document deleted: {doc_id}")
        return True

    def search_documents(self, query: str) -> List[Dict]:
        """Search documents by title"""
        query_lower = query.lower()
        results = []

        for doc in self.documents.values():
            if query_lower in doc["title"].lower():
                results.append({
                    "id": doc["id"],
                    "title": doc["title"],
                    "type": doc["type"],
                    "url": doc.get("url")
                })

        return results

    def get_documents_content(self) -> str:
        """Get all document content for RAG — cached in memory, refreshed every 60s.
        Cache is explicitly cleared on add/delete so changes are reflected immediately."""
        self.load_documents()  # No-op if TTL fresh; reloads from DB if expired or invalidated
        if self._content_cache:
            return self._content_cache
        content = ""
        logger.info(f"🔍 Assembling content from {len(self.documents)} documents")

        for doc in self.documents.values():
            content += f"\n\n=== {doc['title']} ===\n"

            # Add link URLs
            if doc["type"] == "link" and doc.get("url"):
                content += f"Source: {doc['url']}\n"

            # Add document content from database (PRIORITY) or file (FALLBACK)
            if doc["type"] == "document":
                if doc.get("content"):
                    # Use content stored in database
                    content += doc["content"]
                    logger.info(f"✅ Using database content for: {doc['title']}")
                elif doc.get("file_path"):
                    # Fallback to reading file if no database content
                    try:
                        with open(doc["file_path"], 'r', encoding='utf-8') as f:
                            file_content = f.read()
                            content += file_content
                            # Save to database for future use
                            self._save_document_content(doc['id'], file_content)
                            logger.info(f"📝 Using file content for: {doc['title']} (saved to DB)")
                    except Exception as e:
                        logger.warning(f"Could not read file: {doc['file_path']} - {str(e)}")

        self._content_cache = content
        logger.info(f"📊 Total content: {len(content)} chars (cached for next request)")
        return content

    def _save_document_content(self, doc_id: str, content: str):
        """Save document content to database"""
        try:
            import uuid as _uuid_mod
            from src.database import SessionLocal
            from src.models.document import Document

            try:
                uuid_id = _uuid_mod.UUID(str(doc_id))
            except Exception:
                uuid_id = doc_id

            session = SessionLocal()
            try:
                doc = session.query(Document).filter(Document.id == uuid_id).first()
                if doc and not doc.content:
                    doc.content = content
                    session.commit()
                    logger.info(f"✅ Saved document content to database: {doc_id}")
            finally:
                session.close()
        except Exception as e:
            logger.warning(f"Could not save to database: {str(e)}")

    def get_documents_summary(self) -> str:
        """Get summary of all documents"""
        summary = "Uploaded Resources:\n\n"

        for doc in self.documents.values():
            if doc["type"] == "link":
                summary += f"🔗 {doc['title']}: {doc.get('url', 'N/A')}\n"
            else:
                summary += f"📄 {doc['title']} (File: {doc.get('file_name', 'N/A')})\n"

        return summary
