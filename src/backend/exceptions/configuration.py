"""Environment and process configuration failures."""

from .base import AppError


class ApplicationConfigurationError(AppError):
    """Raised when backend environment configuration is invalid."""

    code = "CONFIGURATION_ERROR"
    http_status = 503
