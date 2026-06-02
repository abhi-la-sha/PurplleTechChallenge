
import logging
import sys
from typing import Any

from pythonjsonlogger.json import JsonFormatter

from app.core.config import Settings

# Keys that cannot be passed via logging extra= (reserved on LogRecord).
RESERVED_LOGRECORD_KEYS = frozenset(
    {
        "message",
        "msg",
        "name",
        "levelname",
        "pathname",
        "filename",
        "lineno",
        "module",
        "funcName",
        "created",
        "msecs",
        "relativeCreated",
        "thread",
        "threadName",
        "process",
        "processName",
        "args",
        "exc_info",
        "exc_text",
        "stack_info",
        "levelno",
    }
)


def safe_extra(**fields: Any) -> dict[str, Any]:
    """Build an extra dict omitting reserved LogRecord attribute names."""
    return {key: value for key, value in fields.items() if key not in RESERVED_LOGRECORD_KEYS}


class CustomJsonFormatter(JsonFormatter):
    """JSON log formatter with consistent field names."""

    def add_fields(
        self,
        log_record: dict[str, Any],
        record: logging.LogRecord,
        message_dict: dict[str, Any],
    ) -> None:
        super().add_fields(log_record, record, message_dict)
        log_record.setdefault("level", record.levelname)
        log_record.setdefault("logger", record.name)
        if not log_record.get("timestamp"):
            log_record["timestamp"] = self.formatTime(record, self.datefmt)


def setup_logging(settings: Settings) -> None:
    """Configure root logger for structured JSON output."""
    root = logging.getLogger()
    root.handlers.clear()

    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(
        CustomJsonFormatter(
            "%(timestamp)s %(level)s %(name)s %(message)s",
            rename_fields={"levelname": "level", "name": "logger"},
        )
    )

    level = getattr(logging, settings.log_level.upper(), logging.INFO)
    root.setLevel(level)
    root.addHandler(handler)

    logging.getLogger("uvicorn.access").handlers = []
    logging.getLogger("uvicorn.error").handlers = []
