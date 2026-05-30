from __future__ import annotations

import argparse
import json
import re
import statistics
import urllib.parse
import urllib.request
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Set

from openri.analyzer import analyze_manuscript
from openri.models import RunRequest, Status

HF_ROWS_URL = (
    "https://datasets-server.huggingface.co/rows?"
    "dataset={dataset}&config={config}&split={split}&offset={offset}&length={length}"
)

REVIEW_CONCERN_PATTERNS = {
    "claim_evidence_or_overclaim": [
        r"\bclaim",
        r"\bevidence",
        r"overclaim",
        r"not support",
        r"unsupported",
        r"\bconclusion",
        r"\bcausal",
        r"\bnovel",
    ],
    "method_or_experiment": [
        r"\bexperiment",
        r"\bbaseline",
        r"\bablation",
        r"\bmethod",
        r"\bevaluation",
        r"\bdataset",
        r"\bsample",
        r"\bdesign",
    ],
    "statistics_or_results": [
        r"\bstatistic",
        r"significant",
        r"p[- ]?value",
        r"confidence interval",
        r"\bvariance",
        r"error bar",
        r"sample size",
    ],
    "reproducibility_or_code": [
        r"\bcode",
        r"reproduc",
        r"implementation",
        r"hyperparameter",
        r"\bdetails",
        r"\brelease",
        r"open source",
    ],
    "citation_or_related_work": [
        r"related work",
        r"\bcitation",
        r"\bcite",
        r"\breference",
        r"prior work",
        r"missing reference",
    ],
    "clarity_or_presentation": [
        r"\bclarity",
        r"\bclear",
        r"\btypo",
        r"\bwriting",
        r"presentation",
        r"difficult to read",
        r"organization",
    ],
}


def fetch_hf_rows(dataset: str, split: str, offset: int, length: int, config: str, timeout: float) -> dict:
    url = HF_ROWS_URL.format(
        dataset=urllib.parse.quote(dataset, safe=""),
        config=urllib.parse.quote(config, safe=""),
        split=urllib.parse.quote(split, safe=""),
        offset=offset,
        length=length,
    )
    with urllib.request.urlopen(url, timeout=timeout) as response:
        payload = json.loads(response.read().decode("utf-8"))
    payload["source_url"] = url
    return payload


def _cache_key(dataset: str, split: str, offset: int, length: int, config: str) -> str:
    raw = f"{dataset}__{config}__{split}__{offset}__{length}"
    return re.sub(r"[^A-Za-z0-9_.-]+", "_", raw)


def fetch_hf_rows_cached(
    dataset: str,
    split: str,
    offset: int,
    length: int,
    config: str,
    timeout: float,
    cache_dir: Optional[Path],
    refresh_cache: bool,
) -> dict:
    if cache_dir is None:
        payload = fetch_hf_rows(dataset, split, offset, length, config, timeout)
        payload["cache_status"] = "disabled"
        return payload

    cache_dir.mkdir(parents=True, exist_ok=True)
    cache_path = cache_dir / f"{_cache_key(dataset, split, offset, length, config)}.json"
    if cache_path.exists() and not refresh_cache:
        payload = json.loads(cache_path.read_text(encoding="utf-8"))
        payload["cache_status"] = "hit"
        payload["cache_path"] = str(cache_path)
        return payload

    try:
        payload = fetch_hf_rows(dataset, split, offset, length, config, timeout)
    except Exception:
        if cache_path.exists():
            payload = json.loads(cache_path.read_text(encoding="utf-8"))
            payload["cache_status"] = "stale-fallback"
            payload["cache_path"] = str(cache_path)
            return payload
        raise

    payload["cache_status"] = "refresh" if refresh_cache else "miss"
    payload["cache_path"] = str(cache_path)
    cache_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return payload


def manuscript_from_reviewbench(row: dict, max_chars: int) -> str:
    markdown = (row.get("markdown") or "").strip()
    if markdown:
        return markdown[:max_chars]
    return (
        f"Title\n{row.get('title', '')}\n\n"
        f"Abstract\n{row.get('abstract', '')}\n"
    )[:max_chars]


