"""Central logging configuration for the IntelFlow backend."""

from __future__ import annotations

import logging
import logging.config
import os
import json
import traceback
from pathlib import Path
from contextvars import ContextVar, Token
from datetime import UTC, datetime
from typing import Any
from dotenv import load_dotenv

_request_id: ContextVar[str] = ContextVar("request_id", default="-")


class RequestContextFilter(logging.Filter):
    """Attach the current request ID to every log record."""

    def filter(self, record: logging.LogRecord) -> bool:
        record.request_id = _request_id.get()
        return True


class JsonFormatter(logging.Formatter):
    """Render application logs as one JSON object per line."""

    EXTRA_FIELDS = (
        "method",
        "path",
        "status_code",
        "duration_ms",
        "error_code",
        "error_type",
        "upstream_status",
        "sectors_path",
        "sectors_params",
        "operation",
        "cache_outcome",
    )

    def format(self, record: logging.LogRecord) -> str:
        payload: dict[str, Any] = {
            "timestamp": datetime.now(UTC).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "request_id": getattr(record, "request_id", "-"),
            "message": record.getMessage(),
        }
        for field in self.EXTRA_FIELDS:
            if hasattr(record, field):
                payload[field] = getattr(record, field)
        if record.exc_info:
            payload["error_type"] = record.exc_info[0].__name__
            # Exception messages and chained validation errors may contain raw
            # payloads or credentials. Keep locations without exception values.
            payload["traceback"] = [
                {"file": f.filename, "line": f.lineno, "function": f.name}
                for f in traceback.extract_tb(record.exc_info[2])
            ]
        return json.dumps(payload, ensure_ascii=False, default=str)


def set_request_id(value: str) -> Token[str]:
    """Set the request ID for the current async context."""

    return _request_id.set(value)


def reset_request_id(token: Token[str]) -> None:
    """Restore the request ID context after a request finishes."""

    _request_id.reset(token)


def configure_logging(level: str | None = None) -> None:
    """Configure application logging to stdout and daily rotating files.

    The API key and response bodies are intentionally never part of this
    configuration. Callers should log endpoint names and status metadata only.
    """

    load_dotenv()
    log_level = (level or os.getenv("LOG_LEVEL", "INFO")).upper()
    valid_levels = {"CRITICAL", "ERROR", "WARNING", "INFO", "DEBUG"}
    if log_level not in valid_levels:
        log_level = "INFO"
    log_path = Path(os.getenv("LOG_DIR", "logs"))
    log_path.mkdir(parents=True, exist_ok=True)

    logging.config.dictConfig(
        {
            "version": 1,
            "disable_existing_loggers": False,
            "filters": {
                "request_context": {"()": RequestContextFilter},
            },
            "formatters": {
                "default": {
                    "()": JsonFormatter,
                },
            },
            "handlers": {
                "file": {
                    "class": "logging.handlers.TimedRotatingFileHandler",
                    "filename": str(log_path / "intelflow.log"),
                    "when": "midnight",
                    "backupCount": 14,
                    "utc": True,
                    "encoding": "utf-8",
                    "formatter": "default",
                    "filters": ["request_context"],
                },
                "console": {
                    "class": "logging.StreamHandler",
                    "formatter": "default",
                    "filters": ["request_context"],
                    "stream": "ext://sys.stdout",
                },
            },
            "root": {
                "handlers": ["console", "file"],
                "level": log_level,
            },
        }
    )
