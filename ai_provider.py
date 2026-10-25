"""
ai_provider.py — Sutreva's model-provider boundary.

This module owns model-provider concerns only: provider selection, API-client
creation, retries, and model invocation. Engineering extraction, evidence,
and audit rules remain outside this module.
"""

from __future__ import annotations

import os
import time
from functools import lru_cache
from typing import Any, Protocol

from runtime_config import DEFAULT_BASE_URL, DEFAULT_MODEL, get_runtime_config

try:
    from openai import OpenAI
except ImportError:  # pragma: no cover - dependency is validated by deployment checks.
    OpenAI = None

DEFAULT_MODEL_NAME = DEFAULT_MODEL
NEBIUS_API_BASE_URL = DEFAULT_BASE_URL
# Legacy constants retained for compatibility with existing integrations.
API_BASE_URL = NEBIUS_API_BASE_URL
REQUEST_TIMEOUT_S = 90
MAX_PROVIDER_RETRIES = 1
MAX_RETRIES = MAX_PROVIDER_RETRIES


class ModelProvider(Protocol):
    """Minimal provider contract used by Sutreva's AI orchestration layer."""

    name: str

    def generate(self, prompt: str, model_name: str = DEFAULT_MODEL_NAME) -> str:
        """Generate a model response for the supplied prompt."""
        ...


class NebiusNemotronProvider:
    """Current production provider: Nemotron through Nebius' OpenAI API."""

    name = "nebius_nemotron"

    def __init__(
        self,
        *,
        api_key: str | None = None,
        base_url: str = NEBIUS_API_BASE_URL,
        timeout_s: float = REQUEST_TIMEOUT_S,
        client: Any | None = None,
    ) -> None:
        self._api_key = api_key
        runtime = get_runtime_config()
        self._base_url = base_url if base_url != NEBIUS_API_BASE_URL else runtime.base_url
        self._timeout_s = timeout_s if timeout_s != REQUEST_TIMEOUT_S else runtime.timeout_s
        self._client_override = client

    @property
    def client(self) -> Any:
        if self._client_override is not None:
            return self._client_override
        api_key = self._api_key or os.environ.get("NEBIUS_API_KEY")
        if not api_key:
            raise RuntimeError("NEBIUS_API_KEY not found. Check your .env file.")
        return _build_openai_client(api_key, self._base_url, self._timeout_s)

    def generate(self, prompt: str, model_name: str = DEFAULT_MODEL_NAME) -> str:
        """Call Nemotron using the existing request semantics with env-configured model support."""
        runtime_model = get_runtime_config().model_name
        selected_model = runtime_model if model_name == DEFAULT_MODEL_NAME else model_name
        last_error: Exception | None = None

        for attempt in range(MAX_PROVIDER_RETRIES + 1):
            try:
                response = self.client.chat.completions.create(
                    model=selected_model,
                    messages=[
                        {
                            "role": "system",
                            "content": (
                                "You are a precise technical data extraction engine. "
                                "You only output valid JSON."
                            ),
                        },
                        {"role": "user", "content": prompt},
                    ],
                    temperature=0,
                )
                message = response.choices[0].message
                raw_content = getattr(message, "content", None) or ""
                raw_reasoning = getattr(message, "reasoning_content", None) or ""
                # Prefer content if it contains JSON braces; otherwise fall back to reasoning_content
                if "{" in str(raw_content):
                    content = str(raw_content)
                elif "{" in str(raw_reasoning):
                    content = str(raw_reasoning)
                else:
                    content = str(raw_content or raw_reasoning)
                if not str(content).strip():
                    raise RuntimeError("Model returned an empty response.")
                return str(content)
            except Exception as exc:  # noqa: BLE001 - surface the provider failure after retry.
                last_error = exc
                if attempt < MAX_PROVIDER_RETRIES:
                    time.sleep(1.5)

        raise RuntimeError(
            f"Model call failed after {MAX_PROVIDER_RETRIES + 1} attempts: {last_error}"
        )


@lru_cache(maxsize=8)
def _build_openai_client(api_key: str, base_url: str, timeout_s: float) -> Any:
    """Cache OpenAI-compatible clients so connection pools are reused."""
    if OpenAI is None:
        raise RuntimeError(
            "The optional openai package is required for AI extraction. "
            "Install requirements.txt."
        )
    return OpenAI(base_url=base_url, api_key=api_key, timeout=timeout_s)


def build_model_provider(provider_name: str | None = None) -> ModelProvider:
    """Build a provider from an explicit name or the environment default."""
    runtime = get_runtime_config()
    selected = (provider_name or runtime.provider).strip().lower()
    if selected in {"nebius_nemotron", "nebius", "nemotron"}:
        return NebiusNemotronProvider()
    raise ValueError(f"Unsupported Sutreva model provider: {selected!r}")


@lru_cache(maxsize=1)
def get_model_provider() -> ModelProvider:
    """Return the configured provider for normal application use."""
    return build_model_provider()


def clear_model_provider_cache() -> None:
    """Clear the provider cache for tests or controlled runtime reconfiguration."""
    get_model_provider.cache_clear()
