from __future__ import annotations

from typing import Any

from . import __version__
from .models import Finding, RunReport, Severity, Status


_SEVERITY_TO_SARIF_LEVEL = {
    Severity.CRITICAL: "error",
    Severity.HIGH: "error",
    Severity.MEDIUM: "warning",
    Severity.LOW: "note",
    Severity.INFO: "note",
}


def _line_from_location(location: str | None) -> int:
    if not location:
        return 1
    digits = "".join(ch for ch in location if ch.isdigit())
    return int(digits) if digits else 1


def _result_from_finding(finding: Finding, artifact_uri: str) -> dict[str, Any]:
    locations: list[dict[str, Any]] = []
    if finding.evidence:
        for ev in finding.evidence:
            if ev.location:
                locations.append(
                    {
                        "physicalLocation": {
                            "artifactLocation": {"uri": artifact_uri},
                            "region": {"startLine": _line_from_location(ev.location)},
                        }
                    }
                )
    if not locations:
        locations.append(
            {
                "physicalLocation": {
                    "artifactLocation": {"uri": artifact_uri},
                    "region": {"startLine": 1},
                }
            }
        )
    return {
        "ruleId": finding.check_id,
        "level": _SEVERITY_TO_SARIF_LEVEL.get(finding.severity, "warning"),
        "message": {"text": f"{finding.title}: {finding.message}"},
        "locations": locations,
        "properties": {
            "score": finding.score,
            "status": finding.status.value,
            "severity": finding.severity.value,
            "recommendation": finding.recommendation,
            "tags": finding.tags,
        },
    }


def _rule_from_finding(finding: Finding) -> dict[str, Any]:
    return {
        "id": finding.check_id,
        "name": finding.title,
        "shortDescription": {"text": finding.title},
        "fullDescription": {"text": finding.recommendation or finding.message},
        "defaultConfiguration": {"level": _SEVERITY_TO_SARIF_LEVEL.get(finding.severity, "warning")},
        "properties": {"category": finding.category, "tags": finding.tags},
    }


def report_to_sarif(report: RunReport, artifact_uri: str = "manuscript.txt") -> dict[str, Any]:
    findings_to_export = [f for f in report.findings if f.status in {Status.WARNING, Status.FAILED}]
    seen_rules: dict[str, dict[str, Any]] = {}
    for finding in findings_to_export:
        seen_rules.setdefault(finding.check_id, _rule_from_finding(finding))
    return {
        "$schema": "https://raw.githubusercontent.com/oasis-tcs/sarif-spec/master/Schemata/sarif-schema-2.1.0.json",
        "version": "2.1.0",
        "runs": [
            {
                "tool": {
                    "driver": {
                        "name": "OpenRI",
                        "informationUri": "https://github.com/your-org/openri",
                        "version": __version__,
                        "rules": list(seen_rules.values()),
                    }
                },
                "results": [_result_from_finding(f, artifact_uri) for f in findings_to_export],
                "properties": {
                    "strictness": report.strictness,
                    "summary": report.summary.model_dump(),
                    "report_id": report.report_id,
                    "manuscript_title": report.title,
                },
            }
        ],
    }
