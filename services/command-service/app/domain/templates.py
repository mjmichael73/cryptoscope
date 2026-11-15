"""Static catalog of alert rule templates.

A template is a preset for a common pattern (for example "alert if BTC drops
5% in 1 hour"). The API exposes the catalog so clients can present ready-made
choices; creating a rule from a template is still an ordinary create command,
so idempotency and validation apply unchanged.

Templates whose comparator is a price level (above/below/crossing) leave the
threshold to the user; pattern templates pin their threshold and window.
"""

from __future__ import annotations

from typing import Any

ALERT_TEMPLATES: list[dict[str, Any]] = [
    {
        "id": "price-above",
        "name": "Price above level",
        "description": "Alert when the price rises above a level you set.",
        "comparator": "above",
        "threshold": None,
        "window_seconds": None,
        "interval": "1m",
        "cooldown_seconds": 300,
    },
    {
        "id": "price-below",
        "name": "Price below level",
        "description": "Alert when the price falls below a level you set.",
        "comparator": "below",
        "threshold": None,
        "window_seconds": None,
        "interval": "1m",
        "cooldown_seconds": 300,
    },
    {
        "id": "crosses-above",
        "name": "Price crosses above level",
        "description": "Alert once when the price crosses above a level from below.",
        "comparator": "crosses_above",
        "threshold": None,
        "window_seconds": None,
        "interval": "1m",
        "cooldown_seconds": 300,
    },
    {
        "id": "crosses-below",
        "name": "Price crosses below level",
        "description": "Alert once when the price crosses below a level from above.",
        "comparator": "crosses_below",
        "threshold": None,
        "window_seconds": None,
        "interval": "1m",
        "cooldown_seconds": 300,
    },
    {
        "id": "big-rally-1h",
        "name": "Big rally in 1 hour",
        "description": "Alert when the price gains 5% or more within an hour.",
        "comparator": "pct_change_above",
        "threshold": 5.0,
        "window_seconds": 3600,
        "interval": "1m",
        "cooldown_seconds": 900,
    },
    {
        "id": "big-drop-1h",
        "name": "Big drop in 1 hour",
        "description": "Alert when the price loses 5% or more within an hour.",
        "comparator": "pct_change_below",
        "threshold": 5.0,
        "window_seconds": 3600,
        "interval": "1m",
        "cooldown_seconds": 900,
    },
    {
        "id": "rsi-overbought-1h",
        "name": "RSI overbought (1h)",
        "description": "Alert when the 1h RSI(14) goes above 70.",
        "comparator": "rsi_above",
        "threshold": 70.0,
        "window_seconds": None,
        "interval": "1h",
        "cooldown_seconds": 900,
    },
    {
        "id": "rsi-oversold-1h",
        "name": "RSI oversold (1h)",
        "description": "Alert when the 1h RSI(14) drops below 30.",
        "comparator": "rsi_below",
        "threshold": 30.0,
        "window_seconds": None,
        "interval": "1h",
        "cooldown_seconds": 900,
    },
]
