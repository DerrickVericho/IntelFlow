"""Public interface for the Sectors integration."""

from .client import SectorsClient
from .gateway import SectorsGateway
from ..exceptions.sectors import SectorsError

__all__ = ["SectorsClient", "SectorsError", "SectorsGateway"]
