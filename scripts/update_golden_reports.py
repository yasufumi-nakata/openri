from __future__ import annotations

import json
from pathlib import Path

from openri.analyzer import analyze_manuscript
from openri.models import RunRequest


ROOT = Path(__file__).resolve().parents[1]
SAMPLE_DIR = ROOT / "samples" / "golden"
REPORT_DIR = ROOT / "backend" / "tests" / "golden_reports"


def main() -> int:
    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    for sample in sorted(SAMPLE_DIR.glob("*.txt")):
        report = analyze_manuscript(
            RunRequest(
                manuscript_text=sample.read_text(encoding="utf-8"),
                title=sample.name,
                activated_rulesets=["consort"] if "ruleset" in sample.name else [],
            )
        )
        payload = json.loads(report.model_dump_json())
        payload["report_id"] = "golden-stable-id"
        payload["created_at"] = "2026-01-01T00:00:00Z"
        out = REPORT_DIR / f"{sample.stem}.json"
        out.write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
