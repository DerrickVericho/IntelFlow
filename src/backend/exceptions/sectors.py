"""Failures produced by the Sectors transport and provider boundary."""

from __future__ import annotations

from typing import Any


class SectorsError(Exception):
    """Base exception for Sectors integration failures."""

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


class SectorsValidationError(SectorsError):
    """A request is invalid locally or rejected with HTTP 400."""


class SectorsAuthenticationError(SectorsError):
    """Authentication failed with HTTP 401 or 403."""


class SectorsNotFoundError(SectorsError):
    """The requested symbol or dataset was not found."""


class SectorsRateLimitError(SectorsError):
    """The API rate or credit limit was reached."""


class SectorsUpstreamError(SectorsError):
    """The upstream API timed out or returned a server/network failure."""


class SectorsResponseError(SectorsError):
    """The upstream API returned an unreadable or inconsistent response."""
