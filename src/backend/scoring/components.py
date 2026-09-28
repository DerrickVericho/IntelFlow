"""Pure calculations for individual flow and fundamental score components."""

from collections.abc import Mapping
from statistics import median

from ..models.flow import BrokerSummary, FlowEvidence
from ..models.fundamentals import Metric
from ..sectors.schemas.company_reports import CompanyFinancialsDetail
from .utils import average, clamp

MetricMap = Mapping[str, Metric]


# Flow value
def liquidity_value(flow: FlowEvidence) -> float | None:
    daily_scores = [
        clamp(100 * point.close_idr * point.volume_shares / 5_000_000_000)
        for point in flow.liquidity.series
        if point.close_idr > 0 and point.volume_shares >= 0
    ]
    return average(daily_scores)


def _balance_direction(ratio: float, saturation: float = 0.25) -> float:
    if ratio >= saturation:
        return 100.0
    if ratio <= -saturation:
        return 0.0
    return 50 + 50 * ratio / saturation


def foreign_flow_value(flow: FlowEvidence) -> float | None:
    foreign = flow.foreign_flow
    balance = flow.foreign_broker_balance
    if not foreign.series or balance is None or balance.balance_ratio is None:
        return None
    shares = [
        p.foreign_share_percent
        for p in foreign.series
        if p.foreign_share_percent is not None
    ]
    if not shares:
        return None
    participation = min(max(sum(shares) / len(shares) / 40, 0), 1)
    direction = _balance_direction(balance.balance_ratio)
    return round((1 - participation) * 50 + participation * direction, 2)


def broker_flow_value(flow: FlowEvidence) -> float | None:
    short = flow.broker_summary_5d
    if short is None or len(short.daily) < 4:
        return None
    short_value = _broker_window_value(short)
    long_value = _broker_window_value(flow.broker_summary)
    if short_value is None or long_value is None:
        return None
    return round(0.65 * short_value + 0.35 * long_value, 2)


def _broker_window_value(summary: BrokerSummary) -> float | None:
    if not summary.daily:
        return None
    slices = {b.top_n: b for b in summary.breadth}
    if any(
        n not in slices
        or slices[n].balance_ratio is None
        or slices[n].buyer_count < n
        or slices[n].seller_count < n
        for n in (3, 5)
    ):
        return None
    total = sum(p.total_buy_idr for p in summary.daily)
    if total <= 0:
        return None
    scores = []
    for n, target in ((3, 0.05), (5, 0.08)):
        net = [
            (
                p.top3_net_idr + p.top3_seller_net_idr
                if n == 3
                else p.top5_net_idr + p.top5_seller_net_idr
            )
            for p in summary.daily
        ]
        direction = _balance_direction(slices[n].balance_ratio, saturation=0.20)
        positive = sum(value > 0 for value in net)
        negative = sum(value < 0 for value in net)
        consistency = (
            100 * positive / (positive + negative) if positive + negative else 50.0
        )
        period_balance = sum(net)
        strength = min(abs(period_balance) / total / target, 1)
        concentration = 50 + 50 * strength if period_balance > 0 else 50 - 50 * strength
        scores.append(0.5 * direction + 0.3 * consistency + 0.2 * concentration)
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
    years = sorted(
        {
            int(point.period)
            for key in ("operating_cash_flow", "free_cash_flow", "cash_conversion")
            for point in metrics[key].series
        },
        reverse=True,
    )[:3]
    scores: list[float] = []
    for key in ("operating_cash_flow", "free_cash_flow", "cash_conversion"):
        observations = {int(point.period): point.value for point in metrics[key].series}
        for year in years:
            value = observations.get(year)
            if value is None:
                continue
            scores.append(
                clamp(50 * value) if key == "cash_conversion" else _level_value(value)
            )
    return average(scores)


def valuation_value(
    metrics: MetricMap,
    financials: CompanyFinancialsDetail | None,
) -> float | None:
    statements = (
        sorted(financials.historical_financials, key=lambda row: row.year)
        if financials
        else []
    )
    valuation_years = sorted(
        {
            int(point.period)
            for key in ("pe", "pb", "ps", "pcf")
            for point in metrics[key].series
        },
        reverse=True,
    )[:3]
    scores: list[float] = []

    for key, denominator_name in (
        ("pe", "earnings"),
        ("pb", "total_equity"),
        ("ps", "revenue"),
        ("pcf", "operating_cash_flow"),
    ):
        observations = sorted(metrics[key].series, key=lambda point: int(point.period))
        for point in observations:
            year = int(point.period)
            if year not in valuation_years or point.value is None or point.value <= 0:
                continue
            statement = next(
                (row for row in reversed(statements) if row.year <= year), None
            )
            denominator = getattr(statement, denominator_name, None)
            if (
                statement is None
                or year - statement.year > 1
                or denominator is None
                or denominator <= 0
            ):
                continue
            past = [
                earlier.value
                for earlier in observations
                if int(earlier.period) < year
                and earlier.value is not None
                and earlier.value > 0
            ]
            if len(past) < 2:
                continue
            historical_median = median(past)
            scores.append(
                clamp(100 * historical_median / (historical_median + point.value))
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
