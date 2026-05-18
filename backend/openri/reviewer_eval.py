from __future__ import annotations

import json
from pathlib import Path
from typing import Iterable, List


CRITICAL_LABELS = {"critical", "high", "major", "must_fix"}


def load_review_result(path: Path) -> dict:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"{path} must contain a JSON object")
    payload.setdefault("model", path.stem)
    payload.setdefault("findings", [])
    return payload


def compare_review_results(paths: Iterable[Path]) -> dict:
    results = [load_review_result(path) for path in paths]
    by_model = {}
    all_keys = set()
    for result in results:
        model = str(result["model"])
        findings = result.get("findings", [])
        keys = {_finding_key(item) for item in findings if _is_major(item)}
        by_model[model] = sorted(keys)
        all_keys.update(keys)

    missing_by_model = {
        model: sorted(all_keys - set(keys))
        for model, keys in by_model.items()
    }
    recall = {
        model: 1.0 if not all_keys else round(len(set(keys) & all_keys) / len(all_keys), 3)
        for model, keys in by_model.items()
    }
    disagreements = [
        {
            "finding_key": key,
            "present_in": sorted(model for model, keys in by_model.items() if key in keys),
            "missing_in": sorted(model for model, keys in by_model.items() if key not in keys),
        }
        for key in sorted(all_keys)
        if any(key not in keys for keys in by_model.values())
    ]
    return {
        "schema": "openri-cross-model-review-eval-v1",
        "models": sorted(by_model),
        "major_finding_universe": sorted(all_keys),
        "major_finding_recall": recall,
        "missing_by_model": missing_by_model,
        "disagreements": disagreements,
        "policy": "Disagreement is recorded as evidence/rubric debt, not resolved by majority vote.",
    }


def _is_major(item: dict) -> bool:
    severity = str(item.get("severity", "")).lower()
    status = str(item.get("status", "")).lower()
    return severity in CRITICAL_LABELS or status in CRITICAL_LABELS


def _finding_key(item: dict) -> str:
    if item.get("check_id"):
        return str(item["check_id"])
    if item.get("id"):
        return str(item["id"])
    return str(item.get("title", "unknown")).strip().lower().replace(" ", "_")[:80]


def write_eval_report(paths: List[Path], out: Path) -> dict:
    report = compare_review_results(paths)
    out.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return report
