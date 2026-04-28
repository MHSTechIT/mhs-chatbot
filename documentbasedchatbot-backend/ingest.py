import os
from langchain_community.document_loaders import TextLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_postgres.vectorstores import PGVector
from sqlalchemy import create_engine, text

# Database Connection String
DB_CONNECTION = os.getenv("DB_CONNECTION")
if not DB_CONNECTION:
    raise RuntimeError("DB_CONNECTION environment variable is required but not set.")
COLLECTION_NAME = "company_info"

def _create_db_engine():
    connect_args = {}
    # Supabase requires SSL. We add sslmode=require if not already present.
    if "supabase.co" in DB_CONNECTION and "sslmode=" not in DB_CONNECTION:
        connect_args["sslmode"] = "require"

    engine_kwargs = dict(pool_pre_ping=True)
    if connect_args:
        engine_kwargs["connect_args"] = connect_args

    return create_engine(DB_CONNECTION, **engine_kwargs)

def ingest_document():
    print("Loading document...")
    loader = TextLoader("company_info.txt", encoding="utf-8")
    documents = loader.load()

    print("Splitting document...")
    text_splitter = RecursiveCharacterTextSplitter(chunk_size=500, chunk_overlap=50)
    texts = text_splitter.split_documents(documents)
    print(f"Created {len(texts)} chunks.")

    print("Initializing embeddings model (all-MiniLM-L6-v2)...")
    embeddings = HuggingFaceEmbeddings(model_name="all-MiniLM-L6-v2")

    print("Connecting to PostgreSQL vector database...")
    engine = _create_db_engine()

    # Ensure pgvector extension exists (Supabase supports this, but it may need enabling)
    try:
        with engine.begin() as conn:
            conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector;"))
    except Exception as e:
        print(f"Note: could not create/verify pgvector extension automatically: {e}")

    # Remove existing collection so we replace old content (e.g. TechNova) with new (e.g. My Health School)
    print("Removing existing collection (if any)...")
    try:
        existing_store = PGVector(
            embeddings=embeddings,
            collection_name=COLLECTION_NAME,
            connection=engine,
            use_jsonb=True,
        )
        existing_store.delete_collection()
        print("Existing collection removed.")
    except Exception as e:
        print(f"Note: Could not remove existing collection (may be first run): {e}")

    # Store documents in PGVector
    print("Storing vectors in database. This might take a moment...")
    PGVector.from_documents(
        embedding=embeddings,
        documents=texts,
        collection_name=COLLECTION_NAME,
        connection=engine,
        use_jsonb=True,
    )
    print("Ingestion complete. The document is now successfully stored in the vector database.")

if __name__ == "__main__":
    ingest_document()
