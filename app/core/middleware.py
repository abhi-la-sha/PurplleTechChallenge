"""HTTP middleware for structured request logging."""

import logging
import time
import uuid
from collections.abc import Callable

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

from app.core.logging import safe_extra

logger = logging.getLogger("app.request")


class StructuredLoggingMiddleware(BaseHTTPMiddleware):
    """Emit one JSON log line per HTTP request."""

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        request_id = request.headers.get("X-Request-ID", str(uuid.uuid4()))
        start = time.perf_counter()

        response: Response | None = None
        error: str | None = None
        try:
            response = await call_next(request)
            return response
        except Exception as exc:
            error = repr(exc)
            raise
        finally:
            duration_ms = (time.perf_counter() - start) * 1000
            status_code = response.status_code if response is not None else 500
            log_extra = safe_extra(
                event_message="http_request",
                request_id=request_id,
                method=request.method,
                path=request.url.path,
                status_code=status_code,
                duration_ms=round(duration_ms, 2),
                client_host=request.client.host if request.client else None,
                error=error,
            )
            if error:
                logger.error("request_failed", extra=log_extra)
            else:
                logger.info("request_completed", extra=log_extra)

            if response is not None:
                response.headers["X-Request-ID"] = request_id
