from dotenv import load_dotenv
import os
from typing import Optional

# Load .env file explicitly with absolute path
env_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env")
load_dotenv(env_path, override=True)

import sys
import logging
import traceback
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request, HTTPException
logging.basicConfig(level=logging.INFO)
log = logging.getLogger(__name__)

log.info(f"GOOGLE_API_KEY present: {'GOOGLE_API_KEY' in os.environ}")
log.info(f"Working directory: {os.getcwd()}")
log.info(f"Python version: {sys.version}")

# Track startup errors for diagnostics
_startup_errors = []

# Try to import routers — catch errors so health check always passes
chat_router = None
admin_router = None
RateLimitMiddleware = None

try:
    from src.controller.chat_controller import router as chat_router
    log.info("✅ chat_controller loaded")
except Exception as e:
    err = f"chat_controller import failed: {type(e).__name__}: {e}\n{traceback.format_exc()}"
    log.error(err)
    _startup_errors.append(err)

try:
    from src.controller.admin_controller import router as admin_router
    log.info("✅ admin_controller loaded")
except Exception as e:
    err = f"admin_controller import failed: {type(e).__name__}: {e}\n{traceback.format_exc()}"
    log.error(err)
    _startup_errors.append(err)

try:
    from src.middleware.rate_limit import RateLimitMiddleware
    log.info("✅ rate_limit loaded")
except Exception as e:
    err = f"rate_limit import failed: {type(e).__name__}: {e}\n{traceback.format_exc()}"
    log.error(err)
    _startup_errors.append(err)

from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse


@asynccontextmanager
async def lifespan(app: FastAPI):
    import asyncio

    if _startup_errors:
        log.error(f"App started with {len(_startup_errors)} import error(s)")
    else:
        log.info("✅ App startup complete — all modules loaded")

    # Pre-warm LLM — run in a thread so blocking network call doesn't freeze the event loop
    try:
        from src.controller.chat_controller import get_health_service
        svc = get_health_service()
        await asyncio.wait_for(asyncio.to_thread(svc._init_llm), timeout=30)
        log.info("✅ Pre-warmed: HealthChatService + LLM ready")
    except asyncio.TimeoutError:
        log.warning("Pre-warm timeout: LLM will initialise on first request")
    except Exception as e:
        log.warning(f"Pre-warm skipped: {e}")

    # Pre-warm AdminRepository (DB connection)
    try:
        from src.repository.admin_repo import get_admin_repository
        await asyncio.wait_for(asyncio.to_thread(get_admin_repository), timeout=30)
        log.info("✅ Pre-warmed: AdminRepository loaded")
    except asyncio.TimeoutError:
        log.warning("Pre-warm timeout: AdminRepo will load on first request")
    except Exception as e:
        log.warning(f"AdminRepo pre-warm skipped: {e}")

    yield


app = FastAPI(
    title="Document-Based Q&A Voice Chatbot API",
    description="A FastAPI backend for document-based Q&A with TTS.",
    version="1.0.0",
    lifespan=lifespan,
)

# Rate Limiting Middleware (only if loaded)
if RateLimitMiddleware:
    app.add_middleware(RateLimitMiddleware, requests_per_minute=120)

# CORS: allow localhost (dev) and any HTTPS origin (production).
# iOS Safari sends strict CORS preflight requests — allowing all HTTPS origins
# prevents 403 blocks when the app is served from custom or Render/Railway domains.
app.add_middleware(
    CORSMiddleware,
    allow_origin_regex=r"(http://(localhost|127\.0\.0\.1)(:\d+)?|https://.*)",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["*"],
)

# Mount routers (only if loaded)
if chat_router:
    app.include_router(chat_router, tags=["Chat"])
if admin_router:
    app.include_router(admin_router, tags=["Admin"])


def _cors_headers(origin: Optional[str] = None):
    """Return CORS headers allowing the given origin if it is localhost or any HTTPS origin."""
    import re
    allowed_pattern = re.compile(r"(http://(localhost|127\.0\.0\.1)(:\d+)?|https://.*)")
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


@app.get("/ping", tags=["Health"])
def ping():
    """Ultra-lightweight keep-alive endpoint — use this for uptime monitors."""
    return {"ok": True}


@app.get("/", tags=["Health"])
def health_check():
    if _startup_errors:
        return {
            "status": "degraded",
            "errors": _startup_errors,
            "python": sys.version,
        }
    return {"status": "FastAPI is running successfully!"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=int(os.getenv("PORT", 8000)))
