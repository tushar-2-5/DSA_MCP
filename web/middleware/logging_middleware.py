import sys
import logging
import time
import uuid
from starlette.middleware.base import BaseHTTPMiddleware

logging.basicConfig(stream=sys.stderr, level=logging.INFO)
logger = logging.getLogger("recall.api")


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        request_id = str(uuid.uuid4())[:8]
        start = time.time()
        response = await call_next(request)
        duration = round((time.time() - start) * 1000, 2)
        logger.info(
            f"[{request_id}] {request.method} {request.url.path} "
            f"-> {response.status_code} ({duration}ms)"
        )
        return response
