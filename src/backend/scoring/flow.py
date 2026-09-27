"""Flow Score assembly from normalized flow evidence."""

from ..models.flow import FlowEvidence
from ..models.scoring import Component, Score
from .components import broker_flow_value, foreign_flow_value, liquidity_value
from .utils import weighted

MIN_PARTIAL_OBSERVATIONS = 16
FULL_WINDOW_OBSERVATIONS = 20


def calculate_flow_score(flow: FlowEvidence) -> Score:
    components = [
        Component(
            key="liquidity",
            value=liquidity_value(flow),
            weight=30,
            reason="Need 20 prior observations with positive mean volume",
            source_keys=["daily"],
        ),
        Component(
            key="foreign_flow",
            value=foreign_flow_value(flow),
            weight=30,
            reason="Need positive foreign turnover",
            source_keys=["foreign_flow"],
        ),
        Component(
            key="broker_flow",
            value=broker_flow_value(flow),
            weight=40,
            reason="Need at least 3 buyers and 3 sellers",
            source_keys=["broker_top"],
        ),
    ]

    for component in components:
        if component.value is not None:
            component.reason = None

    score = weighted(components, require_all=True)
    foreign_dates = {point.date for point in flow.foreign_flow.series}
    baseline_dates = {
        point.date for point in flow.liquidity.series if point.volume_ratio is not None
    }
    if (
        flow.window != "20d"
        or flow.trading_days < FULL_WINDOW_OBSERVATIONS
        or len(foreign_dates) < MIN_PARTIAL_OBSERVATIONS
        or len(baseline_dates) < MIN_PARTIAL_OBSERVATIONS
    ):
        score.value = None
        score.reason = (
            "Flow Score needs 20 trading observations and at least 16 dated "
            "foreign-flow and volume-baseline observations."
        )
    elif score.value is not None and (
        len(foreign_dates) < FULL_WINDOW_OBSERVATIONS
        or len(baseline_dates) < FULL_WINDOW_OBSERVATIONS
    ):
        score.reason = (
            f"Partial coverage: foreign flow {len(foreign_dates)} of 20 dates; "
            f"volume baseline {len(baseline_dates)} of 20 dates. "
            "The score uses available observations."
        )
    return score
