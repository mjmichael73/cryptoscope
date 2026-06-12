"""Domain level errors mapped to transport errors at the edges."""

from __future__ import annotations


class ConflictError(RuntimeError):
    """Raised when a uniqueness rule would be violated."""


class ValidationError(ValueError):
    """Raised when a command carries invalid input."""
