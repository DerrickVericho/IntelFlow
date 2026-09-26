"""Deterministic synthetic market fixture, never presented as live Sectors data."""

from copy import deepcopy
from datetime import date, timedelta
from collections import Counter
from collections.abc import Callable
from typing import Any
from ..exceptions.sectors import SectorsNotFoundError

TODAY = date(2026, 9, 22)


class FixtureTransport:
    def __init__(self) -> None:
        self.calls: Counter[str] = Counter()
        self.failures: dict[str, Exception] = {}
        self.days = [
            TODAY - timedelta(days=n)
            for n in range(89, -1, -1)
            if (TODAY - timedelta(days=n)).weekday() < 5
        ]
        self.rows = [
            dict(
                symbol="TEST.JK",
                date=d.isoformat(),
                close=1000 + i,
                open=1000,
                high=1100,
                low=900,
                volume=100000 + i * 1000,
                market_cap=1000000000,
            )
            for i, d in enumerate(self.days)
        ]

    def __getattr__(self, operation: str) -> Callable[..., Any]:
        def get(symbol: str = "TEST", **params: Any) -> Any:
            self.calls[operation] += 1
            if operation in self.failures:
                raise self.failures[operation]
            if symbol != "TEST":
                raise SectorsNotFoundError("Fixture ticker not found.")
            return deepcopy(getattr(self, "_" + operation)(**params))

        return get

    def _get_daily(self, **params: Any) -> list[dict[str, Any]]:
        return self.rows

    def _get_top_brokers(
        self,
        start: str,
        end: str,
        **params: Any,
    ) -> dict[str, Any]:
        def row(i: int, side: int) -> dict[str, Any]:
            return dict(
                rank=i + 1,
                broker_code=("B" if side == 1 else "S") + str(i),
                net_idr=side * (10000 - i * 500) * (2 if side == 1 else 1),
                buy_idr=50000,
                sell_idr=50000 - side * (10000 - i * 500) * (2 if side == 1 else 1),
                foreign_net_idr=100,
                foreign_buy_idr=200,
                foreign_sell_idr=100,
            )

        return dict(
            symbol="TEST.JK",
            start=start,
            end=end,
            origin="all",
            cohort="all",
            foreign=False,
            top_buyers=[row(i, 1) for i in range(10)],
            top_sellers=[row(i, -1) for i in range(10)],
        )

    def _get_foreign_flow(self, start: str, end: str) -> dict[str, Any]:
        return dict(
            symbol="TEST.JK",
            start=start,
            end=end,
            data=[
                dict(
                    date=d.isoformat(),
                    net_foreign_inflow=5000,
                    foreign_buy_idr=10000,
                    foreign_sell_idr=5000,
                    foreign_share=0.3,
                )
                for d in self.days
                if start <= d.isoformat() <= end
            ],
        )

    def _get_company_report(self, sections: list[str]) -> dict[str, Any]:
        overview = dict(
            industry="Test",
            sub_industry="Test",
            sector="Test",
            sub_sector="Test",
            market_cap=1000000000,
            market_cap_rank=1,
        )
        financials = dict(
            historical_eps={},
            eps=100,
            yoy_quarter_revenue_growth=0.1,
            yoy_quarter_earnings_growth=0.2,
            historical_financials=[
                dict(
                    year=y,
                    revenue=100000 * (y - 2020),
                    earnings=10000 * (y - 2020),
                    operating_pnl=12000,
                    operating_cash_flow=15000,
                    free_cash_flow=10000,
                    capital_expenditure=-5000,
                    total_equity=50000,
                )
                for y in range(2022, 2026)
            ],
            historical_financial_ratio=[
                dict(
                    year=y,
                    profitability=dict(
                        roa=0.1,
                        roe=0.2,
                        net_profit_margin=0.15,
                        operating_profit_margin=0.2,
                    ),
                )
                for y in range(2022, 2026)
            ],
        )
        valuation = dict(
            last_close_price=1100,
            latest_close_date=TODAY.isoformat(),
            historical_valuation=[
                dict(
                    year=y,
                    pe=20 - (y - 2022),
                    pb=3,
                    ps=4,
                    pcf=5,
                    pe_peer_avg=20,
                    pb_peer_avg=3,
                    ps_peer_avg=4,
                )
                for y in range(2022, 2027)
            ],
        )
        all_sections = dict(
            overview=overview, financials=financials, valuation=valuation
        )
        return dict(
            symbol="TEST.JK",
            company_name="Synthetic Fixture Company",
            **{s: all_sections[s] for s in sections},
        )

    def _get_shareholder_composition(self, year: int) -> dict[str, Any]:
        categories = (
            "insurance",
            "corporate",
            "pension_fund",
            "financial_institutions",
            "individual",
            "mutual_fund",
            "securities_companies",
            "foundation",
            "other",
        )
        return dict(
            symbol="TEST.JK",
            year=year,
            data=[
                dict(
                    date=f"{year}-06-30",
                    shares_number=10000,
                    **{f"{c}_{s}": 100 for c in categories for s in ("l", "f")},
                    total_l=900,
                    total_f=900,
                    numbers_of_shareholders=50,
                    change_in_shareholders=2,
                )
            ],
        )

    def _get_broker_summary(self, start: str, end: str) -> dict[str, Any]:
        return dict(
            symbol="TEST.JK",
            start=start,
            end=end,
            data=[
                dict(
                    date=d.isoformat(),
                    summary=[
                        dict(
                            broker_code=c,
                            bfreq=1,
                            blot=20,
                            bval=2000 + net,
                            sfreq=1,
                            slot=20,
                            sval=2000,
                            nlot=0,
                            nval=net,
                        )
                        for c, net in (
                            ("B0", 1000),
                            ("B1", 500),
                            ("B2", 250),
                            ("S0", -1000),
                            ("S1", -500),
                            ("S2", -250),
                        )
                    ],
                )
                for d in self.days
                if start <= d.isoformat() <= end
            ],
        )
