"""Contract for retrieving data from the Sectors API.

Response schemas intentionally remain untyped until representative API output
has been reviewed and agreed on.
"""

from __future__ import annotations

from typing import Any, Protocol, Sequence


class SectorsGateway(Protocol):
    """Operations from Sectors API that IntelFlow currently depends on."""

    def get_free_float(
        self,
        *,
        sector: str | None = None,
        sub_sector: str | None = None,
        industry: str | None = None,
        sub_industry: str | None = None,
    ) -> Any: ...

    def get_daily(
        self,
        symbol: str,
        *,
        start: str | None = None,
        end: str | None = None,
    ) -> Any: ...

    def get_revenue_segments(
        self,
        symbol: str,
        *,
        financial_year: int | None = None,
    ) -> Any: ...

    def get_company_report(
        self,
        symbol: str,
        *,
        sections: Sequence[str],
    ) -> Any: ...

    def get_shareholder_composition(
        self,
        symbol: str,
        *,
        year: int | None = None,
    ) -> Any: ...

    def get_broker_summary(
        self,
        symbol: str,
        *,
        start: str | None = None,
        end: str | None = None,
        broker_code: str | None = None,
    ) -> Any: ...

    def get_top_brokers(
        self,
        symbol: str,
        *,
        start: str | None = None,
        end: str | None = None,
        cohort: str | None = None,
        origin: str | None = None,
        foreign: bool | None = None,
        n_brokers: int | None = None,
    ) -> Any: ...

    def get_foreign_flow(
        self,
        symbol: str,
        *,
        start: str | None = None,
        end: str | None = None,
    ) -> Any: ...

