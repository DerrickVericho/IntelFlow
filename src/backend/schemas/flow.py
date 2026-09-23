"""Response schema for window-specific flow evidence."""

from ..models.flow import FlowEvidence
from .common import Envelope


class FlowResponse(Envelope):
    flow: FlowEvidence
