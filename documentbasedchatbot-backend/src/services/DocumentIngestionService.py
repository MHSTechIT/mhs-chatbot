import os
import logging
from typing import List
import requests
from bs4 import BeautifulSoup
from langchain_text_splitters import RecursiveCharacterTextSplitter
from src.repository.vector_db import get_vector_store

logger = logging.getLogger(__name__)

class DocumentIngestionService:
    """Service to ingest documents into the vector store for RAG"""

    def __init__(self):
        # Deferred imports — torch/sentence-transformers crash Render's 512MB free tier on startup
        from langchain_huggingface import HuggingFaceEmbeddings
        self.vector_store = get_vector_store()
        self.embeddings = HuggingFaceEmbeddings(model_name="all-MiniLM-L6-v2")
        # Chunking strategy for better RAG performance
        self.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=500,
            chunk_overlap=100,
            separators=["\n\n", "\n", " ", ""]
        )

    def ingest_text_file(self, file_path: str, title: str) -> bool:
        """Ingest a text file into the vector store"""
        try:
            if not os.path.exists(file_path):
                logger.warning(f"File not found: {file_path}")
                return False

            from langchain_community.document_loaders import TextLoader
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()

            if not content.strip():
                logger.warning(f"File is empty: {file_path}")
                return False

            # Split content into chunks
            chunks = self.text_splitter.split_text(content)

            # Add to vector store with metadata
            documents = [
                {
                    "page_content": chunk,
                    "metadata": {"source": title, "file_path": file_path}
                }
                for chunk in chunks
            ]

            # Store in vector database
            from langchain_core.documents import Document
            doc_objects = [
                Document(page_content=doc["page_content"], metadata=doc["metadata"])
                for doc in documents
            ]

            self.vector_store.add_documents(doc_objects)
            logger.info(f"Ingested {len(chunks)} chunks from {title}")
            return True

        except Exception as e:
            logger.error(f"Error ingesting text file {file_path}: {str(e)}")
            return False

    def ingest_pdf_file(self, file_path: str, title: str) -> bool:
        """Ingest a PDF file into the vector store"""
        try:
            if not os.path.exists(file_path):
                logger.warning(f"PDF file not found: {file_path}")
                return False

            from langchain_community.document_loaders import PyPDFLoader
            loader = PyPDFLoader(file_path)
            documents = loader.load()

            if not documents:
                logger.warning(f"No content extracted from PDF: {file_path}")
                return False

            # Split content into chunks
            all_chunks = []
            for doc in documents:
                chunks = self.text_splitter.split_text(doc.page_content)
                all_chunks.extend(chunks)

            # Add to vector store with metadata
            from langchain_core.documents import Document
            doc_objects = [
                Document(
                    page_content=chunk,
                    metadata={"source": title, "file_path": file_path}
                )
                for chunk in all_chunks
            ]

            self.vector_store.add_documents(doc_objects)
            logger.info(f"Ingested {len(all_chunks)} chunks from PDF {title}")
            return True

        except Exception as e:
            logger.error(f"Error ingesting PDF file {file_path}: {str(e)}")
            return False

    def ingest_docx_file(self, file_path: str, title: str) -> bool:
        """Ingest a DOCX file into the vector store"""
        try:
            if not os.path.exists(file_path):
                logger.warning(f"DOCX file not found: {file_path}")
                return False

            from docx import Document as DocxDocument

            doc = DocxDocument(file_path)
            content = "\n".join([paragraph.text for paragraph in doc.paragraphs])

            if not content.strip():
                logger.warning(f"No content extracted from DOCX: {file_path}")
                return False

            # Split content into chunks
            chunks = self.text_splitter.split_text(content)

            # Add to vector store with metadata
            from langchain_core.documents import Document
            doc_objects = [
                Document(
                    page_content=chunk,
                    metadata={"source": title, "file_path": file_path}
                )
                for chunk in chunks
            ]

            self.vector_store.add_documents(doc_objects)
            logger.info(f"Ingested {len(chunks)} chunks from DOCX {title}")
            return True

        except Exception as e:
            logger.error(f"Error ingesting DOCX file {file_path}: {str(e)}")
            return False

    def scrape_webpage(self, url: str) -> str:
        """
        Scrape content from a webpage and extract text.

        Args:
            url: URL to scrape

        Returns:
            Extracted text content
        """
        try:
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            }

            response = requests.get(url, timeout=10, headers=headers)
            response.raise_for_status()

            soup = BeautifulSoup(response.content, 'html.parser')

            # Remove script and style elements
            for script in soup(["script", "style", "meta", "noscript"]):
                script.decompose()

            # Get text content
            text = soup.get_text()

            # Clean up whitespace
            lines = (line.strip() for line in text.splitlines())
            chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
            text = '\n'.join(chunk for chunk in chunks if chunk)

            return text

        except Exception as e:
            logger.error(f"Error scraping webpage {url}: {str(e)}")
            return ""

    def ingest_link(self, url: str, title: str) -> bool:
        """
        Fetch and ingest content from a URL into the vector store.

        Args:
            url: URL to scrape and ingest
            title: Document title for metadata

        Returns:
            True if successful, False otherwise
        """
        try:
            # Scrape the webpage
            content = self.scrape_webpage(url)

            if not content or not content.strip():
                logger.warning(f"No content extracted from URL: {url}")
                return False

            # Split content into chunks
            chunks = self.text_splitter.split_text(content)

            if not chunks:
                logger.warning(f"No chunks created from URL content: {url}")
                return False

            # Add to vector store with metadata
            from langchain_core.documents import Document
            doc_objects = [
                Document(
                    page_content=chunk,
                    metadata={"source": title, "url": url, "type": "link"}
                )
                for chunk in chunks
            ]

            self.vector_store.add_documents(doc_objects)
            logger.info(f"Ingested {len(chunks)} chunks from URL {title}: {url}")
            return True

        except Exception as e:
            logger.error(f"Error ingesting link {title} ({url}): {str(e)}")
            return False

    def ingest_document(self, file_path: str, file_name: str, title: str, doc_type: str) -> bool:
        """
        Ingest a document based on its type (PDF, TXT, DOCX)

        Args:
            file_path: Path to the file
            file_name: Original file name
            title: Document title for metadata
            doc_type: 'document' or 'link'

        Returns:
            True if successful, False otherwise
        """
        if doc_type == "link":
            return self.ingest_link(file_path, title)

        # For documents, detect type from extension
        if file_name.endswith('.pdf'):
            return self.ingest_pdf_file(file_path, title)
        elif file_name.endswith('.txt'):
            return self.ingest_text_file(file_path, title)
        elif file_name.endswith('.docx'):
            return self.ingest_docx_file(file_path, title)
        else:
            logger.warning(f"Unsupported file type: {file_name}")
            return False
