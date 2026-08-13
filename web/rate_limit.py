import os
import sys
from fastapi import Request
from fastapi.responses import JSONResponse
from slowapi import Limiter
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address

# Rate limiting is disabled if TESTING or TEST_MODE env var is set, or if running pytest
is_testing = (
    os.getenv("TESTING", "").lower() == "true"
    or os.getenv("TEST_MODE", "").lower() == "true"
    or "pytest" in sys.modules
)

limiter = Limiter(
    key_func=get_remote_address,
    enabled=not is_testing,
)


def custom_rate_limit_exceeded_handler(request: Request, exc: RateLimitExceeded):
    return JSONResponse(
        status_code=429,
        content={"error": "Rate limit exceeded. Please try again later."},
    )
