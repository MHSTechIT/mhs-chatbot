import os
from sqlalchemy import create_engine

# Configuration
DB_CONNECTION = os.getenv("DB_CONNECTION", "postgresql+psycopg://admin:password@localhost:5432/vectordb")
COLLECTION_NAME = "company_info"

# Cache the vector store instance to prevent reconnecting on every request
_vector_store_instance = None


def _create_db_engine():
    connect_args = {}
    # Supabase requires SSL. We add sslmode=require if not already present.
    if "supabase.co" in DB_CONNECTION and "sslmode=" not in DB_CONNECTION:
        connect_args["sslmode"] = "require"

    engine_kwargs = dict(pool_size=5, max_overflow=10, pool_pre_ping=True)
    if connect_args:
        engine_kwargs["connect_args"] = connect_args

    return create_engine(DB_CONNECTION, **engine_kwargs)

def get_vector_store():
    """
    Returns a singleton instance of the PGVector store connected to the vector database.
    It initializes the same HuggingFace embeddings model used during ingestion.
    Returns None if connection fails - caller should handle gracefully.
    Heavy imports (torch, sentence-transformers) are deferred to first call.
    """
    global _vector_store_instance
    if _vector_store_instance is None:
        try:
            # Deferred imports — torch/sentence-transformers are ~400MB,
            # loading them at module level crashes Render's 512MB free tier.
            from langchain_huggingface import HuggingFaceEmbeddings
            from langchain_postgres.vectorstores import PGVector
            embeddings = HuggingFaceEmbeddings(model_name="all-MiniLM-L6-v2")
            engine = _create_db_engine()

            _vector_store_instance = PGVector(
                embeddings=embeddings,
                collection_name=COLLECTION_NAME,
                connection=engine,
                use_jsonb=True,
            )
        except Exception as e:
            import logging
            logger = logging.getLogger(__name__)
            logger.warning(f"Vector database connection failed: {str(e)}. Using fallback.")
            return None
    return _vector_store_instance


def retrieve_relevant_documents(query: str, k: int = 5) -> str:
    """
    Retrieve relevant document chunks from the vector store based on semantic similarity.

    Args:
        query: The user's question
        k: Number of chunks to retrieve (default 5)

    Returns:
        Formatted string of relevant document chunks
    """
    try:
        vector_store = get_vector_store()
        # Perform similarity search
        docs = vector_store.similarity_search(query, k=k)

        if not docs:
            return ""

        # Format the retrieved documents
        content = ""
        for i, doc in enumerate(docs, 1):
            source = doc.metadata.get("source", "Unknown")
            content += f"\n[Document {i} - {source}]\n{doc.page_content}\n"

        return content
    except Exception as e:
        import logging
        logger = logging.getLogger(__name__)
        logger.error(f"Error retrieving documents: {str(e)}")
        return ""
