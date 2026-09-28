class DomainError(Exception):
    """Base class for service errors that map to HTTP responses."""

    status_code = 400

    def __init__(self, detail: str) -> None:
        super().__init__(detail)
        self.detail = detail


class NotFoundError(DomainError):
    status_code = 404


class ConflictError(DomainError):
    """The request is valid but conflicts with the current state."""

    status_code = 409


class InvalidReferenceError(DomainError):
    """A referenced record does not exist or is not visible to the user."""

    status_code = 422