def manuscript_from_peersum(row: dict, max_chars: int) -> str:
    return (
        f"Title\n{row.get('paper_title', '')}\n\n"
        f"Abstract\n{row.get('paper_abstract', '')}\n"
    )[:max_chars]


def review_text_from_reviewbench(row: dict) -> str:
    raw = row.get("reviews_json")
    if raw in (None, ""):
        reviews: Any = []
    elif isinstance(raw, str):
        try:
            reviews = json.loads(raw)
        except json.JSONDecodeError:
            return raw
    else:
        reviews = raw
    if isinstance(reviews, dict):
        reviews = [reviews]
    if not isinstance(reviews, list):
        return str(reviews)
    chunks: List[str] = []
    for review in reviews:
        if not isinstance(review, dict):
            continue
        for key, value in review.items():
            if key in {"review_id", "reviewer", "rating", "confidence"}:
                continue
            if isinstance(value, str) and value.strip():
                chunks.append(value.strip())
    return "\n\n".join(chunks)


def review_text_from_peersum(row: dict) -> str:
    contents = row.get("review_contents") or []
    if isinstance(contents, list):
        return "\n\n".join(str(item) for item in contents if str(item).strip())
    return str(contents)


def detect_review_concerns(review_text: str) -> Set[str]:
    lowered = review_text.lower()
    concerns = set()
    for concern, patterns in REVIEW_CONCERN_PATTERNS.items():
        if any(re.search(pattern, lowered) for pattern in patterns):
            concerns.add(concern)
    return concerns


def openri_dimension_flags(report) -> Set[str]:
    active = {finding.check_id for finding in report.findings if finding.status in {Status.WARNING, Status.FAILED}}
    packet = report.ai_review_protocol.get("review_packet", {})
    high_tasks = {
        task.get("id")
        for task in packet.get("reviewer_tasks", [])
        if task.get("priority") in {"high", "critical"}
    }
    flags = set()
    if "claim_evidence_alignment" in active or packet.get("claim_inventory"):
        flags.add("claim_evidence_or_overclaim")
    if "task_method_and_design_challenge" in high_tasks:
        flags.add("method_or_experiment")
    if active & {"statistical_consistency", "summary_stat_plausibility", "effect_size_ci_coverage"}:
        flags.add("statistics_or_results")
    if active & {"reporting_transparency", "ruleset_coverage"} or "task_reproducibility_packet" in high_tasks:
        flags.add("reproducibility_or_code")
    if active & {"citation_integrity", "citation_context", "doi_existence"}:
        flags.add("citation_or_related_work")
    if active & {"template_text"}:
        flags.add("clarity_or_presentation")
    return flags


def summarize_counter(counter: Counter) -> Dict[str, int]:
    return {key: counter[key] for key in sorted(counter)}


def mean(values: Iterable[float]) -> float:
    values = list(values)
    return round(sum(values) / len(values), 3) if values else 0.0


