from dotenv import load_dotenv
import os
from typing import Optional

# Load .env file explicitly with absolute path
env_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env")
load_dotenv(env_path, override=True)

import sys
import logging
import traceback
from logging.handlers import RotatingFileHandler
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request, HTTPException

# Rotating log — max 10 MB per file, keep only 2 backups (max ~20 MB total)
_log_handler = RotatingFileHandler(
    "app.log", maxBytes=10 * 1024 * 1024, backupCount=2
)
_log_handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(name)s: %(message)s"))
logging.basicConfig(level=logging.INFO, handlers=[_log_handler, logging.StreamHandler(sys.stdout)])
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

    # 🧹 Clean up leftover uploaded files from previous crashed/incomplete uploads
    try:
        import glob as _glob
        upload_dir = "uploads"
        os.makedirs(upload_dir, exist_ok=True)
        leftovers = _glob.glob(os.path.join(upload_dir, "*"))
        if leftovers:
            for f in leftovers:
                try:
                    os.remove(f)
                except Exception:
                    pass
            log.info(f"🧹 Cleaned {len(leftovers)} leftover file(s) from uploads folder")
        else:
            log.info("🧹 Uploads folder is clean")
    except Exception as e:
        log.warning(f"Upload cleanup skipped: {e}")

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

# CORS: allow localhost (dev) + explicit production origin from env.
# Set ALLOWED_ORIGIN=https://your-frontend-domain.com in production .env
_allowed_origin = os.getenv("ALLOWED_ORIGIN", "")
_cors_origins = [_allowed_origin] if _allowed_origin else []
_cors_regex = r"http://(localhost|127\.0\.0\.1)(:\d+)?"

app.add_middleware(
    CORSMiddleware,
    allow_origins=_cors_origins,
    allow_origin_regex=_cors_regex,
    allow_credentials=True,
    allow_methods=["GET", "POST", "DELETE", "OPTIONS"],
    allow_headers=["Content-Type", "Authorization"],
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
        content={"detail": "An internal error occurred. Please try again later.", "type": "internal_error"},
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
