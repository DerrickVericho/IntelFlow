"""Central logging configuration for the IntelFlow backend."""

from __future__ import annotations

import json
import logging
import logging.config
import os
import sys
import traceback
from contextvars import ContextVar, Token
from datetime import UTC, datetime
from typing import Any

from dotenv import load_dotenv

_request_id: ContextVar[str] = ContextVar("request_id", default="-")
_client_ip: ContextVar[str] = ContextVar("client_ip", default="-")


class RequestContextFilter(logging.Filter):
    """Attach request metadata without retaining a request or response body."""

    def filter(self, record: logging.LogRecord) -> bool:
        record.request_id = _request_id.get()
        record.client_ip = _client_ip.get()
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
            "client_ip": getattr(record, "client_ip", "-"),
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


class TextFormatter(logging.Formatter):
    """Readable local-console view of the same redacted structured fields."""

    COLORS = {
        "DEBUG": "\033[36m",
        "INFO": "\033[32m",
        "WARNING": "\033[33m",
        "ERROR": "\033[31m",
        "CRITICAL": "\033[35m",
    }

    def __init__(self, *, color: bool | None = None) -> None:
        super().__init__()
        self.color = (
            color
            if color is not None
            else os.getenv("NO_COLOR") is None
            and (sys.stdout.isatty() or os.getenv("FORCE_COLOR") is not None)
        )

    def format(self, record: logging.LogRecord) -> str:
        payload = json.loads(JsonFormatter().format(record))
        plain_level = payload.pop("level")
        level = f"{plain_level:<7}"
        if self.color:
            level = f"{self.COLORS.get(plain_level, '')}{level}\033[0m"
        timestamp = payload.pop("timestamp")
        logger_name = payload.pop("logger")
        request_id = payload.pop("request_id")
        client_ip = payload.pop("client_ip")
        message = payload.pop("message")
        fields = " ".join(f"{key}={value}" for key, value in payload.items())
        return (
            f"{timestamp} {level} {logger_name} "
            f"request_id={request_id} client_ip={client_ip} {message} {fields}"
        ).rstrip()


def set_request_id(value: str) -> Token[str]:
    """Set the request ID for the current async context."""

    return _request_id.set(value)


def reset_request_id(token: Token[str]) -> None:
    """Restore the request ID context after a request finishes."""

    _request_id.reset(token)


def set_client_ip(value: str) -> Token[str]:
    return _client_ip.set(value)


def reset_client_ip(token: Token[str]) -> None:
    _client_ip.reset(token)


def configure_logging(level: str | None = None) -> None:
    """Send development text or production JSON to stdout only."""

    load_dotenv()
    log_level = (level or os.getenv("LOG_LEVEL", "INFO")).upper()
    valid_levels = {"CRITICAL", "ERROR", "WARNING", "INFO", "DEBUG"}
    if log_level not in valid_levels:
        log_level = "INFO"
    formatter = (
        TextFormatter
        if os.getenv("APP_ENV", "development").lower() == "development"
        else JsonFormatter
    )

    logging.config.dictConfig(
        {
            "version": 1,
            "disable_existing_loggers": False,
            "filters": {
                "request_context": {"()": RequestContextFilter},
            },
            "formatters": {"default": {"()": formatter}},
            "handlers": {
                "console": {
                    "class": "logging.StreamHandler",
                    "formatter": "default",
                    "filters": ["request_context"],
                    "stream": "ext://sys.stdout",
                },
            },
            "root": {"handlers": ["console"], "level": log_level},
            "loggers": {
                "uvicorn": {
                    "handlers": ["console"],
                    "level": log_level,
                    "propagate": False,
                },
                "uvicorn.error": {
                    "handlers": ["console"],
                    "level": log_level,
                    "propagate": False,
                },
                "uvicorn.access": {
                    "handlers": [],
                    "level": "CRITICAL",
                    "propagate": False,
                },
            },
        }
    )
