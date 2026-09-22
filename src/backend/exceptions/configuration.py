"""Environment and process configuration failures."""


class ApplicationConfigurationError(RuntimeError):
    """Raised when backend environment configuration is invalid."""
