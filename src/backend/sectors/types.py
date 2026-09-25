"""Shared types for the Sectors boundary."""

from dataclasses import dataclass
from datetime import datetime
from typing import Generic, Literal, TypeVar

T = TypeVar("T")

Operation = Literal[
    "get_daily",
    "get_free_float",
    "get_broker_summary",
    "get_top_brokers",
    "get_foreign_flow",
    "get_company_report",
    "get_shareholder_composition",
    "get_revenue_segments",
]


@dataclass(frozen=True)
class Retrieved(Generic[T]):
    """Validated provider data together with its retrieval time."""

    data: T
    fetched_at: datetime
