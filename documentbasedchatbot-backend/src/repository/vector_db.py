import os
from sqlalchemy import create_engine

# Configuration
DB_CONNECTION = os.getenv("DB_CONNECTION", "postgresql+psycopg://admin:password@localhost:5432/vectordb")
COLLECTION_NAME = "company_info"

# Cache the vector store instance to prevent reconnecting on every request
_vector_store_instance = None


def _create_db_engine():
    connect_args = {}
    if "supabase.co" in DB_CONNECTION and "sslmode=" not in DB_CONNECTION:
        connect_args["sslmode"] = "require"

    engine_kwargs = dict(pool_size=5, max_overflow=10, pool_pre_ping=True)
    if connect_args:
        engine_kwargs["connect_args"] = connect_args

    return create_engine(DB_CONNECTION, **engine_kwargs)


def get_vector_store():
    """
    Returns a singleton PGVector store using Google Gemini embeddings (API-based).
    No local model download, no PyTorch — embeddings run via Gemini API.
    """
    global _vector_store_instance
    if _vector_store_instance is None:
        try:
            from langchain_google_genai import GoogleGenerativeAIEmbeddings
            from langchain_postgres.vectorstores import PGVector

            embeddings = GoogleGenerativeAIEmbeddings(
                model="models/text-embedding-004",
                google_api_key=os.getenv("GOOGLE_API_KEY"),
            )
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
    """
    try:
        vector_store = get_vector_store()
        if not vector_store:
            return ""
        docs = vector_store.similarity_search(query, k=k)

        if not docs:
            return ""

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
