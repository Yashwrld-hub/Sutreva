"""Runtime configuration for Sutreva deployments.

Keeps deployment-facing configuration in one place while preserving the
existing provider defaults for local development.
"""
from __future__ import annotations

import os
from dataclasses import dataclass

DEFAULT_PROVIDER = "nebius_nemotron"
DEFAULT_MODEL = "nvidia/NVIDIA-Nemotron-3-Nano-30B-A3B"
DEFAULT_BASE_URL = "https://api.tokenfactory.nebius.com/v1/"
DEFAULT_TIMEOUT_S = 90


def _env(name: str, default: str) -> str:
    value = os.environ.get(name)
    return value.strip() if value and value.strip() else default


@dataclass(frozen=True)
class SutrevaRuntimeConfig:
    environment: str = "development"
    provider: str = DEFAULT_PROVIDER
    model_name: str = DEFAULT_MODEL
    base_url: str = DEFAULT_BASE_URL
    timeout_s: float = DEFAULT_TIMEOUT_S


def get_runtime_config() -> SutrevaRuntimeConfig:
    environment = _env("SUTREVA_ENV", "development").lower()
    provider = _env("SUTREVA_MODEL_PROVIDER", DEFAULT_PROVIDER).lower()
    model_name = _env("NEBIUS_MODEL_NAME", DEFAULT_MODEL)
    base_url = _env("NEBIUS_API_BASE_URL", DEFAULT_BASE_URL)
    try:
        timeout_s = float(_env("NEBIUS_REQUEST_TIMEOUT_S", str(DEFAULT_TIMEOUT_S)))
    except ValueError:
        timeout_s = float(DEFAULT_TIMEOUT_S)
    return SutrevaRuntimeConfig(
        environment=environment,
        provider=provider,
        model_name=model_name,
        base_url=base_url,
        timeout_s=timeout_s,
    )


def runtime_summary() -> dict[str, str]:
    cfg = get_runtime_config()
    return {
        "environment": cfg.environment,
        "provider": cfg.provider,
        "model": cfg.model_name,
        "base_url": cfg.base_url,
    }
