"""Read-side errors."""

from __future__ import annotations


class ValidationError(ValueError):
    """Raised when a query carries invalid parameters."""
