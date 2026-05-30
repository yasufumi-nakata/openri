from __future__ import annotations

import json
import os
import time
import urllib.error
import urllib.request
from typing import Optional

from . import __version__
from .config import crossref_cache_dir

CROSSREF_API = "https://api.crossref.org/works/"


def _user_agent() -> str:
    mailto = os.environ.get("OPENRI_CROSSREF_MAILTO", "").strip()
    contact = f"; mailto:{mailto}" if mailto else ""
    return f"OpenRI/{__version__} (https://github.com/yasufumi-nakata/openri{contact})"


def lookup_doi(
    doi: str, timeout: Optional[float] = None, cache_only: Optional[bool] = None, retries: Optional[int] = None
) -> dict:
    """Return a small dict describing the Crossref lookup outcome for a DOI.

    Network is the user's responsibility — callers should gate this on an opt-in flag.
    """
    timeout = timeout if timeout is not None else float(os.environ.get("OPENRI_CROSSREF_TIMEOUT", "4.0"))
    cache_only = (
        cache_only
        if cache_only is not None
        else os.environ.get("OPENRI_CROSSREF_CACHE_ONLY", "").lower() in {"1", "true", "yes"}
    )
    retries = retries if retries is not None else int(os.environ.get("OPENRI_CROSSREF_RETRIES", "2"))
    cached = _read_cache(doi)
    if cached is not None:
        cached["cache"] = "hit"
        return cached
    if cache_only:
        return {"doi": doi, "status": "cache_miss", "cache": "miss", "network": "disabled"}

    url = CROSSREF_API + urllib.request.quote(doi, safe="")
    request = urllib.request.Request(url, headers={"User-Agent": _user_agent(), "Accept": "application/json"})
    payload = None
    last_error: Optional[dict] = None
    for attempt in range(retries + 1):
        try:
            with urllib.request.urlopen(request, timeout=timeout) as response:
                payload = json.loads(response.read().decode("utf-8", errors="replace"))
            break
        except urllib.error.HTTPError as exc:
            result = {
                "doi": doi,
                "status": "missing" if exc.code == 404 else "http_error",
                "http_status": exc.code,
                "cache": "miss",
                "attempts": attempt + 1,
            }
            if exc.code == 404:
                _write_cache(doi, result)
                return result
            last_error = result
        except (urllib.error.URLError, TimeoutError, json.JSONDecodeError) as exc:
            last_error = {
                "doi": doi,
                "status": "error",
                "error": str(exc)[:160],
                "cache": "miss",
                "attempts": attempt + 1,
            }
        if attempt < retries:
            time.sleep(min(2.0, 0.25 * (2**attempt)))
    if payload is None:
        return last_error or {"doi": doi, "status": "error", "cache": "miss"}

    message = payload.get("message", {}) if isinstance(payload, dict) else {}
    result = {
        "doi": doi,
        "status": "found",
        "title": (message.get("title") or [None])[0],
        "type": message.get("type"),
        "issued_year": _issued_year(message),
        "publisher": message.get("publisher"),
        "cache": "miss",
    }
    _write_cache(doi, result)
    return result


def _issued_year(message: dict) -> Optional[int]:
    parts = message.get("issued", {}).get("date-parts") if isinstance(message.get("issued"), dict) else None
    if not parts or not parts[0]:
        return None
    first = parts[0][0]
    return int(first) if isinstance(first, int) else None


def _cache_path(doi: str):
    digest = urllib.request.quote(doi.lower(), safe="")
    return crossref_cache_dir() / f"{digest}.json"


def _read_cache(doi: str) -> Optional[dict]:
    path = _cache_path(doi)
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None


def _write_cache(doi: str, payload: dict) -> None:
    path = _cache_path(doi)
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    except OSError:
        return
