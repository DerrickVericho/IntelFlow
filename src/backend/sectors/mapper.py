"""Pure transformations from validated provider facts to research evidence."""

from statistics import mean

from ..models.flow import (
    BrokerBar,
    BrokerSummary,
    Breadth,
    ForeignFlow,
    ForeignPoint,
    Liquidity,
    LiquidityPoint,
)
from ..models.fundamentals import Fundamentals, Metric, MetricGroup, MetricPoint


def broker_evidence(report):
    if report is None:
        return BrokerSummary()
    buyers = sorted(report.top_buyers, key=lambda b: b.rank)
    sellers = sorted(report.top_sellers, key=lambda b: b.rank)
    bars, seen = [], set()
    for side, rows in (("buyer", buyers), ("seller", sellers)):
        for row in rows:
            if row.broker_code in seen:
                continue
            seen.add(row.broker_code)
            bars.append(
                BrokerBar(
                    broker_code=row.broker_code,
                    side=side,
                    rank=row.rank,
                    buy_idr=row.buy_idr,
                    sell_idr=row.sell_idr,
                    net_idr=row.net_idr,
                    foreign_net_idr=row.foreign_net_idr,
                )
            )
    breadth = []
    for n in (3, 5, 10):
        buy = sum(b.net_idr for b in buyers[:n])
        sell = sum(b.net_idr for b in sellers[:n])
        denominator = abs(buy) + abs(sell)
        breadth.append(
            Breadth(
                top_n=n,
                buyer_net_idr=buy,
                seller_net_idr=sell,
                balance_idr=buy + sell,
                balance_ratio=(buy + sell) / denominator if denominator else None,
                buyer_count=len(buyers[:n]),
                seller_count=len(sellers[:n]),
            )
        )
    return BrokerSummary(brokers=bars, breadth=breadth)


def foreign_evidence(rows):
    rows = sorted(rows, key=lambda r: r.date)
    if not rows:
        return ForeignFlow()
    total, series = 0, []
    for row in rows:
        total += row.net_foreign_inflow
        series.append(
            ForeignPoint(
                date=row.date,
                net_inflow_idr=row.net_foreign_inflow,
                cumulative_net_inflow_idr=total,
                foreign_share_percent=row.foreign_share * 100,
            )
        )
    return ForeignFlow(
        net_inflow_idr=total,
        buy_idr=sum(r.foreign_buy_idr for r in rows),
        sell_idr=sum(r.foreign_sell_idr for r in rows),
        average_foreign_share_percent=mean(r.foreign_share for r in rows) * 100,
        positive_days=sum(r.net_foreign_inflow > 0 for r in rows),
        negative_days=sum(r.net_foreign_inflow < 0 for r in rows),
        series=series,
    )


def liquidity_evidence(history, selected_dates):
    history = sorted(history, key=lambda r: r.date)
    series = []
    for i, row in enumerate(history):
        if row.date not in selected_dates:
            continue
        prior = history[max(0, i - 20) : i]
        baseline = mean(r.volume for r in prior) if len(prior) == 20 else None
        ratio = row.volume / baseline if baseline is not None and baseline > 0 else None
        series.append(
            LiquidityPoint(
                date=row.date,
                close_idr=row.close,
                volume_shares=row.volume,
                average_volume_shares=baseline,
                volume_ratio=ratio,
                baseline_observations=len(prior),
            )
        )
    if not series:
        return Liquidity()
    last = series[-1]
    return Liquidity(
        latest_volume_shares=last.volume_shares,
        average_volume_shares=last.average_volume_shares,
        latest_vs_average_ratio=last.volume_ratio,
        series=series,
    )


