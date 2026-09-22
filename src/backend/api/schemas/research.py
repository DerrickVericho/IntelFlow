"""Aggregate response schema for the comprehensive IntelScore page."""

from ...domain.models.fundamentals import Fundamentals
from ...domain.models.research import Company, KeyPoint
from ...domain.models.scoring import Scores
from .flow import FlowResponse


class ResearchResponse(FlowResponse):
    company: Company
    scores: Scores
    key_points: list[KeyPoint]
    fundamentals: Fundamentals
