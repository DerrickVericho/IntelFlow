"""Public interface for the Sectors integration."""

from .client import SectorsClient
from .exceptions import SectorsError
from .gateway import SectorsGateway

__all__ = ["SectorsClient", "SectorsError", "SectorsGateway"]

