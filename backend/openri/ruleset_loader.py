from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable, Optional

RULESETS_DIR = Path(__file__).parent / "rulesets"


@dataclass(frozen=True)
class Pattern:
    id: str
    type: str  # "phrase" | "regex" | "codepoint"
    value: str
    severity: str  # "info" | "low" | "medium" | "high" | "critical"


@dataclass(frozen=True)
class Ruleset:
    id: str
    name: str
    description: str
    patterns: tuple[Pattern, ...]


@dataclass(frozen=True)
class KeywordItem:
    id: str
    label: str
    keywords: tuple[str, ...]
    severity: str = "medium"
    required_evidence: tuple[str, ...] = ()
    not_applicable_policy: str = "requires_explicit_reason"
    section_preference: tuple[str, ...] = ()
    reference_url: str = ""


@dataclass(frozen=True)
class KeywordRuleset:
    id: str
    name: str
    description: str
    items: tuple[KeywordItem, ...]


def _coerce_pattern(raw: dict[str, Any]) -> Pattern:
    return Pattern(
        id=str(raw["id"]),
        type=str(raw.get("type", "phrase")),
        value=str(raw["value"]),
        severity=str(raw.get("severity", "medium")).lower(),
    )


def _load_yaml(path: Path) -> dict[str, Any]:
    try:
        import yaml  # type: ignore
    except ImportError as exc:
        raise RuntimeError(
            "PyYAML is required to load OpenRI rulesets. Install pyyaml or remove the ruleset path."
        ) from exc
    with path.open("r", encoding="utf-8") as handle:
        loaded = yaml.safe_load(handle) or {}
    if not isinstance(loaded, dict):
        raise ValueError(f"Ruleset {path} must be a mapping at the top level.")
    return loaded


def load_ruleset(path: Path) -> Ruleset:
    raw = _load_yaml(path)
    patterns = tuple(_coerce_pattern(p) for p in raw.get("patterns", []))
    return Ruleset(
        id=str(raw.get("id", path.stem)),
        name=str(raw.get("name", path.stem)),
        description=str(raw.get("description", "")),
        patterns=patterns,
    )


def load_default_ruleset(name: str) -> Optional[Ruleset]:
    path = RULESETS_DIR / f"{name}.yaml"
    if not path.exists():
        return None
    try:
        return load_ruleset(path)
    except RuntimeError:
        return None


def load_extra_rulesets(env_var: str) -> Iterable[Ruleset]:
    value = os.environ.get(env_var, "").strip()
    if not value:
        return ()
    rulesets: list[Ruleset] = []
    for raw_path in value.split(os.pathsep):
        candidate = Path(raw_path).expanduser()
        if candidate.exists():
            rulesets.append(load_ruleset(candidate))
    return tuple(rulesets)


def merge_patterns(rulesets: Iterable[Ruleset]) -> list[Pattern]:
    seen_ids: set[str] = set()
    merged: list[Pattern] = []
    for ruleset in rulesets:
        for pattern in ruleset.patterns:
            if pattern.id in seen_ids:
                continue
            seen_ids.add(pattern.id)
            merged.append(pattern)
    return merged


def _coerce_keyword_item(raw: dict[str, Any]) -> KeywordItem:
    keywords = tuple(str(k).lower() for k in raw.get("keywords", []))
    return KeywordItem(
        id=str(raw["id"]),
        label=str(raw.get("label", raw["id"])),
        keywords=keywords,
        severity=str(raw.get("severity", "medium")).lower(),
        required_evidence=tuple(str(item) for item in raw.get("required_evidence", [])),
        not_applicable_policy=str(raw.get("not_applicable_policy", "requires_explicit_reason")),
        section_preference=tuple(str(item).lower() for item in raw.get("section_preference", [])),
        reference_url=str(raw.get("reference_url", "")),
    )


def load_keyword_ruleset(path: Path) -> KeywordRuleset:
    raw = _load_yaml(path)
    items = tuple(_coerce_keyword_item(item) for item in raw.get("items", []))
    return KeywordRuleset(
        id=str(raw.get("id", path.stem)),
        name=str(raw.get("name", path.stem)),
        description=str(raw.get("description", "")),
        items=items,
    )


def load_default_keyword_ruleset(name: str) -> Optional[KeywordRuleset]:
    path = RULESETS_DIR / f"{name}.yaml"
    if not path.exists():
        return None
    try:
        return load_keyword_ruleset(path)
    except RuntimeError:
        return None


def discover_keyword_rulesets() -> dict[str, Path]:
    """Return id -> path for ruleset YAMLs that look like keyword rulesets."""
    out: dict[str, Path] = {}
    if not RULESETS_DIR.exists():
        return out
    for path in sorted(RULESETS_DIR.glob("*.yaml")):
        try:
            raw = _load_yaml(path)
        except (RuntimeError, ValueError):
            continue
        if "items" in raw:
            out[str(raw.get("id", path.stem))] = path
    return out
