"""Public, dated chart contract for the BrokerFlow page."""

from datetime import date
from typing import Literal

from ..models.base import Record
from .common import Envelope
from .prices import PricePoint


class BrokerFlowRank(Record):
    rank: int
    broker_code: str
    net_idr: int


class BrokerFlowPoint(Record):
    date: date
    net_shares: int | None
    cumulative_net_shares: int | None


class BrokerFlowSeries(Record):
    broker_code: str
    side: Literal["buyer", "seller"]
    points: list[BrokerFlowPoint]


class DailyBrokerQuantity(Record):
    broker_code: str
    shares: int


class BrokerFlowDay(Record):
    date: date
    available: bool
    top_buyers: list[DailyBrokerQuantity]
    top_sellers: list[DailyBrokerQuantity]


class BrokerFlowResponse(Envelope):
    range: Literal["5d", "1m", "3m"]
    effective_start: date
    effective_end: date
    incomplete_history: bool
    excluded_price_dates: list[date]
    prices: list[PricePoint]
    top_buyers: list[BrokerFlowRank]
    top_sellers: list[BrokerFlowRank]
    broker_series: list[BrokerFlowSeries]
    days: list[BrokerFlowDay]
