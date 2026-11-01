from pydantic import Field

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


def test_secret_file_overrides_environment_value(tmp_path, monkeypatch):
    class DatabaseSettings(BaseServiceSettings):
        postgres_dsn: str = Field(default="", alias="TEST_POSTGRES_DSN")

    secret_file = tmp_path / "postgres-dsn"
    secret_file.write_text("postgresql://svc:secret@db/app\n", encoding="utf-8")
    monkeypatch.setenv("TEST_POSTGRES_DSN", "postgresql://ignored@db/app")
    monkeypatch.setenv("TEST_POSTGRES_DSN_FILE", str(secret_file))

    assert DatabaseSettings().postgres_dsn == "postgresql://svc:secret@db/app"


def test_secret_file_read_errors_fail_closed(tmp_path, monkeypatch):
    class DatabaseSettings(BaseServiceSettings):
        postgres_dsn: str = Field(default="fallback", alias="TEST_POSTGRES_DSN")

    monkeypatch.setenv("TEST_POSTGRES_DSN_FILE", str(tmp_path / "missing"))

    try:
        DatabaseSettings()
    except ValueError as exc:
        assert "could not read secret file" in str(exc)
    else:
        raise AssertionError("invalid secret file should fail settings initialization")


def test_database_secrets_require_files_in_production(monkeypatch):
    class DatabaseSettings(BaseServiceSettings):
        postgres_dsn: str = Field(default="", alias="POSTGRES_DSN")

    monkeypatch.setenv("CRYPTOSCOPE_ENV", "production")
    monkeypatch.setenv("POSTGRES_DSN", "postgresql://inline-secret@db/app")
    monkeypatch.delenv("POSTGRES_DSN_FILE", raising=False)

    try:
        DatabaseSettings()
    except ValueError as exc:
        assert "POSTGRES_DSN_FILE is required in production" in str(exc)
    else:
        raise AssertionError("production settings should require a mounted secret")
