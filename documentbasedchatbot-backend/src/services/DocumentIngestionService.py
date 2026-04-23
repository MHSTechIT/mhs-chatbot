import os
import logging
import requests
from bs4 import BeautifulSoup
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_core.documents import Document
from src.repository.vector_db import get_vector_store

logger = logging.getLogger(__name__)


class DocumentIngestionService:
    """Service to ingest documents into the vector store for RAG.
    Uses Google Gemini embeddings API — no PyTorch, no local model download.
    """

    def __init__(self):
        self.vector_store = get_vector_store()
        self.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=500,
            chunk_overlap=100,
            separators=["\n\n", "\n", " ", ""]
        )

    def _add_chunks(self, chunks: list, title: str, extra_meta: dict = None) -> bool:
        """Helper: wrap text chunks into Documents and add to vector store."""
        if not chunks:
            return False
        meta = {"source": title}
        if extra_meta:
            meta.update(extra_meta)
        docs = [Document(page_content=c, metadata=meta) for c in chunks]
        self.vector_store.add_documents(docs)
        logger.info(f"Ingested {len(docs)} chunks from '{title}'")
        return True

    def ingest_text_file(self, file_path: str, title: str) -> bool:
        """Ingest a plain text file into the vector store."""
        try:
            if not os.path.exists(file_path):
                logger.warning(f"File not found: {file_path}")
                return False
            with open(file_path, "r", encoding="utf-8") as f:
                content = f.read()
            if not content.strip():
                logger.warning(f"File is empty: {file_path}")
                return False
            chunks = self.text_splitter.split_text(content)
            return self._add_chunks(chunks, title, {"file_path": file_path})
        except Exception as e:
            logger.error(f"Error ingesting text file {file_path}: {e}")
            return False

    def ingest_pdf_file(self, file_path: str, title: str) -> bool:
        """Ingest a PDF file using pypdf (no langchain-community needed)."""
        try:
            if not os.path.exists(file_path):
                logger.warning(f"PDF not found: {file_path}")
                return False
            from pypdf import PdfReader
            reader = PdfReader(file_path)
            all_chunks = []
            for page in reader.pages:
                text = page.extract_text() or ""
                if text.strip():
                    all_chunks.extend(self.text_splitter.split_text(text))
            if not all_chunks:
                logger.warning(f"No content extracted from PDF: {file_path}")
                return False
            return self._add_chunks(all_chunks, title, {"file_path": file_path})
        except Exception as e:
            logger.error(f"Error ingesting PDF {file_path}: {e}")
            return False

    def ingest_docx_file(self, file_path: str, title: str) -> bool:
        """Ingest a DOCX file into the vector store."""
        try:
            if not os.path.exists(file_path):
                logger.warning(f"DOCX not found: {file_path}")
                return False
            from docx import Document as DocxDocument
            doc = DocxDocument(file_path)
            content = "\n".join(p.text for p in doc.paragraphs)
            if not content.strip():
                logger.warning(f"No content extracted from DOCX: {file_path}")
                return False
            chunks = self.text_splitter.split_text(content)
            return self._add_chunks(chunks, title, {"file_path": file_path})
        except Exception as e:
            logger.error(f"Error ingesting DOCX {file_path}: {e}")
            return False

    def scrape_webpage(self, url: str) -> str:
        """Scrape and extract plain text from a webpage."""
        try:
            headers = {"User-Agent": "Mozilla/5.0"}
            response = requests.get(url, timeout=10, headers=headers)
            response.raise_for_status()
            soup = BeautifulSoup(response.content, "html.parser")
            for tag in soup(["script", "style", "meta", "noscript"]):
                tag.decompose()
            lines = (line.strip() for line in soup.get_text().splitlines())
            chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
            return "\n".join(c for c in chunks if c)
        except Exception as e:
            logger.error(f"Error scraping {url}: {e}")
            return ""

    def ingest_link(self, url: str, title: str) -> bool:
        """Fetch and ingest content from a URL."""
        try:
            content = self.scrape_webpage(url)
            if not content.strip():
                logger.warning(f"No content from URL: {url}")
                return False
            chunks = self.text_splitter.split_text(content)
            if not chunks:
                return False
            return self._add_chunks(chunks, title, {"url": url, "type": "link"})
        except Exception as e:
            logger.error(f"Error ingesting link {url}: {e}")
            return False

    def ingest_document(self, file_path: str, file_name: str, title: str, doc_type: str) -> bool:
        """Route ingestion based on document type."""
        if doc_type == "link":
            return self.ingest_link(file_path, title)
        if file_name.endswith(".pdf"):
            return self.ingest_pdf_file(file_path, title)
        elif file_name.endswith(".txt"):
            return self.ingest_text_file(file_path, title)
        elif file_name.endswith(".docx"):
            return self.ingest_docx_file(file_path, title)
        else:
            logger.warning(f"Unsupported file type: {file_name}")
            return False
