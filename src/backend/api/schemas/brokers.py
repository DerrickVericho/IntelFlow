"""Response schemas for selectable broker timelines."""

from datetime import date

from ...domain.models.base import Record
from .common import Envelope


class BrokerPoint(Record):
    date: date
    buy_idr: int | None
    sell_idr: int | None
    net_idr: int | None
    cumulative_net_idr: int | None


class BrokerSeries(Record):
    broker_code: str
    points: list[BrokerPoint]


class BrokerResponse(Envelope):
    range: str
    effective_start: date
    effective_end: date
    incomplete_history: bool
    default_brokers: list[str]
    selected_brokers: list[str]
    available_brokers: list[str]
    series: list[BrokerSeries]
