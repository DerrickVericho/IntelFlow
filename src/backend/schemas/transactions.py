"""Provider schema for Sectors daily transaction rows."""

from datetime import date

from pydantic import BaseModel, ConfigDict


class DailyTransaction(BaseModel):
    model_config = ConfigDict(extra="ignore")

    symbol: str
    date: date
    close: int
    open: int | None = None
    high: int | None = None
    low: int | None = None
    volume: int
    market_cap: int
