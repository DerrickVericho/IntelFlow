"""Shared contract for errors that can cross the HTTP boundary."""


class AppError(Exception):
    """A typed application failure with an explicit public code and HTTP status.

    Subclasses define their own code and status. Only a safe message is returned
    to clients; provider payloads and internal details stay on the server.
    """

    code = "INTERNAL_ERROR"
    http_status = 500

    def __init__(self, message: str) -> None:
        self.message = message
        super().__init__(message)
