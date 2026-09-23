"""Fields shared by every analytical HTTP response."""

from datetime import date
from typing import Literal

from ..models.base import Record
from ..models.common import MissingInput, Source


class Envelope(Record):
    symbol: str
    as_of: date | None
    status: Literal["complete", "partial", "stale"]
    sources: list[Source]
    missing_inputs: list[MissingInput]
