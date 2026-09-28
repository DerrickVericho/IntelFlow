"""Flow Score assembly from normalized flow evidence."""

from ..models.flow import FlowEvidence
from ..models.scoring import Component, Score
from .components import broker_flow_value, foreign_flow_value, liquidity_value
from .utils import weighted

MIN_PARTIAL_OBSERVATIONS = 16
FULL_WINDOW_OBSERVATIONS = 20
MIN_SHORT_OBSERVATIONS = 4
FULL_SHORT_OBSERVATIONS = 5


def calculate_flow_score(flow: FlowEvidence) -> Score:
    components = [
        Component(
            key="liquidity",
            value=liquidity_value(flow),
            weight=30,
            reason="Need dated closing price and nonnegative share volume",
            source_keys=["daily"],
        ),
        Component(
            key="foreign_flow",
            value=foreign_flow_value(flow),
            weight=30,
            reason="Need dated foreign participation and foreign-ranked broker buy/sell balance",
            source_keys=["foreign_flow", "broker_foreign_top"],
        ),
        Component(
            key="broker_flow",
            value=broker_flow_value(flow),
            weight=40,
            reason="Need independent 5-day and 20-day top 3/5 rankings with daily broker activity",
            source_keys=["broker_top_5d", "broker_top", "broker_activity"],
        ),
    ]

    for component in components:
        if component.value is not None:
            component.reason = None

    score = weighted(components, require_all=True)
    foreign_dates = {point.date for point in flow.foreign_flow.series}
    liquidity_dates = {
        point.date
        for point in flow.liquidity.series
        if point.close_idr > 0 and point.volume_shares >= 0
    }

    broker_dates = {point.date for point in flow.broker_summary.daily}
    short_broker_dates = (
        {point.date for point in flow.broker_summary_5d.daily}
        if flow.broker_summary_5d
        else set()
    )

    if (
        flow.window != "20d"
        or flow.trading_days < FULL_WINDOW_OBSERVATIONS
        or len(foreign_dates) < MIN_PARTIAL_OBSERVATIONS
        or len(liquidity_dates) < MIN_PARTIAL_OBSERVATIONS
        or len(broker_dates) < MIN_PARTIAL_OBSERVATIONS
        or len(short_broker_dates) < MIN_SHORT_OBSERVATIONS
    ):
        score.value = None
        score.reason = (
            "Flow Score needs 20 trading observations and at least 16 dated "
            "foreign-flow and liquidity observations, 16 daily-broker observations, "
            "and at least 4 recent broker observations."
        )
    elif score.value is not None and (
        len(foreign_dates) < FULL_WINDOW_OBSERVATIONS
        or len(liquidity_dates) < FULL_WINDOW_OBSERVATIONS
        or len(broker_dates) < FULL_WINDOW_OBSERVATIONS
        or len(short_broker_dates) < FULL_SHORT_OBSERVATIONS
    ):
        score.reason = (
            f"Partial coverage: foreign flow {len(foreign_dates)} of 20 dates; "
            f"liquidity {len(liquidity_dates)} of 20 dates; "
            f"daily broker activity {len(broker_dates)} of 20 dates. "
            f"Recent broker activity {len(short_broker_dates)} of 5 dates. "
            "The score uses available observations."
        )
    return score
