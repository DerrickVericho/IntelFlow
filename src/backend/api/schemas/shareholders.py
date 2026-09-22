"""Response schemas for monthly shareholder composition."""

from datetime import date

from ...domain.models.base import Record
from .common import Envelope


class Category(Record):
    key: str
    label: str


class ShareholderPoint(Record):
    date: date
    shares_number: int
    holdings: dict[str, int | None]
    total_local: int
    total_foreign: int
    shareholder_count: int
    shareholder_count_change: int


class ShareholderResponse(Envelope):
    year: int
    supported_years: list[int]
    categories: list[Category]
    series: list[ShareholderPoint]
