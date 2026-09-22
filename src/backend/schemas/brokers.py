"""Provider schemas for Sectors broker and foreign-flow responses."""

from datetime import date

from pydantic import BaseModel, ConfigDict


class BrokerActivitySummary(BaseModel):
    model_config = ConfigDict(extra="ignore")

    broker_code: str
    bfreq: int
    blot: int
    bval: int
    bavg_per_share: float | None = None
    sfreq: int
    slot: int
    sval: int
    savg_per_share: float | None = None
    nlot: int
    nval: int
    navg_per_share: float | None = None
    f_bfreq: int | None = None
    f_blot: int | None = None
    f_bval: int | None = None
    f_bavg_per_share: float | None = None
    d_bavg_per_share: float | None = None
    f_sfreq: int | None = None
    f_slot: int | None = None
    f_sval: int | None = None
    f_savg_per_share: float | None = None
    d_savg_per_share: float | None = None


class BrokerActivitySymbolDetails(BaseModel):
    model_config = ConfigDict(extra="ignore")

    date: date
    summary: list[BrokerActivitySummary]


class BrokerActivityList(BaseModel):
    model_config = ConfigDict(extra="ignore")

    symbol: str
    start: date
    end: date
    data: list[BrokerActivitySymbolDetails]


class ForeignFlowDetails(BaseModel):
    model_config = ConfigDict(extra="ignore")

    date: date
    net_foreign_inflow: int
    foreign_buy_idr: int
    foreign_sell_idr: int
    foreign_share: float


class ForeignFlowList(BaseModel):
    model_config = ConfigDict(extra="ignore")

    symbol: str
    start: date
    end: date
    data: list[ForeignFlowDetails]


class TopBrokerDetails(BaseModel):
    model_config = ConfigDict(extra="ignore")

    rank: int
    broker_code: str
    net_idr: int
    buy_idr: int
    sell_idr: int
    foreign_net_idr: int
    foreign_buy_idr: int
    foreign_sell_idr: int


class TopBrokerList(BaseModel):
    model_config = ConfigDict(extra="ignore")

    symbol: str
    start: date
    end: date
    origin: str
    cohort: str
    foreign: bool
    top_buyers: list[TopBrokerDetails]
    top_sellers: list[TopBrokerDetails]
