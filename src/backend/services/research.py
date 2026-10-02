"""Public service facade preserving the research API across use cases."""

from .brokers import BrokerSeriesService
from .broker_flow import BrokerFlowService
from .intel_score import IntelScoreService
from .prices import PriceHistoryService
from .shareholders import ShareholderService


class ResearchService(
    IntelScoreService,
    PriceHistoryService,
    ShareholderService,
    BrokerSeriesService,
    BrokerFlowService,
):
    """Expose independent research use cases through the existing route contract."""
