"""Async typed application boundary; SectorsClient remains raw transport."""

from __future__ import annotations

from typing import Protocol, Sequence
from .cached import Retrieved
from ..schemas.transactions import DailyTransaction
from ..schemas.screeners import FreeFloat
from ..schemas.brokers import BrokerActivityList, TopBrokerList, ForeignFlowList
from ..schemas.company_reports import CompanyReportList
from ..schemas.detail_reports import ShareholderList, RevenueSegmentList


class SectorsGateway(Protocol):
    """Operations from Sectors API that IntelFlow currently depends on."""

    async def get_free_float(
        self,
        *,
        sector: str | None = None,
        sub_sector: str | None = None,
        industry: str | None = None,
        sub_industry: str | None = None,
    ) -> Retrieved[list[FreeFloat]]: ...

    async def get_daily(
        self,
        symbol: str,
        *,
        start: str | None = None,
        end: str | None = None,
    ) -> Retrieved[list[DailyTransaction]]: ...

    async def get_revenue_segments(
        self,
        symbol: str,
        *,
        financial_year: int | None = None,
    ) -> Retrieved[RevenueSegmentList]: ...

    async def get_company_report(
        self,
        symbol: str,
        *,
        sections: Sequence[str],
    ) -> Retrieved[CompanyReportList]: ...

    async def get_shareholder_composition(
        self,
        symbol: str,
        *,
        year: int | None = None,
    ) -> Retrieved[ShareholderList]: ...

    async def get_broker_summary(
        self,
        symbol: str,
        *,
        start: str | None = None,
        end: str | None = None,
        broker_code: str | None = None,
    ) -> Retrieved[BrokerActivityList]: ...

    async def get_top_brokers(
        self,
        symbol: str,
        *,
        start: str | None = None,
        end: str | None = None,
        cohort: str | None = None,
        origin: str | None = None,
        foreign: bool | None = None,
        n_brokers: int | None = None,
    ) -> Retrieved[TopBrokerList]: ...

    async def get_foreign_flow(
        self,
        symbol: str,
        *,
        start: str | None = None,
        end: str | None = None,
    ) -> Retrieved[ForeignFlowList]: ...
