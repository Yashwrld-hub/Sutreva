from __future__ import annotations

from scripts.nebius_preflight import validate_config


def test_nebius_preflight_accepts_defaults(monkeypatch):
    for name in [
        "SUTREVA_MODEL_PROVIDER",
        "NEBIUS_MODEL_NAME",
        "NEBIUS_API_BASE_URL",
        "NEBIUS_REQUEST_TIMEOUT_S",
    ]:
        monkeypatch.delenv(name, raising=False)
    assert validate_config() == []


def test_nebius_preflight_rejects_insecure_url(monkeypatch):
    monkeypatch.setenv("NEBIUS_API_BASE_URL", "http://example.com/v1/")
    errors = validate_config()
    assert any("HTTPS" in error for error in errors)
