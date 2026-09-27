"""Top-level deterministic IntelScore calculation."""

from datetime import UTC, datetime

from ..models.flow import FlowEvidence
from ..models.fundamentals import Fundamentals
from ..models.scoring import Component, Scores
from ..sectors.schemas.company_reports import CompanyFinancialsDetail
from .flow import calculate_flow_score
from .fundamentals import calculate_fundamental_score
from .utils import weighted

VERSION = "draft-v0.4"


def calculate(
    flow: FlowEvidence,
    fundamentals: Fundamentals,
    *,
    financials: CompanyFinancialsDetail | None = None,
    calculated_at: datetime | None = None,
) -> Scores:
    """Combine independently calculated Flow and Fundamental scores."""

    flow_score = calculate_flow_score(flow)
    fundamental_score = calculate_fundamental_score(fundamentals, financials)
    combined_score = weighted(
        [
            Component(key="flow", value=flow_score.value, weight=60),
            Component(
                key="fundamental",
                value=fundamental_score.value,
                weight=40,
            ),
        ],
        require_all=True,
    )

    research_state = "Insufficient evidence"
    if flow_score.value is not None and fundamental_score.value is not None:
        states = {
            (True, True): "Accumulation with fundamental support",
            (True, False): "Flow without fundamental confirmation",
            (False, True): "Fundamentally supported, flow unconfirmed",
            (False, False): "Weak or mixed evidence",
        }
        research_state = states[(flow_score.value >= 60, fundamental_score.value >= 60)]

    metrics = {
        metric.key: metric for group in fundamentals.groups for metric in group.metrics
    }

    return Scores(
        flow=flow_score,
        fundamental=fundamental_score,
        combined=combined_score,
        calculation_version=VERSION,
        calculated_at=calculated_at or datetime.now(UTC),
        input_periods={
            "flow_start": str(flow.effective_start) if flow.effective_start else None,
            "flow_end": str(flow.effective_end) if flow.effective_end else None,
            "financial_year": fundamentals.reporting_period,
            "valuation_year": metrics["pe"].period,
        },
        research_state=research_state,
    )
