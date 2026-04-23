import os
import json
import logging
from uuid import uuid4

logger = logging.getLogger(__name__)

DB_CONNECTION = os.getenv("DB_CONNECTION", "postgresql+psycopg://admin:password@localhost:5432/vectordb")
COLLECTION_NAME = "company_info"
EMBEDDING_MODEL = "models/text-embedding-004"
EMBEDDING_DIM = 768  # text-embedding-004 output dimension

_vector_store_instance = None


def _psycopg_dsn() -> str:
    """Convert SQLAlchemy-style DSN to plain psycopg3 DSN."""
    return DB_CONNECTION.replace("postgresql+psycopg://", "postgresql://")


def _get_conn():
    """Open a psycopg3 connection with pgvector registered."""
    import psycopg
    from pgvector.psycopg import register_vector
    dsn = _psycopg_dsn()
    connect_kwargs = {}
    if "supabase.co" in dsn and "sslmode=" not in dsn:
        connect_kwargs["sslmode"] = "require"
    conn = psycopg.connect(dsn, **connect_kwargs)
    register_vector(conn)
    return conn


def _embed_texts(texts: list, task_type: str = "retrieval_document") -> list:
    """Embed a list of texts using Gemini API. Returns list of float lists."""
    import google.generativeai as genai
    import numpy as np
    genai.configure(api_key=os.getenv("GOOGLE_API_KEY"))
    embeddings = []
    for text in texts:
        result = genai.embed_content(
            model=EMBEDDING_MODEL,
            content=text,
            task_type=task_type,
        )
        embeddings.append(np.array(result["embedding"], dtype=np.float32))
    return embeddings


def _embed_query(text: str) -> "np.ndarray":
    """Embed a single query string."""
    import numpy as np
    return _embed_texts([text], task_type="retrieval_query")[0]


class SimpleVectorStore:
    """
    Minimal vector store: PostgreSQL + pgvector + Google Gemini embeddings.
    Replaces langchain_postgres.PGVector — no langchain dependency.
    """

    def __init__(self, collection_name: str):
        self.collection_name = collection_name
        self._collection_id: str | None = None
        self._ensure_tables()

    def _ensure_tables(self):
        """Create pgvector tables and the named collection if they do not exist."""
        try:
            with _get_conn() as conn:
                with conn.cursor() as cur:
                    cur.execute("CREATE EXTENSION IF NOT EXISTS vector")

                    cur.execute("""
                        CREATE TABLE IF NOT EXISTS langchain_pg_collection (
                            uuid  UUID PRIMARY KEY,
                            name  VARCHAR NOT NULL,
                            cmetadata JSON
                        )
                    """)

                    cur.execute(f"""
                        CREATE TABLE IF NOT EXISTS langchain_pg_embedding (
                            id            SERIAL,
                            collection_id UUID REFERENCES langchain_pg_collection(uuid)
                                          ON DELETE CASCADE,
                            embedding     VECTOR({EMBEDDING_DIM}),
                            document      TEXT,
                            cmetadata     JSONB,
                            uuid          UUID
                        )
                    """)

                    # Get or create the named collection
                    cur.execute(
                        "SELECT uuid FROM langchain_pg_collection WHERE name = %s",
                        [self.collection_name],
                    )
                    row = cur.fetchone()
                    if row:
                        self._collection_id = str(row[0])
                    else:
                        self._collection_id = str(uuid4())
                        cur.execute(
                            "INSERT INTO langchain_pg_collection (uuid, name, cmetadata) VALUES (%s, %s, %s)",
                            [self._collection_id, self.collection_name, None],
                        )

                conn.commit()
            logger.info(
                f"Vector store ready — collection='{self.collection_name}' id={self._collection_id}"
            )
        except Exception as e:
            logger.error(f"Error initialising vector tables: {e}")
            raise

    def add_documents(self, docs) -> None:
        """
        Embed and store documents.
        Each doc must have .page_content (str) and .metadata (dict).
        """
        if not docs:
            return
        texts = [d.page_content for d in docs]
        embeddings = _embed_texts(texts, task_type="retrieval_document")
        try:
            with _get_conn() as conn:
                with conn.cursor() as cur:
                    for doc, emb in zip(docs, embeddings):
                        cur.execute(
                            """INSERT INTO langchain_pg_embedding
                               (collection_id, embedding, document, cmetadata, uuid)
                               VALUES (%s, %s, %s, %s, %s)""",
                            [
                                self._collection_id,
                                emb,
                                doc.page_content,
                                json.dumps(doc.metadata),
                                str(uuid4()),
                            ],
                        )
                conn.commit()
            logger.info(f"Stored {len(docs)} embeddings in '{self.collection_name}'")
        except Exception as e:
            logger.error(
                f"Error storing documents (tip: if dimension mismatch, drop and "
                f"recreate langchain_pg_embedding + langchain_pg_collection tables): {e}"
            )
            raise


def get_vector_store():
    """
    Returns the singleton SimpleVectorStore.
    Returns None (with a warning) if the DB is unreachable.
    """
    global _vector_store_instance
    if _vector_store_instance is None:
        try:
            _vector_store_instance = SimpleVectorStore(COLLECTION_NAME)
        except Exception as e:
            logger.warning(f"Vector database connection failed: {e}. Using fallback.")
            return None
    return _vector_store_instance


def retrieve_relevant_documents(query: str, k: int = 5) -> str:
    """
    Retrieve the top-k most relevant document chunks from the vector store.
    Returns a formatted string ready to inject into a prompt, or "" on failure.
    """
    try:
        query_emb = _embed_query(query)
        with _get_conn() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "SELECT uuid FROM langchain_pg_collection WHERE name = %s",
                    [COLLECTION_NAME],
                )
                row = cur.fetchone()
                if not row:
                    return ""
                collection_id = str(row[0])

                cur.execute(
                    """SELECT document, cmetadata
                       FROM langchain_pg_embedding
                       WHERE collection_id = %s
                       ORDER BY embedding <=> %s
                       LIMIT %s""",
                    [collection_id, query_emb, k],
                )
                rows = cur.fetchall()

        if not rows:
            return ""

        parts = []
        for i, (document, cmetadata) in enumerate(rows, 1):
            meta = cmetadata if isinstance(cmetadata, dict) else {}
            source = meta.get("source", "Unknown")
            parts.append(f"[Document {i} - {source}]\n{document}")

        return "\n\n".join(parts)

    except Exception as e:
        logger.error(f"Error retrieving documents: {e}")
        return ""
