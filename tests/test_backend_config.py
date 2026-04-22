import pytest

pytest.importorskip("pydantic")
pytest.importorskip("pydantic_settings")

from backend.app.config import Settings


def test_settings_parse_allowed_origins_from_csv() -> None:
    settings = Settings(allowed_origins="http://localhost:3000, http://localhost:8501")
    assert settings.allowed_origins == ["http://localhost:3000", "http://localhost:8501"]


def test_settings_reject_placeholder_db_url_in_production() -> None:
    try:
        Settings(environment="production")
    except ValueError as exc:
        assert "placeholder credentials" in str(exc)
    else:
        raise AssertionError("production settings should reject placeholder credentials")
