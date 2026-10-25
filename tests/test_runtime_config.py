from __future__ import annotations

from runtime_config import DEFAULT_BASE_URL, DEFAULT_MODEL, DEFAULT_PROVIDER, get_runtime_config


def test_runtime_defaults(monkeypatch):
    for name in [
        "SUTREVA_ENV",
        "SUTREVA_MODEL_PROVIDER",
        "NEBIUS_MODEL_NAME",
        "NEBIUS_API_BASE_URL",
        "NEBIUS_REQUEST_TIMEOUT_S",
    ]:
        monkeypatch.delenv(name, raising=False)

    cfg = get_runtime_config()
    assert cfg.environment == "development"
    assert cfg.provider == DEFAULT_PROVIDER
    assert cfg.model_name == DEFAULT_MODEL
    assert cfg.base_url == DEFAULT_BASE_URL
    assert cfg.timeout_s == 90


def test_runtime_environment_overrides(monkeypatch):
    monkeypatch.setenv("SUTREVA_ENV", "production")
    monkeypatch.setenv("SUTREVA_MODEL_PROVIDER", "nebius")
    monkeypatch.setenv("NEBIUS_MODEL_NAME", "nvidia/custom-model")
    monkeypatch.setenv("NEBIUS_API_BASE_URL", "https://example.nebius/v1/")
    monkeypatch.setenv("NEBIUS_REQUEST_TIMEOUT_S", "45")

    cfg = get_runtime_config()
    assert cfg.environment == "production"
    assert cfg.provider == "nebius"
    assert cfg.model_name == "nvidia/custom-model"
    assert cfg.base_url == "https://example.nebius/v1/"
    assert cfg.timeout_s == 45
