"""Research-use-case failures and their public HTTP identities."""

from .base import AppError


class ResearchError(AppError):
    """Base class for research-specific failures."""

    code = "RESEARCH_ERROR"
    http_status = 500


class InvalidSymbolError(ResearchError):
    code = "INVALID_SYMBOL"
    http_status = 422


class InvalidWindowError(ResearchError):
    code = "INVALID_WINDOW"
    http_status = 422


class InvalidRangeError(ResearchError):
    code = "INVALID_RANGE"
    http_status = 422


class InvalidYearError(ResearchError):
    code = "INVALID_YEAR"
    http_status = 422


class InvalidBrokersError(ResearchError):
    code = "INVALID_BROKERS"
    http_status = 422


class DataNotFoundError(ResearchError):
    code = "DATA_NOT_FOUND"
    http_status = 404


class ResearchUnavailableError(ResearchError):
    code = "UPSTREAM_UNAVAILABLE"
    http_status = 503
