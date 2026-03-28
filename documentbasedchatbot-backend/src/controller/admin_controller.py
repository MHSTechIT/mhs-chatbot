import os
import logging
import uuid
from datetime import datetime
from fastapi import APIRouter, File, UploadFile, Form, HTTPException
from pydantic import BaseModel
from src.repository.admin_repo import AdminRepository
from src.repository.enrollment_repo import EnrollmentRepository
from src.database import SessionLocal
from src.services.DocumentIngestionService import DocumentIngestionService

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/admin", tags=["Admin"])

# Database and Services
admin_repo = AdminRepository()
try:
    ingestion_service = DocumentIngestionService()
except Exception as e:
    logger.warning(f"Document ingestion service not available: {str(e)}")
    ingestion_service = None


class LinkRequest(BaseModel):
    title: str
    url: str


class DocumentResponse(BaseModel):
    id: str
    title: str
    type: str
    url: str = None
    file_name: str = None
    uploaded_at: str


class EnrollmentRequest(BaseModel):
    name: str
    phone: str
    sugar_level: str = None


@router.post("/upload")
async def upload_document(file: UploadFile = File(...), title: str = Form(...)):
    """Upload a document (PDF, TXT, DOCX) - saves content to DATABASE"""
    if not title.strip():
        raise HTTPException(status_code=400, detail="Title required")

    db = None
    try:
        # Save file
        upload_dir = "uploads"
        os.makedirs(upload_dir, exist_ok=True)

        file_path = os.path.join(upload_dir, file.filename)
        file_content = await file.read()

        # Read text content from file
        text_content = ""
        try:
            text_content = file_content.decode('utf-8')
            logger.info(f"✅ Read file content: {len(text_content)} characters")
        except:
            # If UTF-8 fails, try other encodings
            try:
                text_content = file_content.decode('latin-1')
                logger.info(f"✅ Read file with latin-1: {len(text_content)} characters")
            except:
                logger.warning("Could not decode file content, will save file path only")

        # Save file to disk
        with open(file_path, "wb") as f:
            f.write(file_content)

        logger.info(f"✅ File uploaded: {file.filename}")

        # Save to database with content
        db = SessionLocal()
        from src.models.document import Document

        doc_id = str(uuid.uuid4())
        new_doc = Document(
            id=doc_id,
            title=title.strip(),
            type="document",
            file_name=file.filename,
            file_path=file_path,
            content=text_content if text_content else None  # Store content in database
        )
        db.add(new_doc)
        db.commit()

        # Also update admin_repo for consistency
        admin_repo.documents[doc_id] = {
            "id": doc_id,
            "title": title.strip(),
            "type": "document",
            "file_name": file.filename,
            "file_path": file_path,
            "content": text_content,
            "url": None,
            "uploaded_at": datetime.now().isoformat()
        }
        admin_repo.save_documents()

        logger.info(f"✅ Document saved to database: {doc_id}")

        # Index document into vector store for RAG (optional)
        if ingestion_service:
            try:
                success = ingestion_service.ingest_document(
                    file_path=file_path,
                    file_name=file.filename,
                    title=title,
                    doc_type="document"
                )
                if success:
                    logger.info(f"Document indexed into vector store: {title}")
                else:
                    logger.warning(f"Failed to index document into vector store: {title}")
            except Exception as e:
                logger.error(f"Error indexing document: {str(e)}")

        return {"success": True, "id": doc_id, "message": "Document uploaded to database"}

    except Exception as e:
        logger.error(f"Upload error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        if db:
            db.close()


@router.post("/add-link")
async def add_link(request: LinkRequest):
    """Add a reference link"""
    if not request.title.strip() or not request.url.strip():
        raise HTTPException(status_code=400, detail="Title and URL required")

    try:
        doc_id = admin_repo.add_document(
            title=request.title,
            url=request.url,
            type="link"
        )

        # Index link into vector store for RAG
        if ingestion_service:
            try:
                success = ingestion_service.ingest_link(
                    url=request.url,
                    title=request.title
                )
                if success:
                    logger.info(f"Link indexed into vector store: {request.title}")
                else:
                    logger.warning(f"Failed to index link into vector store: {request.title}")
            except Exception as e:
                logger.error(f"Error indexing link: {str(e)}")

        logger.info(f"Link added: {request.title}")
        return {"success": True, "id": doc_id, "message": "Link added"}

    except Exception as e:
        logger.error(f"Link error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/documents")
async def get_documents():
    """Get all uploaded documents and links"""
    try:
        # Force reload from file to get latest data
        admin_repo.load_documents()
        documents = admin_repo.get_all_documents()
        return {
            "success": True,
            "documents": documents,
            "count": len(documents)
        }
    except Exception as e:
        logger.error(f"Error fetching documents: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/documents/{doc_id}")
async def delete_document(doc_id: str):
    """Delete a document or link from database AND vector store"""
    try:
        doc = admin_repo.get_document_by_id(doc_id)
        if not doc:
            raise HTTPException(status_code=404, detail="Document not found")

        # Remove from vector store using the document title as metadata
        if ingestion_service:
            try:
                from src.repository.vector_db import get_vector_store
                vector_store = get_vector_store()

                # Delete documents with matching source metadata
                logger.info(f"Attempting to remove document '{doc['title']}' from vector store")
                try:
                    # PGVector supports filtering by metadata
                    vector_store.delete(ids=[doc_id])
                    logger.info(f"Removed '{doc['title']}' from vector store")
                except Exception as e:
                    logger.warning(f"Could not delete from vector store by ID: {e}. This may be normal if not yet indexed.")

            except Exception as e:
                logger.error(f"Error removing from vector store: {str(e)}")

        # Delete from database
        success = admin_repo.delete_document(doc_id)
        if success:
            logger.info(f"Document deleted from database: {doc_id}")
            return {"success": True, "message": "Document deleted from database and vector store"}
        else:
            raise HTTPException(status_code=404, detail="Document not found in database")

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Delete error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/documents/search")
async def search_documents(query: str):
    """Search documents by title"""
    try:
        results = admin_repo.search_documents(query)
        return {"success": True, "results": results}
    except Exception as e:
        logger.error(f"Search error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/submit-enrollment")
async def submit_enrollment(request: EnrollmentRequest):
    """Submit enrollment form with name, phone, and optional sugar level"""
    db = SessionLocal()
    try:
        if not request.name.strip() or not request.phone.strip():
            raise HTTPException(status_code=400, detail="Name and phone are required")

        enrollment_id = EnrollmentRepository.create_enrollment(
            db,
            name=request.name.strip(),
            phone=request.phone.strip(),
            sugar_level=request.sugar_level.strip() if request.sugar_level else None
        )

        logger.info(f"Enrollment submitted: {request.name} ({request.phone})")
        return {
            "success": True,
            "id": str(enrollment_id),
            "message": "Enrollment submitted successfully"
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Enrollment submission error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        db.close()


@router.get("/leads")
async def get_enrollment_leads():
    """Get all enrollment leads"""
    db = SessionLocal()
    try:
        enrollments = EnrollmentRepository.get_all_enrollments(db)
        leads = [
            {
                "id": str(e.id),
                "name": e.name,
                "phone": e.phone,
                "sugar_level": e.sugar_level or "",
                "created_at": e.created_at.isoformat() if hasattr(e.created_at, 'isoformat') else str(e.created_at)
            }
            for e in enrollments
        ]
        return {"success": True, "leads": leads, "count": len(leads)}
    except Exception as e:
        logger.error(f"Error fetching leads: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        db.close()


@router.post("/clear-all")
async def clear_all_data():
    """DANGER: Clear ALL documents, links, and vector store data. Start fresh."""
    try:
        import shutil

        # Clear documents from memory cache
        admin_repo.documents = {}

        # Clear documents from JSON file
        admin_repo.save_documents()
        logger.info("Cleared all documents from JSON storage")

        # Verify by reloading from file
        admin_repo.load_documents()
        if not admin_repo.documents:
            logger.info("Verified: Documents cache is empty")

        # Delete uploaded files
        if os.path.exists("uploads"):
            shutil.rmtree("uploads")
            os.makedirs("uploads", exist_ok=True)
            logger.info("✅ Deleted uploads folder")

        # Clear vector store collection
        if ingestion_service:
            try:
                from src.repository.vector_db import get_vector_store
                vector_store = get_vector_store()

                # Delete the entire collection and recreate it
                try:
                    vector_store.delete_collection()
                    logger.info("✅ Deleted vector store collection")
                except Exception as e:
                    logger.warning(f"Could not delete collection (may not exist yet): {e}")

            except Exception as e:
                logger.error(f"Error clearing vector store: {str(e)}")
                raise HTTPException(status_code=500, detail=f"Failed to clear vector store: {str(e)}")

        logger.info("🔄 System cleared - ready to add new documents from scratch")
        return {
            "success": True,
            "message": "All data cleared successfully. Ready to start fresh."
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error clearing data: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))
