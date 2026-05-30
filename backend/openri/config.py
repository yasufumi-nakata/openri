from __future__ import annotations

import os
from pathlib import Path
from typing import List, Optional

DEFAULT_API_ORIGINS = ("http://localhost:5173", "http://127.0.0.1:5173")
DEFAULT_UPLOAD_LIMIT_BYTES = 20 * 1024 * 1024


def env_bool(name: str, default: bool = False) -> bool:
    raw = os.environ.get(name)
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "yes", "on"}


def env_int(name: str, default: int, *, minimum: Optional[int] = None, maximum: Optional[int] = None) -> int:
    raw = os.environ.get(name)
    if raw is None:
        return default
    try:
        value = int(raw)
    except ValueError:
        return default
    if minimum is not None and value < minimum:
        return default
    if maximum is not None and value > maximum:
        return default
    return value


def split_csv_env(name: str, default: tuple[str, ...] = ()) -> List[str]:
    raw = os.environ.get(name, "")
    items = [item.strip() for item in raw.split(",") if item.strip()]
    return items or list(default)


def upload_limit_bytes() -> int:
    return env_int("OPENRI_UPLOAD_LIMIT_BYTES", DEFAULT_UPLOAD_LIMIT_BYTES, minimum=1)


def retention_days() -> int:
    return env_int("OPENRI_RETENTION_DAYS", 0, minimum=0)


def rate_limit_per_minute() -> int:
    return env_int("OPENRI_RATE_LIMIT_PER_MINUTE", 0, minimum=0)


def allowed_cors_origins() -> List[str]:
    origins = split_csv_env("OPENRI_CORS_ORIGINS", DEFAULT_API_ORIGINS)
    if "*" in origins:
        raise ValueError("OPENRI_CORS_ORIGINS='*' is not allowed; configure explicit trusted origins.")
    return origins


def cors_allow_credentials() -> bool:
    return env_bool("OPENRI_CORS_ALLOW_CREDENTIALS", False)


def rate_limit_key_source() -> str:
    value = os.environ.get("OPENRI_RATE_LIMIT_KEY", "client_ip").strip().lower()
    if value not in {"client_ip", "api_key"}:
        return "client_ip"
    return value


def trust_forwarded_for() -> bool:
    return env_bool("OPENRI_TRUST_X_FORWARDED_FOR", False)


def require_api_key() -> bool:
    return env_bool("OPENRI_REQUIRE_API_KEY", False)


def configured_api_keys() -> List[str]:
    return split_csv_env("OPENRI_API_KEYS")


def crossref_cache_dir() -> Path:
    return Path(os.environ.get("OPENRI_CROSSREF_CACHE_DIR", "~/.cache/openri/crossref")).expanduser()
