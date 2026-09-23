"""Broker, foreign-flow, and liquidity evidence models."""

from datetime import date
from typing import Literal

from pydantic import Field

from .base import Record


class BrokerBar(Record):
    broker_code: str
    side: Literal["buyer", "seller"]
    rank: int
    buy_idr: int
    sell_idr: int
    net_idr: int
    foreign_net_idr: int | None = None


class Breadth(Record):
    top_n: int
    buyer_net_idr: int
    seller_net_idr: int
    balance_idr: int
    balance_ratio: float | None
    buyer_count: int
    seller_count: int


class BrokerSummary(Record):
    brokers: list[BrokerBar] = Field(default_factory=list)
    breadth: list[Breadth] = Field(default_factory=list)


class ForeignPoint(Record):
    date: date
    net_inflow_idr: int
    cumulative_net_inflow_idr: int
    foreign_share_percent: float | None


class ForeignFlow(Record):
    net_inflow_idr: int | None = None
    buy_idr: int | None = None
    sell_idr: int | None = None
    average_foreign_share_percent: float | None = None
    positive_days: int = 0
    negative_days: int = 0
    series: list[ForeignPoint] = Field(default_factory=list)


class LiquidityPoint(Record):
    date: date
    close_idr: int
    volume_shares: int
    average_volume_shares: float | None
    volume_ratio: float | None
    baseline_observations: int


class Liquidity(Record):
    baseline_window: int = 20
    latest_volume_shares: int | None = None
    average_volume_shares: float | None = None
    latest_vs_average_ratio: float | None = None
    series: list[LiquidityPoint] = Field(default_factory=list)


class FlowEvidence(Record):
    window: Literal["1d", "5d", "20d"]
    effective_start: date | None = None
    effective_end: date | None = None
    trading_days: int = 0
    incomplete_history: bool = False
    broker_summary: BrokerSummary = Field(default_factory=BrokerSummary)
    foreign_flow: ForeignFlow = Field(default_factory=ForeignFlow)
    liquidity: Liquidity = Field(default_factory=Liquidity)
