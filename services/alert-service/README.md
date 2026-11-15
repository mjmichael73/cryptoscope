# Alert service

Python/FastAPI consumer that reads `domain.events`, evaluates active PostgreSQL alert rules on `candle_updated` events, persists trigger history, publishes alert events, and sends optional notifications.

The service shares `alert_rules` and `alert_triggers` with command-service migrations. Notification adapters currently support SMTP email, Slack incoming webhooks, Telegram bots, and a generic webhook. Rolling close history is process-local and is lost on restart.

HTTP routes are listed in [the API reference](../../docs/API.md). **Known blocker:** list/detail/acknowledge/clear routes do not consistently enforce tenant ownership. Read [the roadmap](../../docs/roadmap.md) before exposing this service or changing its authorization.

Run `make test-alert` and `make lint-python` from the repository root when validation is requested. Configuration is defined in `app/settings.py`.
