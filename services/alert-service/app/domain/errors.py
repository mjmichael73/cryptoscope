from __future__ import annotations


class AlertServiceError(Exception):
    pass


class RuleNotFoundError(AlertServiceError):
    pass


class EvaluationError(AlertServiceError):
    pass
