from __future__ import annotations

import json
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Iterable

from .models import Evidence, Finding, Severity, Status

PluginCheckFunction = Callable[[str, dict], Finding]


@dataclass(frozen=True)
class PluginCheckSpec:
    id: str
    title: str
    category: str
    description: str
    maturity: str
    run: PluginCheckFunction
    source: str


def load_plugin_checks() -> list[PluginCheckSpec]:
    specs: list[PluginCheckSpec] = []
    for path in _plugin_paths():
        specs.extend(_load_manifest(path))
    return specs


def _plugin_paths() -> Iterable[Path]:
    raw = os.environ.get("OPENRI_CHECK_PLUGIN_PATHS", "").strip()
    if not raw:
        return ()
    return tuple(Path(item).expanduser() for item in raw.split(os.pathsep) if item.strip())


def _load_manifest(path: Path) -> list[PluginCheckSpec]:
    if not path.exists() or not path.is_file():
        return []
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return []
    checks = payload.get("checks", []) if isinstance(payload, dict) else []
    specs: list[PluginCheckSpec] = []
    for raw in checks:
        if not isinstance(raw, dict):
            continue
        check_id = str(raw.get("id", "")).strip()
        keywords = [str(item).lower() for item in raw.get("keywords", []) if str(item).strip()]
        if not check_id or not keywords:
            continue
        spec = PluginCheckSpec(
            id=f"plugin:{check_id}" if not check_id.startswith("plugin:") else check_id,
            title=str(raw.get("title", check_id)),
            category=str(raw.get("category", "plugin")),
            description=str(raw.get("description", "Declarative OpenRI plugin check.")),
            maturity=_maturity(str(raw.get("maturity", "experimental"))),
            run=_keyword_plugin_runner(
                check_id=f"plugin:{check_id}" if not check_id.startswith("plugin:") else check_id,
                title=str(raw.get("title", check_id)),
                category=str(raw.get("category", "plugin")),
                keywords=keywords,
                severity=_severity(str(raw.get("severity", "medium"))),
                source=str(path),
            ),
            source=str(path),
        )
        specs.append(spec)
    return specs


def _maturity(value: str) -> str:
    lowered = value.strip().lower()
    return lowered if lowered in {"stable", "beta", "experimental"} else "experimental"


def _severity(value: str) -> Severity:
    return {
        "critical": Severity.CRITICAL,
        "high": Severity.HIGH,
        "medium": Severity.MEDIUM,
        "low": Severity.LOW,
        "info": Severity.INFO,
    }.get(value.lower(), Severity.MEDIUM)


def _keyword_plugin_runner(
    check_id: str,
    title: str,
    category: str,
    keywords: list[str],
    severity: Severity,
    source: str,
) -> PluginCheckFunction:
    def run(text: str, profile: dict) -> Finding:
        lowered = text.lower()
        hits = []
        for keyword in keywords:
            index = lowered.find(keyword)
            if index >= 0:
                hits.append(
                    Evidence(
                        quote=text[index : index + 180],
                        data={"keyword": keyword, "plugin_source": source},
                    )
                )
        if hits:
            return Finding(
                check_id=check_id,
                title=title,
                category=category,
                severity=severity,
                status=Status.WARNING if severity != Severity.CRITICAL else Status.FAILED,
                score=50 if severity in {Severity.HIGH, Severity.CRITICAL} else 70,
                message=f"External declarative plugin check matched {len(hits)} keyword(s).",
                recommendation="Review this plugin finding against the plugin's documented journal or field policy.",
                evidence=hits[:8],
                tags=["plugin", "external-check"],
            )
        return Finding(
            check_id=check_id,
            title=title,
            category=category,
            severity=Severity.INFO,
            status=Status.PASSED,
            score=100,
            message="External declarative plugin check did not match.",
            recommendation="No plugin-specific action is required for this check.",
            evidence=[Evidence(data={"plugin_source": source, "keywords_checked": len(keywords)})],
            tags=["plugin", "external-check"],
        )

    return run


def plugin_security_boundary() -> dict:
    return {
        "mechanism": "OPENRI_CHECK_PLUGIN_PATHS declarative JSON manifest",
        "executes_arbitrary_code": False,
        "supported_check_type": "keyword_presence",
        "schema_compatibility": "plugin checks emit the same Finding schema as built-in checks",
        "limitations": [
            "Python entry-point execution is intentionally not enabled by default.",
            "Plugins cannot call external APIs unless OpenRI adds an explicit audited adapter.",
        ],
    }
