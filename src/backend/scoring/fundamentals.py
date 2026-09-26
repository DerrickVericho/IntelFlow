"""Fundamental Score assembly from normalized company evidence."""

from ..models.fundamentals import Fundamentals, Metric
from ..models.scoring import Component, Score
from ..sectors.schemas.company_reports import CompanyFinancialsDetail
from .components import (
    cash_flow_value,
    earnings_value,
    growth_value,
    valuation_value,
)
from .utils import weighted


def calculate_fundamental_score(
    fundamentals: Fundamentals,
    financials: CompanyFinancialsDetail | None,
) -> Score:
    metrics: dict[str, Metric] = {
        metric.key: metric for group in fundamentals.groups for metric in group.metrics
    }
    unavailable_reason = "Insufficient comparable metrics or meaningful denominators"
    components = [
        Component(
            key="growth",
            value=growth_value(metrics),
            weight=30,
            reason=unavailable_reason,
            source_keys=["company_financials"],
        ),
        Component(
            key="earnings",
            value=earnings_value(metrics),
            weight=25,
            reason=unavailable_reason,
            source_keys=["company_financials"],
        ),
        Component(
            key="cash_flow",
            value=cash_flow_value(metrics),
            weight=25,
            reason=unavailable_reason,
            source_keys=["company_financials"],
        ),
        Component(
            key="valuation",
            value=valuation_value(metrics, financials),
            weight=20,
            reason=unavailable_reason,
            source_keys=["company_valuation"],
        ),
    ]

    for component in components:
        if component.value is not None:
            component.reason = None

    score = weighted(components)
    if sum(component.value is not None for component in components) < 2:
        score.value = None
        score.reason = "Need at least two fundamental components"

    scores_by_key = {component.key: component.value for component in components}
    for group in fundamentals.groups:
        group.score = scores_by_key.get(group.key)

    return score
