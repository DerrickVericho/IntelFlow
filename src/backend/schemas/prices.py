"""Response schemas for OHLC and volume history."""

from datetime import date

from ..models.base import Record
from .common import Envelope


class PricePoint(Record):
    date: date
    open: int | None
    high: int | None
    low: int | None
    close: int
    volume: int
    market_cap: int | None


class PriceResponse(Envelope):
    range: str
    effective_start: date | None
    effective_end: date | None
    incomplete_history: bool
    series: list[PricePoint]
