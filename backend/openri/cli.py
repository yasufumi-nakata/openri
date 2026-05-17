from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from . import __version__
from .analyzer import analyze_manuscript
from .models import RunRequest, Severity, Status
from .pdf import extract_text_from_pdf
from .pdf_inspect import inspect_pdf
from .sarif import report_to_sarif
from .store import ReportStore


_SEVERITY_RANK = {
    "info": 0,
    "low": 1,
    "medium": 2,
    "high": 3,
    "critical": 4,
}


def _read_manuscript(path: str) -> tuple[str, str, Path | None]:
    if path == "-":
        return sys.stdin.read(), "stdin", None
    p = Path(path).expanduser()
    if not p.exists():
        raise FileNotFoundError(f"manuscript not found: {p}")
    if p.suffix.lower() == ".pdf":
        return extract_text_from_pdf(p), p.name, p
    return p.read_text(encoding="utf-8", errors="replace"), p.name, None


def _max_finding_rank(findings, only_statuses) -> int:
    rank = -1
    for f in findings:
        if f.status not in only_statuses:
            continue
        rank = max(rank, _SEVERITY_RANK.get(f.severity.value, 0))
    return rank


def _print_human(report) -> None:
    summary = report.summary
    protocol = report.ai_review_protocol or {}
    packet = protocol.get("review_packet", {})
    readiness = protocol.get("run_readiness", {})
    handoff = packet.get("editor_handoff", {})
    print(f"OpenRI report {report.report_id}")
    print(f"title: {report.title}")
    print(f"strictness: {report.strictness}")
    print(f"score: {summary.score}/100  passed={summary.passed} warnings={summary.warnings} "
          f"failed={summary.failed} skipped={summary.skipped}")
    if readiness:
        print(f"ai_review_readiness: {readiness.get('state')} - {readiness.get('label')}")
    if handoff:
        print(
            "review_packet: "
            f"claims={handoff.get('claim_count', 0)} "
            f"tasks={handoff.get('task_count', 0)} "
            f"challenges={handoff.get('challenge_count', 0)}"
        )
    print()
    for f in report.findings:
        marker = {
            Status.PASSED: "PASS",
            Status.WARNING: "WARN",
            Status.FAILED: "FAIL",
            Status.SKIPPED: "SKIP",
        }[f.status]
        print(f"  [{marker}] {f.check_id} ({f.severity.value}, score={f.score})")
        print(f"          {f.message}")
        if f.evidence:
            for ev in f.evidence[:3]:
                where = f" @{ev.location}" if ev.location else ""
                quote = (ev.quote or "").replace("\n", " ")[:120]
                if quote:
                    print(f"            evidence{where}: {quote}")


def cmd_check(args: argparse.Namespace) -> int:
    try:
        text, source_name, pdf_path = _read_manuscript(args.manuscript)
    except FileNotFoundError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2

    if not text.strip():
        print("error: empty manuscript", file=sys.stderr)
        return 2

    pdf_inspection = None
    if pdf_path is not None:
        try:
            pdf_inspection = inspect_pdf(pdf_path)
        except Exception as exc:  # noqa: BLE001 - report and continue
            print(f"warning: PDF inspection failed: {exc}", file=sys.stderr)
            pdf_inspection = {"available": False, "reason": str(exc), "hidden_text": [], "page_count": 0}

    request = RunRequest(
        manuscript_text=text,
        title=args.title or source_name,
        strictness=args.strictness,
        review_mode=args.review_mode,
        include_experimental_checks=not args.no_experimental,
        activated_rulesets=args.ruleset or [],
        enable_network=args.network,
        pdf_inspection=pdf_inspection,
    )
    report = analyze_manuscript(request)

    if args.save:
        ReportStore().save(report)

    if args.sarif:
        sarif_payload = report_to_sarif(report, artifact_uri=source_name)
        Path(args.sarif).expanduser().write_text(json.dumps(sarif_payload, indent=2, ensure_ascii=False))

    if args.json:
        sys.stdout.write(report.model_dump_json(indent=2))
        sys.stdout.write("\n")
    else:
        _print_human(report)

    if args.fail_on:
        threshold = _SEVERITY_RANK[args.fail_on]
        max_rank = _max_finding_rank(report.findings, {Status.WARNING, Status.FAILED})
        if max_rank >= threshold:
            return 1
    return 0


def cmd_list(args: argparse.Namespace) -> int:
    rows = ReportStore().list_recent(args.limit)
    if args.json:
        sys.stdout.write(json.dumps(rows, indent=2, ensure_ascii=False))
        sys.stdout.write("\n")
        return 0
    if not rows:
        print("(no saved reports)")
        return 0
    for r in rows:
        print(f"{r['created_at']}  {r['report_id']}  score={r['score']:3d}  "
              f"failed={r['failed']}  warnings={r['warnings']}  {r['title']}")
    return 0


def cmd_show(args: argparse.Namespace) -> int:
    report = ReportStore().get(args.report_id)
    if report is None:
        print(f"error: report not found: {args.report_id}", file=sys.stderr)
        return 2
    if args.sarif:
        Path(args.sarif).expanduser().write_text(
            json.dumps(report_to_sarif(report), indent=2, ensure_ascii=False)
        )
    if args.json:
        sys.stdout.write(report.model_dump_json(indent=2))
        sys.stdout.write("\n")
    else:
        _print_human(report)
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="openri", description="Open Research Integrity test runner")
    parser.add_argument("--version", action="version", version=f"openri {__version__}")
    sub = parser.add_subparsers(dest="command", required=True)

    p_check = sub.add_parser("check", help="Run integrity checks on a manuscript (txt, md, or pdf)")
    p_check.add_argument("manuscript", help="Path to manuscript or '-' for stdin")
    p_check.add_argument("--title", default=None)
    p_check.add_argument("--strictness", choices=["lenient", "standard", "strict"], default="standard")
    p_check.add_argument(
        "--review-mode",
        choices=["integrity_triage", "ai_reviewer_replication"],
        default="ai_reviewer_replication",
        help="Select the review protocol mode for the report packet.",
    )
    p_check.add_argument("--no-experimental", action="store_true", help="Skip experimental checks")
    p_check.add_argument("--json", action="store_true", help="Print the report as JSON")
    p_check.add_argument("--sarif", metavar="PATH", help="Write SARIF 2.1.0 output to PATH")
    p_check.add_argument("--save", action="store_true", help="Persist the report to the SQLite store")
    p_check.add_argument(
        "--fail-on",
        choices=list(_SEVERITY_RANK.keys()),
        default=None,
        help="Exit with status 1 if any warning/failed finding meets or exceeds this severity",
    )
    p_check.add_argument(
        "--ruleset",
        action="append",
        default=None,
        metavar="ID",
        help="Activate a keyword ruleset by id (consort, prisma, mdar_strict, or a custom one). Repeatable.",
    )
    p_check.add_argument(
        "--network",
        action="store_true",
        help="Enable network-backed checks (Crossref DOI lookups).",
    )
    p_check.set_defaults(func=cmd_check)

    p_list = sub.add_parser("list", help="List saved reports from the local store")
    p_list.add_argument("--limit", type=int, default=20)
    p_list.add_argument("--json", action="store_true")
    p_list.set_defaults(func=cmd_list)

    p_show = sub.add_parser("show", help="Show a saved report by report_id")
    p_show.add_argument("report_id")
    p_show.add_argument("--json", action="store_true")
    p_show.add_argument("--sarif", metavar="PATH", help="Write SARIF for this report to PATH")
    p_show.set_defaults(func=cmd_show)

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
