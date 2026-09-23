"""Aggregate response schema for the comprehensive IntelScore page."""

from ..models.fundamentals import Fundamentals
from ..models.research import Company, KeyPoint
from ..models.scoring import Scores
from .flow import FlowResponse


class ResearchResponse(FlowResponse):
    company: Company
    scores: Scores
    key_points: list[KeyPoint]
    fundamentals: Fundamentals
