"""Deterministic score output models."""

from datetime import datetime

from pydantic import Field

from .base import Record


class Component(Record):
    key: str
    value: float | None = Field(default=None, ge=0, le=100)
    weight: float
    reason: str | None = None
    source_keys: list[str] = Field(default_factory=list)


class Score(Record):
    value: float | None = Field(default=None, ge=0, le=100)
    components: list[Component] = Field(default_factory=list)
    reason: str | None = None


class Scores(Record):
    flow: Score
    fundamental: Score
    combined: Score
    calculation_version: str
    calculated_at: datetime
    input_periods: dict[str, str | None]
    research_state: str
