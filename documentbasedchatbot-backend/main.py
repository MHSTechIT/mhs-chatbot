from dotenv import load_dotenv
import os

# Load .env file explicitly with absolute path
env_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env")
result = load_dotenv(env_path, override=True)

import logging
from fastapi import FastAPI, Request, HTTPException
logging.basicConfig(level=logging.INFO)
log = logging.getLogger(__name__)

# Debug: Log environment variable loading
log.info(f"Loading .env from: {env_path} (exists: {os.path.exists(env_path)}, loaded: {result})")
log.info(f"GOOGLE_API_KEY present: {'GOOGLE_API_KEY' in os.environ}")
log.info(f"GOOGLE_API_KEY value (first 10 chars): {os.getenv('GOOGLE_API_KEY', 'NOT SET')[:10] if os.getenv('GOOGLE_API_KEY') else 'NOT SET'}")
log.info(f"Working directory: {os.getcwd()}")
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from src.controller.chat_controller import router as chat_router
from src.controller.admin_controller import router as admin_router
from src.database import init_db
from src.middleware.rate_limit import RateLimitMiddleware

# Import all models so SQLAlchemy knows to create their tables
from src.models.enrollment import Enrollment
from src.models.document import Document

# Initialize database tables on startup
init_db()
log.info("✅ Database initialized")

app = FastAPI(
    title="Document-Based Q&A Voice Chatbot API",
    description="A FastAPI backend leveraging LangChain & Ollama to securely answer questions purely based on a specific company document.",
    version="1.0.0"
)

# Rate Limiting Middleware
app.add_middleware(RateLimitMiddleware, requests_per_minute=120)

# CORS: allow all localhost origins (Vite dev server uses dynamic ports)
app.add_middleware(
    CORSMiddleware,
    allow_origin_regex=r"(http://(localhost|127\.0\.0\.1)(:\d+)?|https://.*\.vercel\.app)",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["*"],
)

# Mount the Chatbot API endpoints
app.include_router(chat_router, tags=["Chat"])
app.include_router(admin_router, tags=["Admin"])


def _cors_headers(origin: str | None = None):
    """Headers so browser allows the response when origin is localhost frontend."""
    import re
    allowed_pattern = re.compile(r"(http://(localhost|127\.0\.0\.1)(:\d+)?|https://.*\.vercel\.app)")
    o = origin if (origin and allowed_pattern.match(origin)) else "http://localhost:5173"
    return {
        "Access-Control-Allow-Origin": o,
        "Access-Control-Allow-Credentials": "true",
        "Access-Control-Allow-Methods": "GET, POST, OPTIONS",
        "Access-Control-Allow-Headers": "Content-Type, Authorization",
    }


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Return JSON with explicit CORS so error responses are never blocked."""
    log.exception("Request failed: %s", exc)
    origin = request.headers.get("origin")
    cors = _cors_headers(origin)
    if isinstance(exc, HTTPException):
        return JSONResponse(
            status_code=exc.status_code,
            content={"detail": exc.detail},
            headers=cors,
        )
    return JSONResponse(
        status_code=500,
        content={"detail": str(exc), "type": "internal_error"},
        headers=cors,
    )


@app.get("/", tags=["Health"])
def health_check():
    return {"status": "FastAPI is running successfully!"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=int(os.getenv("PORT", 8000)))
