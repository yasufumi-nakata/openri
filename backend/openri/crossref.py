from __future__ import annotations

import json
import os
import urllib.error
import urllib.request
from typing import Optional


CROSSREF_API = "https://api.crossref.org/works/"


def _user_agent() -> str:
    mailto = os.environ.get("OPENRI_CROSSREF_MAILTO", "openri@example.org")
    return f"OpenRI/0.2 (https://example.org/openri; mailto:{mailto})"


def lookup_doi(doi: str, timeout: float = 4.0) -> dict:
    """Return a small dict describing the Crossref lookup outcome for a DOI.

    Network is the user's responsibility — callers should gate this on an opt-in flag.
    """
    url = CROSSREF_API + urllib.request.quote(doi, safe="")
    request = urllib.request.Request(url, headers={"User-Agent": _user_agent(), "Accept": "application/json"})
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            payload = json.loads(response.read().decode("utf-8", errors="replace"))
    except urllib.error.HTTPError as exc:
        return {
            "doi": doi,
            "status": "missing" if exc.code == 404 else "http_error",
            "http_status": exc.code,
        }
    except (urllib.error.URLError, TimeoutError, json.JSONDecodeError) as exc:
        return {"doi": doi, "status": "error", "error": str(exc)[:160]}

    message = payload.get("message", {}) if isinstance(payload, dict) else {}
    return {
        "doi": doi,
        "status": "found",
        "title": (message.get("title") or [None])[0],
        "type": message.get("type"),
        "issued_year": _issued_year(message),
        "publisher": message.get("publisher"),
    }


def _issued_year(message: dict) -> Optional[int]:
    parts = message.get("issued", {}).get("date-parts") if isinstance(message.get("issued"), dict) else None
    if not parts or not parts[0]:
        return None
    first = parts[0][0]
    return int(first) if isinstance(first, int) else None
