"""Provider schema for Sectors daily transaction rows."""

from datetime import date

from pydantic import BaseModel, ConfigDict, Field


class DailyTransaction(BaseModel):
    model_config = ConfigDict(extra="ignore")

    symbol: str
    date: date
    close: int = Field(ge=0)
    open: int | None = None
    high: int | None = None
    low: int | None = None
    volume: int = Field(ge=0)
    market_cap: int