def metric(key, label, unit, pairs, source="company_financials"):
    pairs = sorted(pairs, key=lambda p: p[0])
    series = [MetricPoint(period=str(p), value=v) for p, v in pairs]
    value = series[-1].value if series else None
    direction = "unknown"
    if len(series) >= 2 and value is not None and series[-2].value is not None:
        old = series[-2].value
        direction = "up" if value > old else "down" if value < old else "flat"
    return Metric(
        key=key,
        label=label,
        value=value,
        unit=unit,
        period=series[-1].period if series else None,
        availability="available" if value is not None else "unavailable",
        reason=(
            None if value is not None else "Latest comparable observation unavailable"
        ),
        direction=direction,
        series=series,
        source_keys=[source],
    )


def fundamentals_evidence(financials, valuation):
    rows = (
        sorted(financials.historical_financials, key=lambda r: r.year)
        if financials
        else []
    )
    ratios = (
        sorted(financials.historical_financial_ratio, key=lambda r: r.year)
        if financials
        else []
    )
    values = (
        sorted(valuation.historical_valuation, key=lambda r: r.year)
        if valuation
        else []
    )
    growth, earnings, cash, val = [], [], [], []
    for field in ("revenue", "earnings"):
        pairs = []
        for old, new in zip(rows, rows[1:]):
            a, b = getattr(old, field), getattr(new, field)
            change = (
                (b / a - 1) * 100
                if new.year == old.year + 1
                and a is not None
                and a > 0
                and b is not None
                else None
            )
            pairs.append((new.year, change))
        growth.append(
            metric(
                field + "_growth_yoy", field.title() + " growth YoY", "percent", pairs
            )
        )
    # The provider supplies these snapshots without an exact quarter label.
    for key in ("revenue", "earnings"):
        raw = getattr(financials, f"yoy_quarter_{key}_growth", None)
        growth.append(
            Metric(
                key=f"quarterly_{key}_growth_yoy",
                label=f"Latest quarterly {key} growth",
                value=raw * 100 if raw is not None else None,
                unit="percent",
                period=None,
                period_type="quarterly_yoy_undated",
                availability="available" if raw is not None else "unavailable",
                reason="Provider does not identify the quarter",
                source_keys=["company_financials"],
            )
        )
    for field in ("revenue", "earnings", "operating_pnl"):
        earnings.append(
            metric(
                field,
                field.replace("_", " ").title(),
                "idr",
                [(r.year, getattr(r, field)) for r in rows],
            )
        )
    for field in ("net_profit_margin", "operating_profit_margin", "roa", "roe"):
        pairs = []
        for row in ratios:
            raw = getattr(row.profitability, field, None)
            pairs.append((row.year, raw * 100 if raw is not None else None))
        earnings.append(
            metric(field, field.replace("_", " ").title(), "percent", pairs)
        )
    for field in ("operating_cash_flow", "free_cash_flow", "capital_expenditure"):
        cash.append(
            metric(
                field,
                field.replace("_", " ").title(),
                "idr",
                [(r.year, getattr(r, field)) for r in rows],
            )
        )
    cash.append(
        metric(
            "cash_conversion",
            "Operating cash flow / earnings",
            "ratio",
            [
                (
                    r.year,
                    (
                        r.operating_cash_flow / r.earnings
                        if r.earnings is not None
                        and r.earnings > 0
                        and r.operating_cash_flow is not None
                        else None
                    ),
                )
                for r in rows
            ],
        )
    )
    for field in ("pe", "pb", "ps", "pcf"):
        val.append(
            metric(
                field,
                field.upper(),
                "ratio",
                [(r.year, getattr(r, field)) for r in values],
                "company_valuation",
            )
        )
        if field != "pcf":
            val.append(
                metric(
                    field + "_peer_avg",
                    field.upper() + " peer average",
                    "ratio",
                    [(r.year, getattr(r, field + "_peer_avg")) for r in values],
                    "company_valuation",
                )
            )
    return Fundamentals(
        reporting_period=str(rows[-1].year) if rows else None,
        groups=[
            MetricGroup(key=key, label=label, metrics=metrics)
            for key, label, metrics in (
                ("growth", "Growth", growth),
                ("earnings", "Earnings", earnings),
                ("cash_flow", "Cash Flow", cash),
                ("valuation", "Valuation", val),
            )
        ],
    )
