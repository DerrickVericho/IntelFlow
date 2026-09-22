"""Deterministic draft-v0.2 scoring. Exact rules are in docs/SCORING.md."""

from datetime import UTC, datetime
from statistics import mean, median
from ..domain.models.scoring import Component, Score, Scores

VERSION = "draft-v0.2"


def clamp(value):
    return round(max(0.0, min(100.0, value)), 2)


def average(values):
    present = [v for v in values if v is not None]
    return clamp(mean(present)) if present else None


def weighted(components, require_all=False):
    available = [c for c in components if c.value is not None]
    value = None
    if available and (not require_all or len(available) == len(components)):
        value = clamp(
            sum(c.value * c.weight for c in available)
            / sum(c.weight for c in available)
        )
    return Score(
        value=value,
        components=components,
        reason=(
            None
            if len(available) == len(components)
            else "Unavailable components; see component reasons"
        ),
    )


def calculate(flow, fundamentals, *, financials=None, calculated_at=None):
    ratios = [
        p.volume_ratio for p in flow.liquidity.series if p.volume_ratio is not None
    ]
    liquidity = average([clamp(50 * r) for r in ratios])
    f = flow.foreign_flow
    foreign = None
    if (
        f.buy_idr is not None
        and f.sell_idr is not None
        and f.buy_idr + f.sell_idr > 0
        and f.series
    ):
        pressure = clamp(50 + 50 * f.net_inflow_idr / (f.buy_idr + f.sell_idr))
        positive = 100 * f.positive_days / len(f.series)
        foreign = clamp(0.7 * pressure + 0.3 * positive)
    broker = average(
        [
            clamp(50 + 50 * b.balance_ratio)
            for b in flow.broker_summary.breadth
            if b.balance_ratio is not None
            and b.buyer_count >= b.top_n
            and b.seller_count >= b.top_n
        ]
    )
    flow_score = weighted(
        [
            Component(
                key=k,
                value=v,
                weight=w,
                reason=None if v is not None else reason,
                source_keys=[source],
            )
            for k, v, w, reason, source in (
                (
                    "liquidity",
                    liquidity,
                    30,
                    "Need 20 prior observations with positive mean volume",
                    "daily",
                ),
                (
                    "foreign_flow",
                    foreign,
                    30,
                    "Need positive foreign turnover",
                    "foreign_flow",
                ),
                (
                    "broker_flow",
                    broker,
                    40,
                    "Need at least 3 buyers and 3 sellers",
                    "broker_top",
                ),
            )
        ],
        require_all=True,
    )
    metrics = {m.key: m for g in fundamentals.groups for m in g.metrics}

    def current(key):
        return metrics[key].value

    growth = average(
        [
            clamp(50 + current(k)) if current(k) is not None else None
            for k in ("revenue_growth_yoy", "earnings_growth_yoy")
        ]
    )
    # Positive level and relative annual trend contribute equally.
    earnings_values = []
    for key in (
        "earnings",
        "net_profit_margin",
        "operating_profit_margin",
        "roa",
        "roe",
    ):
        m = metrics[key]
        if m.value is None:
            continue
        level = 100 if m.value > 0 else 50 if m.value == 0 else 0
        trend = None
        if (
            len(m.series) > 1
            and m.series[-2].value not in (None, 0)
            and int(m.series[-1].period) - int(m.series[-2].period) == 1
        ):
            old = m.series[-2].value
            trend = clamp(50 + 50 * (m.value - old) / abs(old))
        earnings_values.append(average([level, trend]))
    earnings = average(earnings_values)
    cash_values = [
        100 if current(k) > 0 else 50 if current(k) == 0 else 0
        for k in ("operating_cash_flow", "free_cash_flow")
        if current(k) is not None
    ]
    if current("cash_conversion") is not None:
        cash_values.append(clamp(50 * current("cash_conversion")))
    cash = average(cash_values)
    valuation_values = []
    latest = (
        max(financials.historical_financials, key=lambda r: r.year, default=None)
        if financials
        else None
    )
    for key, denominator in (
        ("pe", "earnings"),
        ("pb", "total_equity"),
        ("ps", "revenue"),
        ("pcf", "operating_cash_flow"),
    ):
        m = metrics[key]
        valid_denominator = getattr(latest, denominator, None)
        past = [p.value for p in m.series[:-1] if p.value is not None and p.value > 0]
        if (
            m.value is not None
            and m.value > 0
            and valid_denominator is not None
            and valid_denominator > 0
            and len(past) >= 2
        ):
            # Annual statements may lag the dated valuation by one year. Older
            # or future denominators are not sufficient to validate the ratio.
            if 0 <= int(m.period) - latest.year <= 1:
                valuation_values.append(
                    clamp(50 + 50 * (median(past) - m.value) / median(past))
                )
    valuation = average(valuation_values)
    fundamental_score = weighted(
        [
            Component(
                key=k,
                value=v,
                weight=w,
                reason=(
                    None
                    if v is not None
                    else "Insufficient comparable metrics or meaningful denominators"
                ),
                source_keys=[
                    "company_valuation" if k == "valuation" else "company_financials"
                ],
            )
            for k, v, w in (
                ("growth", growth, 30),
                ("earnings", earnings, 25),
                ("cash_flow", cash, 25),
                ("valuation", valuation, 20),
            )
        ]
    )
    # A single component is not a meaningful cross-factor fundamental score.
    if sum(c.value is not None for c in fundamental_score.components) < 2:
        fundamental_score.value = None
        fundamental_score.reason = "Need at least two fundamental components"
    for group, component in zip(fundamentals.groups, fundamental_score.components):
        group.score = component.value
    combined = weighted(
        [
            Component(key="flow", value=flow_score.value, weight=60),
            Component(key="fundamental", value=fundamental_score.value, weight=40),
        ],
        require_all=True,
    )
    state = "Insufficient evidence"
    if flow_score.value is not None and fundamental_score.value is not None:
        states = {
            (True, True): "Accumulation with fundamental support",
            (True, False): "Flow without fundamental confirmation",
            (False, True): "Fundamentally supported, flow unconfirmed",
            (False, False): "Weak or mixed evidence",
        }
        state = states[(flow_score.value >= 60, fundamental_score.value >= 60)]
    return Scores(
        flow=flow_score,
        fundamental=fundamental_score,
        combined=combined,
        calculation_version=VERSION,
        calculated_at=calculated_at or datetime.now(UTC),
        input_periods={
            "flow_start": str(flow.effective_start) if flow.effective_start else None,
            "flow_end": str(flow.effective_end) if flow.effective_end else None,
            "financial_year": fundamentals.reporting_period,
            "valuation_year": metrics["pe"].period,
        },
        research_state=state,
    )