def summarize_corpus(
    name: str,
    dataset: str,
    split: str,
    rows: List[dict],
    rows_total: Optional[int],
    source_url: str,
    max_chars: int,
) -> dict:
    scores: List[int] = []
    coverage_blockers: List[int] = []
    claim_counts: List[int] = []
    concern_overlap: List[float] = []
    route_counts: Counter = Counter()
    readiness_counts: Counter = Counter()
    active_findings: Counter = Counter()
    required_reviews: Counter = Counter()
    review_concern_counts: Counter = Counter()
    openri_dimension_counts: Counter = Counter()
    cases = []

    for item in rows:
        row = item["row"]
        if name == "reviewbench":
            manuscript_text = manuscript_from_reviewbench(row, max_chars)
            review_text = review_text_from_reviewbench(row)
            title = row.get("title") or f"row {item.get('row_idx')}"
            decision = row.get("decision")
        else:
            manuscript_text = manuscript_from_peersum(row, max_chars)
            review_text = review_text_from_peersum(row)
            title = row.get("paper_title") or f"row {item.get('row_idx')}"
            decision = row.get("paper_acceptance")

        report = analyze_manuscript(
            RunRequest(
                manuscript_text=manuscript_text,
                title=title,
                source_metadata={
                    "external_corpus": name,
                    "dataset": dataset,
                    "split": split,
                    "row_idx": item.get("row_idx"),
                },
            )
        )
        review_concerns = detect_review_concerns(review_text)
        openri_flags = openri_dimension_flags(report)
        overlap = (
            len(review_concerns & openri_flags) / len(review_concerns)
            if review_concerns
            else None
        )

        active = [finding.check_id for finding in report.findings if finding.status in {Status.WARNING, Status.FAILED}]
        scores.append(report.summary.score)
        coverage_blockers.append(len(report.ai_review_protocol.get("coverage_blockers", [])))
        claim_counts.append(len(report.ai_review_protocol.get("review_packet", {}).get("claim_inventory", [])))
        if overlap is not None:
            concern_overlap.append(overlap)
        route_counts[report.submission_processing["recommended_route"]] += 1
        readiness_counts[report.ai_review_protocol["run_readiness"]["state"]] += 1
        active_findings.update(active)
        required_reviews.update(report.ai_review_protocol.get("required_ai_reviews", []))
        review_concern_counts.update(review_concerns)
        openri_dimension_counts.update(openri_flags)
        cases.append(
            {
                "row_idx": item.get("row_idx"),
                "title": title,
                "decision": decision,
                "score": report.summary.score,
                "route": report.submission_processing["recommended_route"],
                "readiness": report.ai_review_protocol["run_readiness"]["state"],
                "active_findings": active,
                "coverage_blocker_count": coverage_blockers[-1],
                "claim_count": claim_counts[-1],
                "review_concern_categories": sorted(review_concerns),
                "openri_dimension_categories": sorted(openri_flags),
                "review_concern_overlap_proxy": round(overlap, 3) if overlap is not None else None,
            }
        )

    return {
        "corpus": name,
        "dataset": dataset,
        "split": split,
        "source_url": source_url,
        "rows_total": rows_total,
        "case_count": len(cases),
        "input_mode": "fulltext-markdown" if name == "reviewbench" else "title-abstract-only",
        "max_chars_per_case": max_chars,
        "score": {
            "mean": mean(scores),
            "median": round(statistics.median(scores), 3) if scores else 0.0,
            "min": min(scores) if scores else None,
            "max": max(scores) if scores else None,
        },
        "route_distribution": summarize_counter(route_counts),
        "readiness_distribution": summarize_counter(readiness_counts),
        "active_finding_counts": summarize_counter(active_findings),
        "required_ai_review_counts": summarize_counter(required_reviews),
        "review_concern_counts": summarize_counter(review_concern_counts),
        "openri_dimension_counts": summarize_counter(openri_dimension_counts),
        "review_concern_overlap_proxy_mean": mean(concern_overlap),
        "coverage_blocker_count_mean": mean(coverage_blockers),
        "claim_count_mean": mean(claim_counts),
        "cases": cases,
    }


def run_peer_review_corpus_benchmark(args: argparse.Namespace) -> dict:
    corpora = []
    if args.corpus in {"reviewbench", "all"}:
        corpora.append(("reviewbench", "Samarth0710/reviewbench", args.reviewbench_split))
    if args.corpus in {"peersum", "all"}:
        corpora.append(("peersum", "oaimli/PeerSum", "train"))

    reports = []
    cache_dir = getattr(args, "cache_dir", None)
    cache_path = Path(cache_dir).expanduser() if cache_dir else None
    refresh_cache = bool(getattr(args, "refresh_cache", False))
    for name, dataset, split in corpora:
        payload = fetch_hf_rows_cached(
            dataset,
            split,
            args.offset,
            args.limit,
            "default",
            args.timeout,
            cache_path,
            refresh_cache,
        )
        reports.append(
            summarize_corpus(
                name=name,
                dataset=dataset,
                split=split,
                rows=payload.get("rows", []),
                rows_total=payload.get("num_rows_total"),
                source_url=payload.get("source_url", ""),
                max_chars=args.max_chars,
            )
        )
        reports[-1]["fetch_cache"] = "enabled" if cache_path is not None else "disabled"

    return {
        "schema": "openri-peer-review-corpus-benchmark-v1",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "policy": (
            "This is an external-corpus smoke benchmark, not misconduct ground truth. "
            "Reviewer-text overlap is a heuristic proxy for whether OpenRI's review packet surfaces similar review dimensions."
        ),
        "corpora": reports,
    }


