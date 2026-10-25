"""Offline/live preflight for a Nebius-hosted Sutreva deployment."""
from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from runtime_config import get_runtime_config


def validate_config() -> list[str]:
    cfg = get_runtime_config()
    errors: list[str] = []
    if cfg.provider != "nebius_nemotron":
        errors.append(f"Unsupported deployment provider: {cfg.provider}")
    parsed = urlparse(cfg.base_url)
    if parsed.scheme != "https" or not parsed.netloc:
        errors.append(f"NEBIUS_API_BASE_URL must be an HTTPS URL: {cfg.base_url}")
    if not cfg.model_name:
        errors.append("NEBIUS_MODEL_NAME is empty")
    try:
        if cfg.timeout_s <= 0:
            errors.append("NEBIUS_REQUEST_TIMEOUT_S must be positive")
    except (TypeError, ValueError):
        errors.append("NEBIUS_REQUEST_TIMEOUT_S must be numeric")
    return errors


def live_check() -> tuple[bool, str]:
    from openai import OpenAI

    key = os.environ.get("NEBIUS_API_KEY", "").strip()
    if not key or key == "your-key-here":
        return False, "NEBIUS_API_KEY is missing"
    cfg = get_runtime_config()
    client = OpenAI(base_url=cfg.base_url, api_key=key, timeout=cfg.timeout_s)
    models = client.models.list()
    ids = {getattr(item, "id", "") for item in getattr(models, "data", [])}
    if cfg.model_name not in ids:
        return False, f"Configured model is not visible to this key: {cfg.model_name}"
    return True, f"Authenticated; configured model visible: {cfg.model_name}"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--live", action="store_true", help="Verify the live Token Factory model catalog")
    args = parser.parse_args()

    errors = validate_config()
    if errors:
        for error in errors:
            print(f"ERROR: {error}")
        return 1

    cfg = get_runtime_config()
    print(f"Sutreva environment: {cfg.environment}")
    print(f"Provider: {cfg.provider}")
    print(f"Model: {cfg.model_name}")
    print(f"Base URL: {cfg.base_url}")

    if args.live:
        try:
            ok, message = live_check()
        except Exception as exc:  # noqa: BLE001 - CLI should expose the provider error.
            print(f"LIVE ERROR: {exc}")
            return 2
        print(message)
        return 0 if ok else 2

    print("Offline preflight passed. Use --live after setting NEBIUS_API_KEY for provider verification.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
