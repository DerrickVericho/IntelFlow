"""Provider schema for Sectors screener responses."""

from pydantic import BaseModel, ConfigDict


class FreeFloat(BaseModel):
    model_config = ConfigDict(extra="ignore")

    symbol: str
    company_name: str
    free_float: float
