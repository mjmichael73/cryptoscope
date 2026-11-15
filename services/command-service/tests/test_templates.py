"""Tests for the static alert-rule template catalog."""

from __future__ import annotations

from cryptoscope_shared.comparators import ALLOWED_INTERVALS, Comparator, validate_rule_params

from app.domain.templates import ALERT_TEMPLATES

_PRICE_LEVEL_COMPARATORS = {"above", "below", "crosses_above", "crosses_below"}


def test_catalog_covers_every_comparator() -> None:
    comparators = {t["comparator"] for t in ALERT_TEMPLATES}
    assert comparators == {c.value for c in Comparator}


def test_each_template_is_valid_and_complete() -> None:
    ids = set()
    for template in ALERT_TEMPLATES:
        assert template["id"]
        ids.add(template["id"])
        assert template["name"]
        assert template["description"]
        validate_rule_params(template["comparator"], template["window_seconds"])
        assert template["interval"] in ALLOWED_INTERVALS
        assert template["cooldown_seconds"] > 0
    assert len(ids) == len(ALERT_TEMPLATES), "template ids must be unique"


def test_big_drop_template_matches_roadmap_example() -> None:
    drop = next(t for t in ALERT_TEMPLATES if t["id"] == "big-drop-1h")
    assert drop["comparator"] == "pct_change_below"
    assert drop["threshold"] == 5.0
    assert drop["window_seconds"] == 3600


def test_price_level_templates_require_user_threshold() -> None:
    for template in ALERT_TEMPLATES:
        if template["comparator"] in _PRICE_LEVEL_COMPARATORS:
            assert template["threshold"] is None, (
                f"{template['id']} must let the user pick the level"
            )


def test_pct_change_templates_have_fixed_threshold_and_window() -> None:
    for template in ALERT_TEMPLATES:
        if template["comparator"].startswith("pct_change"):
            assert template["threshold"] is not None
            assert template["window_seconds"] is not None
