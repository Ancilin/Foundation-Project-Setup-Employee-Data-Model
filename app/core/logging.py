"""Structured JSON Logging for LedgerForge (Task 18).

Provides:
- JSONFormatter: Formats all python log records as single-line JSON objects.
- setup_logging: Configures root and uvicorn loggers to emit structured JSON.
- RequestLoggingMiddleware: Logs every incoming HTTP request with method, path, status, and duration_ms.
"""

from datetime import datetime, timezone
import json
import logging
import sys
import time
from typing import Any

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

logger = logging.getLogger("ledgerforge")


class JSONFormatter(logging.Formatter):
    """Formats log records as JSON strings for centralized log aggregation."""

    def format(self, record: logging.LogRecord) -> str:
        log_obj: dict[str, Any] = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        if record.exc_info:
            log_obj["exception"] = self.formatException(record.exc_info)
        # Capture custom extra fields if passed
        for k, v in record.__dict__.items():
            if k not in (
                "args", "asctime", "created", "exc_info", "exc_text", "filename",
                "funcName", "id", "levelname", "levelno", "lineno", "module",
                "msecs", "message", "msg", "name", "pathname", "process",
                "processName", "relativeCreated", "stack_info", "thread", "threadName"
            ):
                log_obj[k] = v
        return json.dumps(log_obj)


def setup_logging(level: int = logging.INFO) -> None:
    """Configure the root logger and uvicorn loggers with JSONFormatter."""
    root_logger = logging.getLogger()
    root_logger.setLevel(level)

    # Avoid duplicate handlers
    for h in root_logger.handlers[:]:
        root_logger.removeHandler(h)

    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(JSONFormatter())
    root_logger.addHandler(handler)

    # Configure uvicorn loggers to use the same format
    for uvicorn_log in ("uvicorn", "uvicorn.access", "uvicorn.error"):
        ulog = logging.getLogger(uvicorn_log)
        ulog.handlers = [handler]
        ulog.propagate = False


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """Logs every HTTP request with duration, client IP, method, and response status."""

    async def dispatch(self, request: Request, call_next) -> Response:
        start_time = time.perf_counter()
        client_ip = request.client.host if request.client else "unknown"

        response = await call_next(request)

        duration_ms = round((time.perf_counter() - start_time) * 1000.0, 2)
        # Skip excessive logging for docs assets or favicon
        path = request.url.path
        if not path.startswith("/static") and not path.endswith(".ico"):
            log_data = {
                "method": request.method,
                "path": path,
                "status_code": response.status_code,
                "duration_ms": duration_ms,
                "client_ip": client_ip,
            }
            logger.info(f"{request.method} {path} {response.status_code} in {duration_ms}ms", extra=log_data)

        return response
