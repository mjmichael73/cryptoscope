from cryptoscope_shared.events import (
    ALERT_RULE_DELETED,
    WATCHLIST_CREATED,
    WATCHLIST_DELETED,
    WATCHLIST_UPDATED,
)


def test_new_event_type_constants():
    assert WATCHLIST_UPDATED == "watchlist_updated"
    assert WATCHLIST_DELETED == "watchlist_deleted"
    assert ALERT_RULE_DELETED == "alert_rule_deleted"
    assert WATCHLIST_CREATED == "watchlist_created"  # existing, unchanged
