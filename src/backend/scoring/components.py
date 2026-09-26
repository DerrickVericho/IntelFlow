"""Pure calculations for individual flow and fundamental score components."""

from collections.abc import Mapping
from statistics import median

from ..models.flow import FlowEvidence
from ..models.fundamentals import Metric
from ..sectors.schemas.company_reports import CompanyFinancialsDetail
from .utils import average, clamp

MetricMap = Mapping[str, Metric]

# Flow value
def liquidity_value(flow: FlowEvidence) -> float | None:
    ratios = [
        point.volume_ratio
        for point in flow.liquidity.series
        if point.volume_ratio is not None
    ]
    return average([clamp(50 * ratio) for ratio in ratios])


def foreign_flow_value(flow: FlowEvidence) -> float | None:
    foreign = flow.foreign_flow
    has_turnover = (
        foreign.buy_idr is not None
        and foreign.sell_idr is not None
        and foreign.net_inflow_idr is not None
        and foreign.buy_idr + foreign.sell_idr > 0
        and bool(foreign.series)
    )
    if not has_turnover:
        return None

    turnover = foreign.buy_idr + foreign.sell_idr
    pressure = clamp(50 + 50 * foreign.net_inflow_idr / turnover)
    positive_days = 100 * foreign.positive_days / len(foreign.series)

    return clamp(0.7 * pressure + 0.3 * positive_days)


def broker_flow_value(flow: FlowEvidence) -> float | None:
    scores = [
        clamp(50 + 50 * breadth.balance_ratio)
        for breadth in flow.broker_summary.breadth
        if breadth.balance_ratio is not None
        and breadth.buyer_count >= breadth.top_n
        and breadth.seller_count >= breadth.top_n
    ]
    return average(scores)


# Fundamental value
def growth_value(metrics: MetricMap) -> float | None:
    scores: list[float | None] = []
    for key in ("revenue_growth_yoy", "earnings_growth_yoy"):
        value = metrics[key].value
        scores.append(clamp(50 + value) if value is not None else None)

    return average(scores)


def earnings_value(metrics: MetricMap) -> float | None:
    scores: list[float | None] = []

    for key in (
        "earnings",
        "net_profit_margin",
        "operating_profit_margin",
        "roa",
        "roe",
    ):
        metric = metrics[key]
        if metric.value is None:
            continue

        level = _level_value(metric.value)
        trend = _annual_trend_value(metric)
        scores.append(average([level, trend]))

    return average(scores)


def cash_flow_value(metrics: MetricMap) -> float | None:
    scores = [
        _level_value(metrics[key].value)
        for key in ("operating_cash_flow", "free_cash_flow")
        if metrics[key].value is not None
    ]

    conversion = metrics["cash_conversion"].value
    if conversion is not None:
        scores.append(clamp(50 * conversion))

    return average(scores)


def valuation_value(
    metrics: MetricMap,
    financials: CompanyFinancialsDetail | None,
) -> float | None:
    latest = (
        max(financials.historical_financials, key=lambda row: row.year, default=None)
        if financials
        else None
    )
    scores: list[float] = []

    for key, denominator_name in (
        ("pe", "earnings"),
        ("pb", "total_equity"),
        ("ps", "revenue"),
        ("pcf", "operating_cash_flow"),
    ):
        metric = metrics[key]
        denominator = getattr(latest, denominator_name, None)
        past = [
            point.value
            for point in metric.series[:-1]
            if point.value is not None and point.value > 0
        ]

        has_meaningful_ratio = (
            metric.value is not None
            and metric.value > 0
            and metric.period is not None
            and denominator is not None
            and denominator > 0
            and latest is not None
            and len(past) >= 2
        )
        if not has_meaningful_ratio:
            continue

        statement_lag = int(metric.period) - latest.year
        if not 0 <= statement_lag <= 1:
            continue

        historical_median = median(past)
        scores.append(
            clamp(50 + 50 * (historical_median - metric.value) / historical_median)
        )

    return average(scores)


def _level_value(value: float) -> float:
    if value > 0:
        return 100.0
    if value == 0:
        return 50.0
    return 0.0


def _annual_trend_value(metric: Metric) -> float | None:
    if len(metric.series) < 2:
        return None

    previous = metric.series[-2]
    current = metric.series[-1]
    if previous.value in (None, 0) or current.value is None:
        return None

    if int(current.period) - int(previous.period) != 1:
        return None

    return clamp(50 + 50 * (current.value - previous.value) / abs(previous.value))
