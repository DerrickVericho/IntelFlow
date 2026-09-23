"""Failures produced by the Sectors transport and provider boundary."""

from __future__ import annotations

from typing import Any

from .base import AppError


class SectorsError(AppError):
    """Base exception for Sectors integration failures."""

    code = "UPSTREAM_INVALID_RESPONSE"
    http_status = 503

    def __init__(
        self,
        message: str,
        *,
        status_code: int | None = None,
        details: Any = None,
    ) -> None:
        super().__init__(message)
        self.status_code = status_code
        self.details = details


class SectorsConfigurationError(SectorsError):
    """The client is missing required local configuration."""

    code = "UPSTREAM_CONFIGURATION_ERROR"
    http_status = 503


class SectorsValidationError(SectorsError):
    """A request is invalid locally or rejected with HTTP 400."""

    code = "UPSTREAM_REQUEST_REJECTED"
    http_status = 503


class SectorsAuthenticationError(SectorsError):
    """Authentication failed with HTTP 401 or 403."""

    code = "UPSTREAM_AUTHENTICATION_ERROR"
    http_status = 503


class SectorsNotFoundError(SectorsError):
    """The requested symbol or dataset was not found."""

    code = "DATA_NOT_FOUND"
    http_status = 404


class SectorsRateLimitError(SectorsError):
    """The API rate or credit limit was reached."""

    code = "UPSTREAM_RATE_LIMIT"
    http_status = 503


class SectorsUpstreamError(SectorsError):
    """The upstream API timed out or returned a server/network failure."""

    code = "UPSTREAM_UNAVAILABLE"
    http_status = 503


class SectorsResponseError(SectorsError):
    """The upstream API returned an unreadable or inconsistent response."""

    code = "UPSTREAM_INVALID_RESPONSE"
    http_status = 503
