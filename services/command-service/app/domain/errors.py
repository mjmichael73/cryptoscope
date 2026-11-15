"""Domain level errors mapped to transport errors at the edges."""

from __future__ import annotations


class ConflictError(RuntimeError):
    """Raised when a uniqueness rule would be violated."""


class NotFoundError(RuntimeError):
    """Raised when a referenced resource does not exist for the tenant."""


class ValidationError(ValueError):
    """Raised when a command carries invalid input."""