def write_markdown(report: dict, path: Path) -> None:
    lines = [
        "# OpenRI peer-review corpus benchmark",
        "",
        report["policy"],
        "",
    ]
    for corpus in report["corpora"]:
        lines.extend(
            [
                f"## {corpus['corpus']}",
                "",
                f"- Dataset: `{corpus['dataset']}` / split `{corpus['split']}`",
                f"- Input mode: {corpus['input_mode']}",
                f"- Cases: {corpus['case_count']} of {corpus.get('rows_total')}",
                f"- Fetch cache: {corpus.get('fetch_cache', 'unknown')}",
                f"- Mean score: {corpus['score']['mean']} (min {corpus['score']['min']}, max {corpus['score']['max']})",
                f"- Mean coverage blockers: {corpus['coverage_blocker_count_mean']}",
                f"- Mean claim count: {corpus['claim_count_mean']}",
                f"- Review concern overlap proxy: {corpus['review_concern_overlap_proxy_mean']}",
                f"- Routes: {json.dumps(corpus['route_distribution'], ensure_ascii=False)}",
                f"- Readiness: {json.dumps(corpus['readiness_distribution'], ensure_ascii=False)}",
                f"- Active findings: {json.dumps(corpus['active_finding_counts'], ensure_ascii=False)}",
                "",
                "| Row | Score | Route | Decision | Active findings | Review concerns | Overlap |",
                "| ---: | ---: | --- | --- | --- | --- | ---: |",
            ]
        )
        for case in corpus["cases"]:
            lines.append(
                f"| {case['row_idx']} | {case['score']} | {case['route']} | "
                f"{case.get('decision') or '-'} | "
                f"{', '.join(case['active_findings']) or '-'} | "
                f"{', '.join(case['review_concern_categories']) or '-'} | "
                f"{case['review_concern_overlap_proxy'] if case['review_concern_overlap_proxy'] is not None else '-'} |"
            )
        lines.append("")
    path.write_text("\n".join(lines), encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--corpus", choices=["reviewbench", "peersum", "all"], default="all")
    parser.add_argument("--reviewbench-split", default="iclr")
    parser.add_argument("--limit", type=int, default=10)
    parser.add_argument("--offset", type=int, default=0)
    parser.add_argument("--max-chars", type=int, default=80000)
    parser.add_argument("--timeout", type=float, default=60.0)
    parser.add_argument(
        "--cache-dir",
        default=".openri/benchmark-cache",
        help="Cache Hugging Face row payloads here so repeated smoke benchmarks avoid refetching unchanged rows.",
    )
    parser.add_argument("--refresh-cache", action="store_true", help="Refetch rows even when a cache entry exists.")
    parser.add_argument("--json-out", default="benchmark/peer-review-corpus-benchmark.json")
    parser.add_argument("--md-out", default="benchmark/peer-review-corpus-benchmark.md")
    args = parser.parse_args()

    report = run_peer_review_corpus_benchmark(args)
    json_out = Path(args.json_out)
    md_out = Path(args.md_out)
    json_out.parent.mkdir(parents=True, exist_ok=True)
    md_out.parent.mkdir(parents=True, exist_ok=True)
    json_out.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    write_markdown(report, md_out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
