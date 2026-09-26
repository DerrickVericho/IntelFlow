"""Flow Score assembly from normalized flow evidence."""

from ..models.flow import FlowEvidence
from ..models.scoring import Component, Score
from .components import broker_flow_value, foreign_flow_value, liquidity_value
from .utils import weighted


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

    return weighted(components, require_all=True)
