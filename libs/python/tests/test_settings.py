from cryptoscope_shared.settings import BaseServiceSettings


def test_kafka_broker_list_parsing(monkeypatch):
    monkeypatch.setenv("KAFKA_BROKERS", "a:9092, b:9092 ,")
    settings = BaseServiceSettings()
    assert settings.kafka_broker_list == ["a:9092", "b:9092"]


def test_defaults(monkeypatch):
    monkeypatch.delenv("CRYPTOSCOPE_ENV", raising=False)
    settings = BaseServiceSettings()
    assert settings.environment == "local"
    assert settings.log_level == "info"
