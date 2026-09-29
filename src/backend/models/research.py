"""Company identity and synthesized research insight models."""

from datetime import date
from typing import Literal

from pydantic import Field

from .base import Record


class KeyPoint(Record):
    kind: Literal["evidence", "risk", "conflict", "unavailable"]
    category: Literal["flow", "fundamental", "coverage"] = "flow"
    title: str
    text: str
    items: list[str] = Field(default_factory=list)
    source_keys: list[str]


class Company(Record):
    name: str | None = None
    sector: str | None = None
    sub_sector: str | None = None
    last_close_idr: int | None = None
    close_date: date | None = None
    previous_close_idr: int | None = None
    previous_close_date: date | None = None
    change_idr: int | None = None
    change_percent: float | None = None
