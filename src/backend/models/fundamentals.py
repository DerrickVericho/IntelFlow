"""Cross-sector fundamental metric models."""

from typing import Literal

from pydantic import Field

from .base import Record


class MetricPoint(Record):
    period: str
    value: float | None


class Metric(Record):
    key: str
    label: str
    value: float | None
    unit: Literal["idr", "percent", "ratio"]
    period: str | None
    period_type: Literal["annual", "quarterly_yoy_undated"] = "annual"
    availability: Literal["available", "unavailable"]
    reason: str | None = None
    direction: Literal["up", "down", "flat", "unknown"] = "unknown"
    series: list[MetricPoint] = Field(default_factory=list)
    source_keys: list[str] = Field(default_factory=list)


class MetricGroup(Record):
    key: str
    label: str
    score: float | None = None
    metrics: list[Metric]


class Fundamentals(Record):
    reporting_period: str | None = None
    currency: str = "IDR"
    groups: list[MetricGroup]
