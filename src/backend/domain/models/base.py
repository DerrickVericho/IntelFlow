"""Shared configuration for strict domain records."""

from pydantic import BaseModel, ConfigDict


class Record(BaseModel):
    """Base for normalized records that reject unknown and non-finite values."""

    model_config = ConfigDict(extra="forbid", allow_inf_nan=False)
