"""Company identity and synthesized research insight models."""

from typing import Literal

from .base import Record


class KeyPoint(Record):
    kind: Literal["evidence", "risk", "conflict", "unavailable"]
    title: str
    text: str
    source_keys: list[str]


class Company(Record):
    name: str | None = None
    sector: str | None = None
    sub_sector: str | None = None
    last_close_idr: int | None = None
