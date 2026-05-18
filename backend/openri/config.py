from __future__ import annotations

import os
from pathlib import Path
from typing import List


DEFAULT_API_ORIGINS = ("http://localhost:5173", "http://127.0.0.1:5173")
DEFAULT_UPLOAD_LIMIT_BYTES = 20 * 1024 * 1024


def env_bool(name: str, default: bool = False) -> bool:
    raw = os.environ.get(name)
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "yes", "on"}


def env_int(name: str, default: int) -> int:
    raw = os.environ.get(name)
    if raw is None:
        return default
    try:
        return int(raw)
    except ValueError:
        return default


def split_csv_env(name: str, default: tuple[str, ...] = ()) -> List[str]:
    raw = os.environ.get(name, "")
    items = [item.strip() for item in raw.split(",") if item.strip()]
    return items or list(default)


def upload_limit_bytes() -> int:
    return env_int("OPENRI_UPLOAD_LIMIT_BYTES", DEFAULT_UPLOAD_LIMIT_BYTES)


def retention_days() -> int:
    return env_int("OPENRI_RETENTION_DAYS", 0)


def rate_limit_per_minute() -> int:
    return env_int("OPENRI_RATE_LIMIT_PER_MINUTE", 0)


def allowed_cors_origins() -> List[str]:
    return split_csv_env("OPENRI_CORS_ORIGINS", DEFAULT_API_ORIGINS)


def require_api_key() -> bool:
    return env_bool("OPENRI_REQUIRE_API_KEY", False)


def configured_api_keys() -> List[str]:
    return split_csv_env("OPENRI_API_KEYS")


def crossref_cache_dir() -> Path:
    return Path(os.environ.get("OPENRI_CROSSREF_CACHE_DIR", "~/.cache/openri/crossref")).expanduser()
