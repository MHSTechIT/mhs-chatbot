"""
Rate limiting middleware for FastAPI.
Prevents API abuse by limiting requests per IP address.
"""

import time
from collections import defaultdict
from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse
import logging

logger = logging.getLogger(__name__)


class RateLimitMiddleware(BaseHTTPMiddleware):
    """
    Simple rate limiting middleware based on IP address.
    """

    def __init__(self, app, requests_per_minute: int = 60):
        super().__init__(app)
        self.requests_per_minute = requests_per_minute
        self.request_history = defaultdict(list)

    async def dispatch(self, request: Request, call_next):
        """
        Check rate limit and forward request if within limits.
        """
        # Get client IP
        client_ip = request.client.host if request.client else "unknown"

        # Current time in seconds
        current_time = time.time()
        cutoff_time = current_time - 60  # Last 60 seconds

        # Clean up old requests
        if client_ip in self.request_history:
            self.request_history[client_ip] = [
                req_time for req_time in self.request_history[client_ip]
                if req_time > cutoff_time
            ]

        # Check if exceeded limit
        request_count = len(self.request_history[client_ip])
        if request_count >= self.requests_per_minute:
            logger.warning(f"Rate limit exceeded for {client_ip}: {request_count} requests")
            return JSONResponse(
                status_code=429,
                content={"detail": f"Rate limit exceeded. Max {self.requests_per_minute} requests per minute."}
            )

        # Record this request
        self.request_history[client_ip].append(current_time)

        # Continue with request
        response = await call_next(request)
        return response
