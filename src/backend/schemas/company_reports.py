"""Partial provider schemas for the Sectors Company Report endpoint."""

from __future__ import annotations

from datetime import date

from pydantic import BaseModel, ConfigDict, Field


# Currently skipped: future, management, and peers.


# Overview
class CompanyOverviewDetail(BaseModel):
    model_config = ConfigDict(extra="ignore")

    industry: str
    sub_industry: str
    sector: str
    sub_sector: str
    market_cap: int
    market_cap_rank: int
    esg_score: float | None = None
    indices: list[str] | None = None
    affiliates: list[str] | None = None


# Valuation
class HistoricalValuationDetail(BaseModel):
    """Small cross-sector valuation subset used by the MVP."""

    model_config = ConfigDict(extra="ignore")

    year: int
    pb: float | None = None
    pe: float | None = None
    ps: float | None = None
    pcf: float | None = None
    pb_peer_avg: float | None = None
    pe_peer_avg: float | None = None
    ps_peer_avg: float | None = None


class CompanyValuationDetail(BaseModel):
    model_config = ConfigDict(extra="ignore")

    last_close_price: int
    latest_close_date: date
    forward_pe: float | None = None
    historical_valuation: list[HistoricalValuationDetail]


# Financials
class HistoricalEpsDetail(BaseModel):
    model_config = ConfigDict(extra="ignore")

    eps: float
    eps_growth: float | None = None


class HistoricalFinancialDetail(BaseModel):
    """Minimal general-company statement fields used by the MVP."""

    model_config = ConfigDict(extra="ignore")

    year: int

    # Growth and earnings quality.
    revenue: int | None = None
    earnings: int | None = None
    operating_pnl: int | None = None

    # Cash-flow quality.
    operating_cash_flow: int | None = None
    free_cash_flow: int | None = None
    capital_expenditure: int | None = None

    # Balance-sheet support.
    total_assets: int | None = None
    total_equity: int | None = None
    total_liabilities: int | None = None
    total_debt: int | None = None
    cash_and_equivalents: int | None = None


class LeverageRatioDetail(BaseModel):
    model_config = ConfigDict(extra="ignore")

    debt_to_asset_ratio: float | None = None
    debt_to_equity_ratio: float | None = None


class LiquidityRatioDetail(BaseModel):
    model_config = ConfigDict(extra="ignore")

    current_ratio: float | None = None


class ProfitabilityRatioDetail(BaseModel):
    model_config = ConfigDict(extra="ignore")

    roa: float | None = None
    roe: float | None = None
    net_profit_margin: float | None = None
    operating_profit_margin: float | None = None


class HistoricalFinancialRatioDetail(BaseModel):
    model_config = ConfigDict(extra="ignore")

    year: int
    leverage: LeverageRatioDetail | None = None
    liquidity: LiquidityRatioDetail | None = None
    profitability: ProfitabilityRatioDetail | None = None


class CompanyFinancialsDetail(BaseModel):
    model_config = ConfigDict(extra="ignore")

    eps: float | None = None
    historical_eps: dict[str, HistoricalEpsDetail]
    historical_financials: list[HistoricalFinancialDetail]
    historical_financial_ratio: list[HistoricalFinancialRatioDetail]
    yoy_quarter_earnings_growth: float | None = None
    yoy_quarter_revenue_growth: float | None = None


# Dividend
class DividendHistoryBreakdown(BaseModel):
    date: date
    total: float
    yield_: float = Field(alias="yield")


class DividendHistoryYear(BaseModel):
    breakdown: list[DividendHistoryBreakdown]
    total_yield: float
    total_dividend: float


class DividendDetail(BaseModel):
    model_config = ConfigDict(extra="ignore")

    historical_dividends: dict[str, DividendHistoryYear] | None = None
    payout_ratio: float | None = None
    cash_payout_ratio: float | None = None


# Ownership
class MajorShareholderDetail(BaseModel):
    name: str
    share_value: int
    share_amount: int
    share_percentage: float


class InstitutionalTransactionFlowDetail(BaseModel):
    date: date
    net_transaction: int


class CompanyOwnershipDetail(BaseModel):
    model_config = ConfigDict(extra="ignore")

    major_shareholders: list[MajorShareholderDetail]
    institutional_transaction_flow: (
        list[InstitutionalTransactionFlowDetail] | None
    ) = None
    whale_investors: list[str] | None = None
    conglomerates_group: list[str] | None = None


# Every section is optional because Sectors returns only requested sections.
class CompanyReportList(BaseModel):
    model_config = ConfigDict(extra="ignore")

    symbol: str
    company_name: str
    overview: CompanyOverviewDetail | None = None
    valuation: CompanyValuationDetail | None = None
    financials: CompanyFinancialsDetail | None = None
    dividend: DividendDetail | None = None
    ownership: CompanyOwnershipDetail | None = None
