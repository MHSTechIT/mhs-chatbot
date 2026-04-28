import os
from fastapi import Header, HTTPException


async def verify_admin_key(x_admin_key: str = Header(default=None)):
    """
    FastAPI dependency — require X-Admin-Key header on all /admin routes.
    If ADMIN_API_KEY env var is not set, access is denied to force explicit config.
    """
    admin_key = os.getenv("ADMIN_API_KEY", "").strip()
    if not admin_key:
        raise HTTPException(
            status_code=503,
            detail="Admin access is not configured. Set ADMIN_API_KEY on the server."
        )
    if x_admin_key != admin_key:
        raise HTTPException(status_code=401, detail="Invalid or missing admin key.")
