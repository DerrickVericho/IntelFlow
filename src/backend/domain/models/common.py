"""Provenance and missing-data records shared by analytical sections."""

from datetime import date, datetime

from .base import Record


class Source(Record):
    key: str
    provider: str = "sectors"
    as_of: date | None = None
    period: str | None = None
    fetched_at: datetime
    effective_start: date | None = None
    effective_end: date | None = None
    is_stale: bool = False


class MissingInput(Record):
    key: str
    reason: str
