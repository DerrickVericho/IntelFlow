"""Provider schemas for focused Sectors company-detail endpoints."""

from datetime import date

from pydantic import BaseModel, ConfigDict


class RevenueSegmentDetail(BaseModel):
    model_config = ConfigDict(extra="ignore")

    value: int | float
    source: str
    target: str


class RevenueSegmentList(BaseModel):
    model_config = ConfigDict(extra="ignore")

    symbol: str
    financial_year: int
    revenue_breakdown: list[RevenueSegmentDetail]


class ShareholderDetail(BaseModel):
    model_config = ConfigDict(extra="ignore")

    date: date
    shares_number: int
    insurance_l: int
    corporate_l: int
    pension_fund_l: int
    financial_institutions_l: int
    individual_l: int
    mutual_fund_l: int
    securities_companies_l: int
    foundation_l: int
    other_l: int
    total_l: int
    insurance_f: int
    corporate_f: int
    pension_fund_f: int
    financial_institutions_f: int
    individual_f: int
    mutual_fund_f: int
    securities_companies_f: int
    foundation_f: int
    other_f: int
    total_f: int
    numbers_of_shareholders: int
    change_in_shareholders: int


class ShareholderList(BaseModel):
    model_config = ConfigDict(extra="ignore")

    symbol: str
    year: int
    data: list[ShareholderDetail]
