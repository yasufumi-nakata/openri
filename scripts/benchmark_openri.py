from __future__ import annotations

import argparse
import json
from pathlib import Path

from openri.analyzer import analyze_manuscript
from openri.models import RunRequest, Status


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SAMPLE_DIR = ROOT / "samples" / "golden"


EXPECTED = {
    "clean_transparent": {"must_not_fail": True},
    "p_value_mismatch": {"expected_checks": ["statistical_consistency"]},
    "missing_transparency": {"expected_checks": ["reporting_transparency"]},
    "prompt_injection": {"expected_checks": ["prompt_injection"]},
    "placeholder_citation": {"expected_checks": ["citation_integrity", "citation_context"]},
    "ruleset_omission": {"expected_checks": ["ruleset_coverage"], "rulesets": ["consort"]},
    "unsupported_causal_claim": {"expected_checks": ["citation_context"]},
}


def run_benchmark(sample_dir: Path = DEFAULT_SAMPLE_DIR) -> dict:
    cases = []
    expected_total = 0
    expected_hit = 0
    warning_or_fail = 0
    coverage_blockers = 0
    routes = {}
    for path in sorted(sample_dir.glob("*.txt")):
        config = EXPECTED.get(path.stem, {})
        rulesets = list(config.get("rulesets", []))
        report = analyze_manuscript(
            RunRequest(
                manuscript_text=path.read_text(encoding="utf-8"),
                title=path.name,
                activated_rulesets=rulesets,
            )
        )
        active = {finding.check_id for finding in report.findings if finding.status in {Status.WARNING, Status.FAILED}}
        expected_checks = set(config.get("expected_checks", []))
        expected_total += len(expected_checks)
        expected_hit += len(active & expected_checks)
        warning_or_fail += len(active)
        blockers = report.ai_review_protocol.get("coverage_blockers", [])
        coverage_blockers += len(blockers)
        route = report.submission_processing["recommended_route"]
        routes[route] = routes.get(route, 0) + 1
        cases.append(
            {
                "case": path.stem,
                "score": report.summary.score,
                "route": route,
                "expected_checks": sorted(expected_checks),
                "hit_expected_checks": sorted(active & expected_checks),
                "warning_or_failed_checks": sorted(active),
                "coverage_blocker_count": len(blockers),
            }
        )

    recall_proxy = 1.0 if expected_total == 0 else expected_hit / expected_total
    precision_proxy = 1.0 if warning_or_fail == 0 else expected_hit / warning_or_fail
    return {
        "schema": "openri-public-benchmark-v1",
        "case_count": len(cases),
        "recall_proxy": round(recall_proxy, 3),
        "precision_proxy": round(precision_proxy, 3),
        "route_distribution": routes,
        "coverage_blocker_count": coverage_blockers,
        "cases": cases,
    }


def write_markdown(report: dict, path: Path) -> None:
    lines = [
        "# OpenRI benchmark summary",
        "",
        f"- Cases: {report['case_count']}",
        f"- Recall proxy: {report['recall_proxy']}",
        f"- Precision proxy: {report['precision_proxy']}",
        f"- Coverage blockers: {report['coverage_blocker_count']}",
        "",
        "| Case | Score | Route | Expected hits | Active findings |",
        "| --- | ---: | --- | --- | --- |",
    ]
    for case in report["cases"]:
        lines.append(
            f"| {case['case']} | {case['score']} | {case['route']} | "
            f"{', '.join(case['hit_expected_checks']) or '-'} | {', '.join(case['warning_or_failed_checks']) or '-'} |"
        )
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--sample-dir", default=str(DEFAULT_SAMPLE_DIR))
    parser.add_argument("--json-out", default="benchmark/openri-benchmark.json")
    parser.add_argument("--md-out", default="benchmark/openri-benchmark.md")
    args = parser.parse_args()
    report = run_benchmark(Path(args.sample_dir))
    json_out = Path(args.json_out)
    md_out = Path(args.md_out)
    json_out.parent.mkdir(parents=True, exist_ok=True)
    md_out.parent.mkdir(parents=True, exist_ok=True)
    json_out.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    write_markdown(report, md_out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
