"""
Scrape content from https://www.myhealthschool.in/ and ingest into vector database
"""

import os
import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse
from dotenv import load_dotenv

load_dotenv()

def is_valid_url(url, base_url="https://www.myhealthschool.in"):
    """Check if URL belongs to the target domain"""
    parsed = urlparse(url)
    base_parsed = urlparse(base_url)
    return parsed.netloc == base_parsed.netloc

def scrape_website(start_url="https://www.myhealthschool.in/"):
    """Scrape all pages from My Health School website"""
    visited = set()
    to_visit = [start_url]
    content_blocks = []

    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
    }

    print(f"[INFO] Starting scrape of {start_url}")

    while to_visit and len(visited) < 50:  # Limit to 50 pages
        url = to_visit.pop(0)

        if url in visited or not is_valid_url(url):
            continue

        visited.add(url)
        print(f"[Scraping] {url}")

        try:
            response = requests.get(url, headers=headers, timeout=10)
            response.encoding = 'utf-8'
            soup = BeautifulSoup(response.content, 'html.parser')

            # Extract main content
            main_content = soup.find('main') or soup.find('article') or soup.find('body')
            if not main_content:
                continue

            # Remove scripts and styles
            for script in main_content(['script', 'style']):
                script.decompose()

            # Extract text
            text = main_content.get_text(separator='\n', strip=True)
            if text and len(text) > 100:
                content_blocks.append(text)
                print(f"  [OK] Extracted {len(text)} characters")

            # Find links to other pages
            for link in soup.find_all('a', href=True):
                href = urljoin(url, link['href'])
                if is_valid_url(href) and href not in visited:
                    to_visit.append(href)

        except Exception as e:
            print(f"  [ERROR] Failed to scrape {url}: {str(e)}")

    print(f"\n[INFO] Scraped {len(visited)} pages, total {len(content_blocks)} content blocks")
    return content_blocks

def ingest_content_into_db(content_blocks):
    """Ingest scraped content into vector database"""
    print("\n[INFO] Ingesting content into vector database...")

    from langchain_postgres.vectorstores import PGVector
    from langchain_huggingface import HuggingFaceEmbeddings
    from langchain_core.documents import Document
    from sqlalchemy import create_engine

    db_connection = os.getenv("DB_CONNECTION")
    if not db_connection:
        print("[ERROR] DB_CONNECTION not configured")
        return

    try:
        embeddings = HuggingFaceEmbeddings(model_name="all-MiniLM-L6-v2")
        engine = create_engine(db_connection, pool_size=5, max_overflow=10)

        # First, clear existing data from the collection
        vector_store = PGVector(
            embeddings=embeddings,
            collection_name="company_info",
            connection=engine,
            use_jsonb=True,
        )

        # Delete existing records
        from sqlalchemy import text
        with engine.begin() as conn:
            conn.execute(
                text("DELETE FROM langchain_pg_embedding WHERE collection_id = (SELECT uuid FROM langchain_pg_collection WHERE name = 'company_info')")
            )
        print("[OK] Cleared existing embeddings")

        # Split content into chunks and ingest
        from langchain_text_splitters import RecursiveCharacterTextSplitter

        splitter = RecursiveCharacterTextSplitter(
            chunk_size=500,
            chunk_overlap=50,
        )

        all_documents = []
        for content in content_blocks:
            chunks = splitter.split_text(content)
            for chunk in chunks:
                all_documents.append(Document(page_content=chunk))

        print(f"[INFO] Created {len(all_documents)} document chunks")

        # Add to vector store
        vector_store.add_documents(all_documents)
        print(f"[OK] Ingested {len(all_documents)} chunks into database")

    except Exception as e:
        print(f"[ERROR] Failed to ingest content: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    print("="*60)
    print("My Health School Website Scraper")
    print("="*60)

    # Scrape website
    content = scrape_website("https://www.myhealthschool.in/")

    if content:
        # Ingest into database
        ingest_content_into_db(content)
        print("\n[SUCCESS] Ingestion complete!")
    else:
        print("\n[ERROR] No content scraped")
