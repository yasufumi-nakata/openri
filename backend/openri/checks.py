from __future__ import annotations

import math
import re
from bisect import bisect_right
from collections import Counter
from dataclasses import dataclass
from typing import Callable, Optional

from scipy import stats

from . import cues as cue_patterns
from .crossref import lookup_doi
from .models import Evidence, Finding, Severity, Status
from .references import citation_context_audit
from .ruleset_loader import (
    KeywordRuleset,
    Pattern,
    discover_keyword_rulesets,
    load_default_ruleset,
    load_extra_rulesets,
    load_keyword_ruleset,
    merge_patterns,
)

CLAIM_CAUSAL_CUE_RE = cue_patterns.CAUSAL_CUE_RE
CLAIM_CAUSAL_DESIGN_RE = cue_patterns.CAUSAL_DESIGN_RE
CLAIM_CITATION_CUE_RE = cue_patterns.CITATION_CUE_RE
CLAIM_CUE_RE = cue_patterns.CLAIM_CUE_RE
CLAIM_FIGURE_CUE_RE = cue_patterns.FIGURE_CUE_RE
CLAIM_LIMITATION_CUE_RE = cue_patterns.LIMITATION_CUE_RE
CLAIM_NOVELTY_CUE_RE = cue_patterns.NOVELTY_CUE_RE
CLAIM_OVERGENERAL_CUE_RE = cue_patterns.OVERGENERAL_CUE_RE
CLAIM_STATISTIC_CUE_RE = cue_patterns.STATISTIC_CUE_RE

CheckFunction = Callable[[str, dict], Finding]


@dataclass(frozen=True)
class CheckSpec:
    id: str
    title: str
    category: str
    description: str
    maturity: str
    run: CheckFunction


STAT_RE = re.compile(
    r"(?<![A-Za-z0-9_])(?P<test>t|z|F|r|χ2|χ²|χ\^2|chi-?squared?|chi2)\s*"
    r"\(\s*(?P<df1>\d+(?:\.\d+)?)\s*(?:,\s*(?P<df2>\d+(?:\.\d+)?))?\s*\)\s*"
    r"=?\s*(?P<value>-?(?:\d+(?:\.\d+)?|\.\d+))"
    r"(?P<trailer>[\s\S]{0,220}?)(?:p\s*(?P<op><=|>=|<|>|=)\s*(?P<p>0?\.\d+|1(?:\.0+)?|0(?:\.0+)?))",
    re.IGNORECASE,
)

# APA-style z tests are usually reported without degrees of freedom (z = 3.21, p < .001).
Z_STAT_RE = re.compile(
    r"(?<![A-Za-z0-9_])(?P<test>z)\s*=\s*(?P<value>-?(?:\d+(?:\.\d+)?|\.\d+))"
    r"(?P<trailer>[\s\S]{0,220}?)(?:p\s*(?P<op><=|>=|<|>|=)\s*(?P<p>0?\.\d+|1(?:\.0+)?|0(?:\.0+)?))",
    re.IGNORECASE,
)

EFFECT_RE = re.compile(
    r"\b(?P<kind>Cohen'?s?\s*d|ηp?2|eta\s*squared|OR|RR|HR|r|β)\s*=\s*(?P<value>-?\d+(?:\.\d+)?)", re.IGNORECASE
)
CI_RE = re.compile(
    r"\b(?P<level>9[059]%|95\s*percent)\s*CI\s*[\[:(]\s*(?P<low>-?\d+(?:\.\d+)?)\s*,\s*(?P<high>-?\d+(?:\.\d+)?)\s*[\]):]",
    re.IGNORECASE,
)

MEAN_N_RE = re.compile(
    r"\b(?:M|mean)\s*=\s*(?P<mean>-?\d+(?:\.\d+)?)"
    r"(?P<trailer>[\s\S]{0,120}?)\b(?:n|N)\s*=\s*(?P<n>\d+)\b",
    re.IGNORECASE,
)

INTEGER_ITEM_HINT_RE = re.compile(
    r"(likert|integer\s+item|integer\s+scale|integer\s+response|"
    r"\d+-?point\s+(scale|questionnaire|item|response)|"
    r"count\s+data|"
    r"整数項目|リッカート|\d+件法)",
    re.IGNORECASE,
)

DOI_RE = re.compile(r"\b10\.\d{4,9}/[-._;()/:A-Z0-9]+\b", re.IGNORECASE)
INLINE_NUMERIC_CITE_RE = re.compile(r"\[(\d{1,3}(?:\s*[-,]\s*\d{1,3})*)\]")
REFERENCE_HEADING_RE = re.compile(r"^\s*(references|bibliography|参考文献)\s*$", re.IGNORECASE | re.MULTILINE)
NUMBERED_REFERENCE_RE = re.compile(r"^\s*(?:\[(?P<bracket>\d{1,3})\]|(?P<plain>\d{1,3})[.)])\s+", re.MULTILINE)
PLACEHOLDER_REFERENCE_RE = re.compile(
    r"\b(TBD|TODO|citation needed|lorem ipsum|fake|placeholder|example reference|unknown journal)\b|\?\?\?",
    re.IGNORECASE,
)


def _finding(
    check_id: str,
    title: str,
    category: str,
    severity: Severity,
    status: Status,
    score: int,
    message: str,
    recommendation: str,
    evidence: list[Evidence] | None = None,
    tags: list[str] | None = None,
) -> Finding:
    return Finding(
        check_id=check_id,
        title=title,
        category=category,
        severity=severity,
        status=status,
        score=max(0, min(100, score)),
        message=message,
        recommendation=recommendation,
        evidence=evidence or [],
        tags=tags or [],
    )


def _line_number(text: str, start: int, profile: Optional[dict] = None) -> str:
    line_starts = (profile or {}).get("_line_starts")
    if isinstance(line_starts, list) and line_starts:
        return f"line {bisect_right(line_starts, start)}"
    return f"line {text.count(chr(10), 0, start) + 1}"


def _p_value(test: str, value: float, df1: float | None, df2: float | None) -> float | None:
    test_l = test.lower().replace("^", "").replace("²", "2")
    if test_l == "t" and df1 is not None:
        return float(2 * stats.t.sf(abs(value), df1))
    if test_l == "z":
        return float(2 * stats.norm.sf(abs(value)))
    if test_l == "r" and df1 is not None:
        if df1 <= 0:
            return None
        if abs(value) >= 1:
            return 0.0
        t_stat = value * math.sqrt(df1 / (1 - value * value))
        return float(2 * stats.t.sf(abs(t_stat), df1))
    if test_l == "f" and df2 is not None:
        return float(stats.f.sf(value, df1, df2))
    if test_l in {"χ2", "chi-square", "chi-squared", "chisquare", "chisquared", "chi2"}:
        return float(stats.chi2.sf(value, df1))
    return None


def _reported_p_consistent(calculated: float, reported: float, op: str, tolerance: float) -> tuple[bool, bool, bool]:
    if op in {"<", "<="}:
        threshold_flip = not calculated <= reported + tolerance
        materially_different = threshold_flip and reported >= 0.01
        return (not threshold_flip and not materially_different), threshold_flip, materially_different
    if op in {">", ">="}:
        threshold_flip = not calculated >= reported - tolerance
        materially_different = threshold_flip and reported >= 0.01
        return (not threshold_flip and not materially_different), threshold_flip, materially_different
    materially_different = abs(calculated - reported) > tolerance
    reported_passes = reported < 0.05
    calculated_passes = calculated < 0.05
    threshold_flip = reported_passes != calculated_passes
    return (not materially_different and not threshold_flip), threshold_flip, materially_different


def _one_tailed_context(snippet: str) -> bool:
    return bool(re.search(r"one[-\s]?tailed|one[-\s]?sided|片側", snippet, re.IGNORECASE))


def _stat_matches(text: str) -> list[tuple[re.Match, float | None]]:
    """Collect APA-style test statistics with and without degrees of freedom.

    Standalone z reports (no parentheses) are skipped when their reported p was
    already consumed by a df-style match, so the same p is not checked twice.
    """
    matches: list[tuple[re.Match, float | None]] = []
    consumed_p_spans: set[tuple[int, int]] = set()
    for match in STAT_RE.finditer(text):
        matches.append((match, float(match.group("df1"))))
        consumed_p_spans.add(match.span("p"))
    for match in Z_STAT_RE.finditer(text):
        if match.span("p") in consumed_p_spans:
            continue
        matches.append((match, None))
    matches.sort(key=lambda item: item[0].start())
    return matches


def check_statistical_consistency(text: str, profile: dict) -> Finding:
    mismatches: list[Evidence] = []
    checked = 0
    p_tolerance = float(profile.get("strictness_knobs", {}).get("p_tolerance", 0.02))

    for match, df1 in _stat_matches(text):
        checked += 1
        test = match.group("test")
        reported = float(match.group("p"))
        op = match.group("op")
        value = float(match.group("value"))
        groups = match.groupdict()
        df2 = float(groups["df2"]) if groups.get("df2") else None
        calculated = _p_value(test, value, df1, df2)
        if calculated is None or math.isnan(calculated):
            continue
        if _one_tailed_context(match.group(0)) and test.lower() in {"t", "z", "r"}:
            calculated = calculated / 2

        consistent, threshold_flip, materially_different = _reported_p_consistent(calculated, reported, op, p_tolerance)
        if not consistent:
            mismatches.append(
                Evidence(
                    quote=match.group(0).strip(),
                    location=_line_number(text, match.start(), profile),
                    data={
                        "test": test,
                        "statistic": value,
                        "df1": df1,
                        "df2": df2,
                        "reported_p": reported,
                        "reported_operator": op,
                        "calculated_p": round(calculated, 6),
                        "threshold_flip": threshold_flip,
                        "one_tailed_context": _one_tailed_context(match.group(0)),
                    },
                )
            )

    if checked == 0:
        return _finding(
            "statistical_consistency",
            "Statistical consistency",
            "statistics",
            Severity.INFO,
            Status.SKIPPED,
            70,
            "検定統計量とp値の組を検出できませんでした。",
            "t(df), F(df1, df2), χ2(df), r(df), z = value と p 値を標準形式で記載すると自動検査できます。",
            tags=["statcheck"],
        )

    if mismatches:
        return _finding(
            "statistical_consistency",
            "Statistical consistency",
            "statistics",
            Severity.HIGH,
            Status.FAILED,
            max(10, 85 - 25 * len(mismatches)),
            f"{checked}件の検定表記を再計算し、{len(mismatches)}件でp値または有意性判定の不整合を検出しました。",
            "原稿中の検定統計量、自由度、片側/両側検定、丸め、p値表記を再確認してください。",
            mismatches[:8],
            ["statcheck", "p-value"],
        )

    return _finding(
        "statistical_consistency",
        "Statistical consistency",
        "statistics",
        Severity.LOW,
        Status.PASSED,
        100,
        f"{checked}件の検定表記を再計算し、重大な不整合は見つかりませんでした。",
        "表内・複数行・片側検定の代表的なAPA表記も確認しました。効果量/CIは別findingでcoverage blockerとして扱います。",
        tags=["statcheck", "p-value"],
    )


def check_effect_size_ci_coverage(text: str, profile: dict) -> Finding:
    effects = [
        Evidence(
            quote=match.group(0),
            location=_line_number(text, match.start(), profile),
            data={"kind": match.group("kind"), "value": float(match.group("value"))},
        )
        for match in EFFECT_RE.finditer(text)
    ]
    cis = [
        Evidence(
            quote=match.group(0),
            location=_line_number(text, match.start(), profile),
            data={"level": match.group("level"), "low": float(match.group("low")), "high": float(match.group("high"))},
        )
        for match in CI_RE.finditer(text)
    ]
    if effects or cis:
        return _finding(
            "effect_size_ci_coverage",
            "Effect-size and CI coverage",
            "statistics",
            Severity.INFO,
            Status.WARNING,
            76,
            f"{len(effects)}件の効果量と{len(cis)}件の信頼区間を抽出しましたが、整合性再計算は未対応です。",
            "効果量、信頼区間、p値、サンプルサイズの相互整合は統計担当または次段checkで確認してください。",
            (effects + cis)[:10],
            ["statistics", "effect-size", "confidence-interval", "coverage-blocker"],
        )
    return _finding(
        "effect_size_ci_coverage",
        "Effect-size and CI coverage",
        "statistics",
        Severity.INFO,
        Status.SKIPPED,
        72,
        "効果量または信頼区間を検出できませんでした。",
        "査読前には、主要claimに対応する効果量と信頼区間の有無を確認してください。",
        tags=["statistics", "effect-size", "confidence-interval", "coverage-blocker"],
    )


def check_summary_stat_plausibility(text: str, profile: dict) -> Finding:
    implausible: list[Evidence] = []
    detected = 0
    analyzed = 0
    skipped_matches: list[Evidence] = []
    integer_context = bool(INTEGER_ITEM_HINT_RE.search(text))

    for match in MEAN_N_RE.finditer(text):
        detected += 1
        reported_mean = float(match.group("mean"))
        n = int(match.group("n"))
        if n <= 0:
            skipped_matches.append(
                Evidence(
                    quote=match.group(0).strip(),
                    location=_line_number(text, match.start()),
                    data={"reason": "n_not_positive", "n": n},
                )
            )
            continue
        decimals = len(match.group("mean").split(".")[1]) if "." in match.group("mean") else 0
        if decimals == 0:
            skipped_matches.append(
                Evidence(
                    quote=match.group(0).strip(),
                    location=_line_number(text, match.start()),
                    data={"reason": "mean_has_no_decimal_places", "mean": reported_mean, "n": n},
                )
            )
            continue
        analyzed += 1
        total = reported_mean * n
        distance = abs(total - round(total))
        tolerance = 0.5 * (10**-decimals) * n + 1e-9
        if distance > tolerance:
            implausible.append(
                Evidence(
                    quote=match.group(0).strip(),
                    location=_line_number(text, match.start(), profile),
                    data={
                        "mean": reported_mean,
                        "n": n,
                        "mean_times_n": round(total, 6),
                        "nearest_integer": round(total),
                        "distance": round(distance, 6),
                        "tolerance": round(tolerance, 6),
                        "integer_item_hint_in_text": integer_context,
                    },
                )
            )

    if detected == 0:
        return _finding(
            "summary_stat_plausibility",
            "Summary-stat plausibility",
            "statistics",
            Severity.INFO,
            Status.SKIPPED,
            72,
            "平均値とサンプルサイズの組を検出できませんでした。",
            "整数項目の平均値を報告する場合は、M = ..., n = ... のように書くとGRIM系の検査を追加できます。",
            tags=["grim", "summary-statistics"],
        )

    if analyzed == 0:
        return _finding(
            "summary_stat_plausibility",
            "Summary-stat plausibility",
            "statistics",
            Severity.INFO,
            Status.SKIPPED,
            60,
            f"{detected}件の平均値/n表記を検出しましたが、n<=0または小数なしのためGRIM風の再計算対象は0件でした。",
            "整数項目の平均値を検査するには、小数付きのM = ..., n = ...表記と有効なサンプルサイズを確認してください。",
            skipped_matches[:8],
            ["grim", "summary-statistics", "coverage-blocker"],
        )

    if implausible:
        knobs = profile.get("strictness_knobs", {})
        if integer_context:
            return _finding(
                "summary_stat_plausibility",
                "Summary-stat plausibility",
                "statistics",
                Severity.MEDIUM,
                Status.WARNING,
                max(25, 90 - 15 * len(implausible)),
                f"{detected}件の平均値/n表記を検出し、うち{analyzed}件をGRIM風に再計算して、{len(implausible)}件で整数項目仮定のGRIM違反候補を検出しました。",
                "整数項目尺度が明示されているため、平均値、n、丸め規則、サブグループの定義を確認してください。",
                implausible[:8],
                ["grim", "summary-statistics", "integer-item"],
            )
        if not knobs.get("summary_stat_ambiguous_emitted", True):
            return _finding(
                "summary_stat_plausibility",
                "Summary-stat plausibility",
                "statistics",
                Severity.INFO,
                Status.PASSED,
                90,
                f"{detected}件の平均値/n表記を検出し、うち{analyzed}件をGRIM風に再計算しましたが、整数項目ヒントが無いためambiguous-scaleの警告は抑制しました(lenient)。",
                "対象指標が整数項目か連続量かを明示すると、再度strict/standardで再確認しやすくなります。",
                tags=["grim", "summary-statistics", "ambiguous-scale", "suppressed"],
            )
        return _finding(
            "summary_stat_plausibility",
            "Summary-stat plausibility",
            "statistics",
            Severity.INFO,
            Status.WARNING,
            max(55, 90 - 5 * len(implausible)),
            f"{detected}件の平均値/n表記を検出し、うち{analyzed}件をGRIM風に再計算しました。{len(implausible)}件は、整数項目仮定では不整合になります。"
            "整数項目尺度を示すヒントが原稿中に見つからないため、連続量であれば問題ありません。",
            "対象指標が整数項目(リッカート、件数など)か連続量かを明示し、整数項目ならGRIM風の再確認を行ってください。",
            implausible[:8],
            ["grim", "summary-statistics", "ambiguous-scale"],
        )

    return _finding(
        "summary_stat_plausibility",
        "Summary-stat plausibility",
        "statistics",
        Severity.LOW,
        Status.PASSED,
        96,
        f"{detected}件の平均値/n表記を検出し、うち{analyzed}件をGRIM風に再計算しました。不自然さは見つかりませんでした。",
        "標準偏差、群別n、補足表に対する追加検査も検討してください。",
        tags=["grim", "summary-statistics"],
    )


def check_reporting_transparency(text: str, profile: dict) -> Finding:
    lowered = profile.get("_lower_text") or text.lower()
    required = {
        "ethics": ["ethics", "irb", "institutional review board", "informed consent", "倫理", "同意"],
        "data": ["data availability", "available at", "repository", "osf", "zenodo", "figshare", "データ"],
        "code": ["code availability", "github", "gitlab", "source code", "analysis code", "コード"],
        "conflicts": ["conflict of interest", "competing interests", "利益相反"],
        "funding": ["funding", "grant", "supported by", "資金", "助成"],
    }
    missing = [name for name, keys in required.items() if not any(k in lowered for k in keys)]
    knobs = profile.get("strictness_knobs", {})
    warning_at = int(knobs.get("transparency_warning_at", 1))
    medium_at = int(knobs.get("transparency_medium_at", 3))
    evidence = [
        Evidence(
            quote=None,
            location=None,
            data={
                "missing_sections": missing,
                "detected_sections": [k for k in required if k not in missing],
                "thresholds": {"warning_at": warning_at, "medium_at": medium_at},
            },
        )
    ]
    if len(missing) >= medium_at:
        return _finding(
            "reporting_transparency",
            "Reporting transparency",
            "research-integrity",
            Severity.MEDIUM,
            Status.WARNING,
            45,
            "倫理、データ、コード、利益相反、資金の透明性項目に複数の不足があります。",
            "投稿前に、倫理審査/同意、data availability、code availability、COI、funding statementを明示してください。",
            evidence,
            ["transparency", "mdar"],
        )
    if len(missing) >= warning_at:
        return _finding(
            "reporting_transparency",
            "Reporting transparency",
            "research-integrity",
            Severity.LOW,
            Status.WARNING,
            75,
            f"透明性項目の不足候補があります: {', '.join(missing)}。",
            "不足が意図的な場合も、not applicable の明示を推奨します。",
            evidence,
            ["transparency", "mdar"],
        )
    return _finding(
        "reporting_transparency",
        "Reporting transparency",
        "research-integrity",
        Severity.LOW,
        Status.PASSED,
        100,
        "主要な透明性項目が原稿中に検出されました。",
        "項目の存在だけでなく、リンク先の到達性と再現可能性を次段で確認してください。",
        evidence,
        ["transparency", "mdar"],
    )


def _split_reference_section(text: str) -> tuple[str, str]:
    match = REFERENCE_HEADING_RE.search(text)
    if not match:
        return text, ""
    return text[: match.start()], text[match.end() :]


def _expand_numeric_citation_group(group: str) -> list[int]:
    numbers: list[int] = []
    for part in re.split(r"\s*,\s*", group):
        if "-" in part:
            start_raw, end_raw = [item.strip() for item in part.split("-", 1)]
            if not start_raw.isdigit() or not end_raw.isdigit():
                continue
            start = int(start_raw)
            end = int(end_raw)
            if start <= end and end - start <= 50:
                numbers.extend(range(start, end + 1))
        elif part.strip().isdigit():
            numbers.append(int(part.strip()))
    return numbers


def _numbered_reference_ids(reference_text: str) -> list[int]:
    ids: list[int] = []
    for match in NUMBERED_REFERENCE_RE.finditer(reference_text):
        raw = match.group("bracket") or match.group("plain")
        if raw:
            ids.append(int(raw))
    return ids


def _reference_entries(reference_text: str) -> list[str]:
    entries: list[str] = []
    current: list[str] = []
    for line in reference_text.splitlines():
        stripped = line.strip()
        if not stripped:
            if current:
                entries.append(" ".join(current))
                current = []
            continue
        if NUMBERED_REFERENCE_RE.match(stripped) and current:
            entries.append(" ".join(current))
            current = [stripped]
        else:
            current.append(stripped)
    if current:
        entries.append(" ".join(current))
    return entries


def check_citation_integrity(text: str, profile: dict) -> Finding:
    body_text, reference_text = _split_reference_section(text)
    dois = DOI_RE.findall(text)
    fake_dois = [doi for doi in dois if doi.lower().startswith(("10.0000/", "10.1234/", "10.9999/"))]
    numeric_cite_groups = INLINE_NUMERIC_CITE_RE.findall(body_text)
    numeric_cite_numbers = sorted(
        set(number for group in numeric_cite_groups for number in _expand_numeric_citation_group(group))
    )
    has_references = bool(reference_text.strip())
    reference_ids = sorted(set(_numbered_reference_ids(reference_text)))
    reference_entries = _reference_entries(reference_text)
    placeholder_entries = [entry for entry in reference_entries if PLACEHOLDER_REFERENCE_RE.search(entry)]
    evidence = []

    if fake_dois:
        evidence.extend(Evidence(quote=doi, data={"reason": "placeholder-like DOI"}) for doi in fake_dois[:8])
    if placeholder_entries:
        evidence.append(
            Evidence(
                quote=placeholder_entries[0][:220],
                data={"reason": "placeholder-like-reference-entry", "count": len(placeholder_entries)},
            )
        )
    if numeric_cite_groups and not has_references:
        evidence.append(
            Evidence(
                quote=numeric_cite_groups[0],
                data={"reason": "numeric inline citations detected without a references section"},
            )
        )
    if numeric_cite_numbers and has_references and not reference_ids:
        evidence.append(
            Evidence(
                quote=f"[{numeric_cite_groups[0]}]" if numeric_cite_groups else None,
                data={
                    "reason": "numeric inline citations found but numbered reference entries were not detected",
                    "cited_numbers": numeric_cite_numbers[:30],
                    "reference_entry_count": len(reference_entries),
                },
            )
        )
    if numeric_cite_numbers and reference_ids:
        missing_reference_ids = [number for number in numeric_cite_numbers if number not in reference_ids]
        uncited_reference_ids = [number for number in reference_ids if number not in numeric_cite_numbers]
        if missing_reference_ids:
            evidence.append(
                Evidence(
                    quote=f"[{numeric_cite_groups[0]}]" if numeric_cite_groups else None,
                    data={
                        "reason": "in-text numeric citation has no matching numbered reference",
                        "missing_reference_ids": missing_reference_ids[:30],
                        "cited_numbers": numeric_cite_numbers[:30],
                        "numbered_reference_ids": reference_ids[:30],
                    },
                )
            )
        if len(uncited_reference_ids) >= max(3, len(reference_ids) // 2 + 1):
            evidence.append(
                Evidence(
                    quote=None,
                    data={
                        "reason": "many numbered references are not cited in the body",
                        "uncited_reference_ids": uncited_reference_ids[:30],
                        "cited_numbers": numeric_cite_numbers[:30],
                        "numbered_reference_ids": reference_ids[:30],
                    },
                )
            )

    if evidence:
        return _finding(
            "citation_integrity",
            "Citation integrity",
            "references",
            Severity.MEDIUM,
            Status.WARNING,
            max(35, 75 - 8 * len(evidence)),
            "引用・参考文献に不整合、placeholder、または本文中引用と参考文献番号の対応漏れ候補を検出しました。",
            "DOIの実在性、参考文献リスト、本文中引用番号、重要claimを支える引用文脈を確認してください。",
            evidence,
            ["citation", "doi", "reference-linkage"],
        )
    return _finding(
        "citation_integrity",
        "Citation integrity",
        "references",
        Severity.LOW,
        Status.PASSED if dois or has_references or numeric_cite_groups else Status.SKIPPED,
        92 if dois or has_references or numeric_cite_groups else 70,
        "引用の機械的な不整合は検出されませんでした。"
        if dois or has_references or numeric_cite_groups
        else "引用/参考文献セクションを検出できませんでした。",
        "次段ではCrossref/OpenAlex/Semantic Scholar APIで全参考文献の実在性と引用文脈を検証してください。",
        [
            Evidence(
                data={
                    "doi_count": len(dois),
                    "numeric_citation_groups": len(numeric_cite_groups),
                    "numeric_citation_numbers": numeric_cite_numbers[:30],
                    "has_references": has_references,
                    "reference_entry_count": len(reference_entries),
                    "numbered_reference_ids": reference_ids[:30],
                }
            )
        ],
        ["citation", "doi", "reference-linkage"],
    )


def _claim_sentences(text: str, profile: dict) -> list[dict]:
    sentences: list[dict] = []
    for match in re.finditer(r"[^.!?\n。！？]+(?:[.!?。！？]+|\n|$)", text):
        sentence = " ".join(match.group(0).strip().split())
        if len(sentence) < 35:
            continue
        sentences.append(
            {
                "text": sentence,
                "start": match.start(),
                "location": _line_number(text, match.start(), profile),
            }
        )
    return sentences


def _claim_alignment_flags(sentence: str, full_text: str) -> list[str]:
    flags: list[str] = []
    has_statistic = bool(CLAIM_STATISTIC_CUE_RE.search(sentence))
    has_citation = bool(CLAIM_CITATION_CUE_RE.search(sentence))
    has_figure = bool(CLAIM_FIGURE_CUE_RE.search(sentence))
    has_limitation = bool(CLAIM_LIMITATION_CUE_RE.search(sentence))

    if not has_statistic and not has_citation and not has_figure:
        flags.append("claim_without_local_support_marker")
    if re.search(r"\b(?:significant|significantly)\b|有意", sentence, re.IGNORECASE) and not has_statistic:
        flags.append("significance_claim_without_local_statistic")
    if CLAIM_CAUSAL_CUE_RE.search(sentence) and not CLAIM_CAUSAL_DESIGN_RE.search(full_text):
        flags.append("causal_claim_without_explicit_causal_design")
    if CLAIM_NOVELTY_CUE_RE.search(sentence) and not has_citation:
        flags.append("novelty_or_priority_claim_without_local_citation")
    if CLAIM_OVERGENERAL_CUE_RE.search(sentence):
        flags.append("overgeneralized_or_conclusive_language")
    if not has_limitation and re.search(
        r"\b(?:robust|important|groundbreaking|definitive|conclusive|prove)\b|重要|頑健|証明",
        sentence,
        re.IGNORECASE,
    ):
        flags.append("strong_language_without_local_limitation")
    return flags


def check_claim_evidence_alignment(text: str, profile: dict) -> Finding:
    checked = 0
    evidence: list[Evidence] = []
    high_risk_flags = {
        "causal_claim_without_explicit_causal_design",
        "overgeneralized_or_conclusive_language",
        "significance_claim_without_local_statistic",
    }

    for item in _claim_sentences(text, profile):
        sentence = item["text"]
        if not CLAIM_CUE_RE.search(sentence):
            continue
        checked += 1
        flags = _claim_alignment_flags(sentence, text)
        if not flags:
            continue
        support_markers = {
            "local_statistic": bool(CLAIM_STATISTIC_CUE_RE.search(sentence)),
            "local_citation": bool(CLAIM_CITATION_CUE_RE.search(sentence)),
            "local_figure_or_table": bool(CLAIM_FIGURE_CUE_RE.search(sentence)),
            "local_limitation": bool(CLAIM_LIMITATION_CUE_RE.search(sentence)),
        }
        evidence.append(
            Evidence(
                quote=sentence[:320],
                location=item["location"],
                data={
                    "risk_flags": flags,
                    "support_markers": support_markers,
                    "review_action": "claimを支える結果・図表・引用・限界を明示し、証拠を超える表現は弱めてください。",
                },
            )
        )

    if checked == 0:
        return _finding(
            "claim_evidence_alignment",
            "Claim-evidence alignment",
            "manuscript-quality",
            Severity.INFO,
            Status.SKIPPED,
            72,
            "検査対象になる主要claim候補を検出できませんでした。",
            "abstract/results/discussionに主要claim、対応する結果・図表・引用・限界を明示するとclaim単位の査読パケットを作れます。",
            tags=["claim-evidence", "explainability"],
        )

    if evidence:
        observed_flags = {flag for ev in evidence for flag in (ev.data or {}).get("risk_flags", [])}
        severity = Severity.HIGH if observed_flags & high_risk_flags else Severity.MEDIUM
        return _finding(
            "claim_evidence_alignment",
            "Claim-evidence alignment",
            "manuscript-quality",
            severity,
            Status.WARNING,
            max(20, 88 - 10 * len(evidence) - (10 if severity == Severity.HIGH else 0)),
            f"{checked}件のclaim候補を確認し、{len(evidence)}件で局所的な証拠・引用・限界との対応確認が必要です。",
            "AI reviewer/AI editorには、各claimについて支持する結果、図表、引用、限界、代替説明を1対1で確認させてください。",
            evidence[:10],
            ["claim-evidence", "overclaim", "explainability"],
        )

    return _finding(
        "claim_evidence_alignment",
        "Claim-evidence alignment",
        "manuscript-quality",
        Severity.LOW,
        Status.PASSED,
        96,
        f"{checked}件のclaim候補で、局所的な統計・引用・図表・限界マーカーの欠落は検出されませんでした。",
        "マーカーの存在だけでは内容妥当性は保証されないため、AI reviewer packetでclaimごとの文脈確認を続けてください。",
        tags=["claim-evidence", "explainability"],
    )


def check_citation_context(text: str, profile: dict) -> Finding:
    audit = citation_context_audit(text)
    evidence = [Evidence(data=audit)]
    unresolved = audit["unresolved_numeric_citations"]
    unresolved_author_year = audit["unresolved_author_year_citations"]
    placeholders = audit["placeholder_references"]
    unsupported = audit["unsupported_claims"]
    if unresolved or unresolved_author_year or placeholders:
        return _finding(
            "citation_context",
            "Structured reference and citation-context audit",
            "references",
            Severity.HIGH,
            Status.WARNING,
            45,
            "参考文献リスト、本文中引用(番号/著者-年)、placeholder DOIの対応に確認が必要な箇所があります。",
            "本文中引用番号・著者-年引用と参考文献リストを照合し、placeholder DOIや支えの弱いclaimは著者照会または外部DB照合へ回してください。",
            evidence,
            ["citation", "reference-list", "claim-support"],
        )
    if unsupported:
        return _finding(
            "citation_context",
            "Structured reference and citation-context audit",
            "references",
            Severity.MEDIUM,
            Status.WARNING,
            65,
            f"{len(unsupported)}件のclaimで、同一文内の引用・DOI・統計量マーカーが見つかりませんでした。",
            "重要claimごとに、本文中引用・結果・図表・限界記述との対応をreview_packetで確認してください。",
            evidence,
            ["citation", "reference-list", "claim-support"],
        )
    if audit["reference_count"] or audit["inline_citations"]:
        return _finding(
            "citation_context",
            "Structured reference and citation-context audit",
            "references",
            Severity.LOW,
            Status.PASSED,
            92,
            "参考文献リストと本文中引用の基本構造を抽出し、明確な番号不整合は見つかりませんでした。",
            "引用がclaimを本当に支えているかは、review_packetのclaim inventoryを用いてAI reviewer/AI editorが判断前に確認してください。",
            evidence,
            ["citation", "reference-list", "claim-support"],
        )
    return _finding(
        "citation_context",
        "Structured reference and citation-context audit",
        "references",
        Severity.INFO,
        Status.SKIPPED,
        70,
        "参考文献リストまたは本文中引用を抽出できませんでした。",
        "参考文献セクション、本文中引用、DOIを構造化して記載すると、claim-support確認に接続できます。",
        evidence,
        ["citation", "reference-list", "coverage-blocker"],
    )


_SEVERITY_RANK = {"info": 0, "low": 1, "medium": 2, "high": 3, "critical": 4}


def _prompt_injection_patterns() -> list[Pattern]:
    rulesets = []
    default = load_default_ruleset("prompt_injection")
    if default is not None:
        rulesets.append(default)
    rulesets.extend(load_extra_rulesets("OPENRI_PROMPT_INJECTION_RULES"))
    return merge_patterns(rulesets)


def _scan_pattern(text: str, lowered: str, pattern: Pattern, profile: dict) -> list[Evidence]:
    evidence: list[Evidence] = []
    if pattern.type == "phrase":
        needle = pattern.value.lower()
        start = 0
        while True:
            idx = lowered.find(needle, start)
            if idx < 0:
                break
            evidence.append(
                Evidence(
                    quote=text[idx : idx + max(160, len(pattern.value) + 60)],
                    location=_line_number(text, idx, profile),
                    data={
                        "pattern_id": pattern.id,
                        "type": "phrase",
                        "value": pattern.value,
                        "severity": pattern.severity,
                    },
                )
            )
            start = idx + max(1, len(needle))
    elif pattern.type == "regex":
        try:
            regex = re.compile(pattern.value, re.IGNORECASE | re.DOTALL)
        except re.error:
            return evidence
        for match in regex.finditer(text):
            evidence.append(
                Evidence(
                    quote=match.group(0)[:200],
                    location=_line_number(text, match.start(), profile),
                    data={
                        "pattern_id": pattern.id,
                        "type": "regex",
                        "value": pattern.value,
                        "severity": pattern.severity,
                    },
                )
            )
    elif pattern.type == "codepoint":
        try:
            codepoint = int(pattern.value, 16) if pattern.value.startswith("0x") else int(pattern.value)
        except ValueError:
            return evidence
        char = chr(codepoint)
        start = 0
        while True:
            idx = text.find(char, start)
            if idx < 0:
                break
            evidence.append(
                Evidence(
                    quote=None,
                    location=_line_number(text, idx, profile),
                    data={
                        "pattern_id": pattern.id,
                        "type": "codepoint",
                        "codepoint": hex(codepoint),
                        "severity": pattern.severity,
                    },
                )
            )
            start = idx + 1
    return evidence


def check_prompt_injection(text: str, profile: dict) -> Finding:
    patterns = _prompt_injection_patterns()
    lowered = profile.get("_lower_text") or text.lower()
    evidence: list[Evidence] = []
    max_rank = 0

    for pattern in patterns:
        hits = _scan_pattern(text, lowered, pattern, profile)
        if hits:
            max_rank = max(max_rank, _SEVERITY_RANK.get(pattern.severity, 2))
        evidence.extend(hits)

    if evidence:
        severity = (
            Severity.CRITICAL
            if max_rank >= 4
            else Severity.HIGH
            if max_rank >= 3
            else Severity.MEDIUM
            if max_rank >= 2
            else Severity.LOW
        )
        status = Status.FAILED if max_rank >= 3 else Status.WARNING
        score = {Severity.CRITICAL: 5, Severity.HIGH: 20, Severity.MEDIUM: 50, Severity.LOW: 70}[severity]
        return _finding(
            "prompt_injection",
            "Hidden prompt-injection and reviewer manipulation",
            "ai-safety",
            severity,
            status,
            score,
            f"{len(patterns)}件のrule中、{len(evidence)}件の検出があり、最も重いseverityは{severity.value}でした。",
            "PDF/HTML抽出テキスト、不可視テキスト、白色文字、ゼロ幅文字を除去し、AI reviewer/AI editorが安全に処理できる原稿だけを検査対象にしてください。",
            evidence[:12],
            ["prompt-injection", "hidden-text", "yaml-ruleset"],
        )

    return _finding(
        "prompt_injection",
        "Hidden prompt-injection and reviewer manipulation",
        "ai-safety",
        Severity.LOW,
        Status.PASSED,
        100,
        f"{len(patterns)}件のrulesetパターンを走査しましたが、検出はありませんでした。",
        "PDFの座標・色・レイヤー情報に基づく不可視テキスト検査も併用してください(image_integrity_pdfで対応中)。",
        tags=["prompt-injection", "hidden-text", "yaml-ruleset"],
    )


def _shingles(text: str, k: int = 5) -> set[tuple[str, ...]]:
    tokens = re.findall(r"\w+", text.lower())
    if len(tokens) < k:
        return {tuple(tokens)} if tokens else set()
    return {tuple(tokens[i : i + k]) for i in range(len(tokens) - k + 1)}


def _jaccard(a: set, b: set) -> float:
    if not a or not b:
        return 0.0
    inter = len(a & b)
    union = len(a | b)
    return inter / union if union else 0.0


def check_duplicate_or_template_text(text: str, profile: dict) -> Finding:
    knobs = profile.get("strictness_knobs", {})
    vague_repeat_threshold = int(knobs.get("vague_phrase_repeats", 3))

    paragraphs = [p.strip() for p in re.split(r"\n\s*\n", text) if len(p.strip()) > 80]
    normalized = [" ".join(p.lower().split()) for p in paragraphs]
    counts = Counter(normalized)
    exact_repeats = [p for p, c in counts.items() if c > 1]

    fuzzy_pairs: list[tuple[int, int, float]] = []
    shingle_sets = [_shingles(p) for p in paragraphs]
    for i in range(len(paragraphs)):
        for j in range(i + 1, len(paragraphs)):
            if normalized[i] == normalized[j]:
                continue
            sim = _jaccard(shingle_sets[i], shingle_sets[j])
            if sim >= 0.8:
                fuzzy_pairs.append((i, j, round(sim, 3)))

    vague_phrases = [
        "further research is needed",
        "novel and important",
        "statistically significant",
        "robust results",
        "groundbreaking",
    ]
    vague_hits = [phrase for phrase in vague_phrases if lowered_count(text, phrase) >= vague_repeat_threshold]

    evidence: list[Evidence] = []
    if exact_repeats:
        evidence.append(
            Evidence(
                quote=exact_repeats[0][:220],
                data={"reason": "exact-duplicate-paragraph", "count": len(exact_repeats)},
            )
        )
    for i, j, sim in fuzzy_pairs[:5]:
        evidence.append(
            Evidence(
                quote=paragraphs[i][:200],
                data={
                    "reason": "near-duplicate-paragraph",
                    "jaccard": sim,
                    "paired_with_quote": paragraphs[j][:200],
                },
            )
        )
    if vague_hits:
        evidence.append(
            Evidence(
                quote=None,
                data={"reason": "repeated-vague-phrase", "phrases": vague_hits, "threshold": vague_repeat_threshold},
            )
        )

    if exact_repeats or fuzzy_pairs or vague_hits:
        severity = Severity.MEDIUM if (exact_repeats or fuzzy_pairs) else Severity.LOW
        return _finding(
            "template_text",
            "Template or duplicate text",
            "manuscript-quality",
            severity,
            Status.WARNING,
            max(40, 90 - 12 * (len(exact_repeats) + len(fuzzy_pairs)) - 5 * len(vague_hits)),
            "重複段落、近接重複段落、または過度に反復されたテンプレート表現を検出しました。",
            "コピー編集上の重複か、claim/abstract reuseか、テンプレ表現の過剰反復かを確認してください。",
            evidence,
            ["text-quality", "duplicate"],
        )

    return _finding(
        "template_text",
        "Template or duplicate text",
        "manuscript-quality",
        Severity.LOW,
        Status.PASSED,
        96,
        "明確な重複段落、近接重複、テンプレート表現の過剰反復は検出されませんでした。",
        "分野別の定型文を許容する場合はルールセットを調整してください。",
        tags=["text-quality"],
    )


def lowered_count(text: str, phrase: str) -> int:
    return text.lower().count(phrase.lower())


_SEVERITY_BY_NAME = {
    "info": Severity.INFO,
    "low": Severity.LOW,
    "medium": Severity.MEDIUM,
    "high": Severity.HIGH,
    "critical": Severity.CRITICAL,
}


def check_image_integrity(text: str, profile: dict) -> Finding:
    inspection = profile.get("image_inspection") or {}
    if inspection:
        if not inspection.get("available"):
            return _finding(
                "image_integrity",
                "Image integrity",
                "image-integrity",
                Severity.INFO,
                Status.SKIPPED,
                65,
                f"画像検査を実行できませんでした: {inspection.get('reason', 'unknown')}",
                "Pillowを含む環境で再実行し、画像ファイルを直接アップロードしてください。",
                [Evidence(data=inspection)],
                ["image-integrity", "coverage-blocker"],
            )
        hits = inspection.get("findings", []) or []
        if hits:
            severity = Severity.MEDIUM if any(hit.get("severity") == "medium" for hit in hits) else Severity.LOW
            return _finding(
                "image_integrity",
                "Image integrity",
                "image-integrity",
                severity,
                Status.WARNING,
                max(40, 85 - 10 * len(hits)),
                f"画像メタデータと画素ブロックを確認し、{len(hits)}件のreviewer task候補を検出しました。",
                "EXIF、圧縮履歴、重複領域候補は不正断定ではなく、元画像・処理履歴・図説明との照合タスクとして扱ってください。",
                [Evidence(data=item) for item in hits[:10]],
                ["image-integrity", "metadata", "duplicate-region"],
            )
        return _finding(
            "image_integrity",
            "Image integrity",
            "image-integrity",
            Severity.LOW,
            Status.PASSED,
            95,
            "画像メタデータと画素ブロックの簡易検査で、明確な重複領域候補は見つかりませんでした。",
            "高リスク原稿では、専門ツールによるELA、レイヤー、raw画像履歴の追加確認を推奨します。",
            [Evidence(data=inspection)],
            ["image-integrity", "metadata"],
        )

    pdf_inspection = profile.get("pdf_inspection") or {}
    if pdf_inspection.get("image_count"):
        return _finding(
            "image_integrity",
            "Image integrity",
            "image-integrity",
            Severity.INFO,
            Status.WARNING,
            68,
            f"PDF内に{pdf_inspection.get('image_count')}件の画像候補がありますが、個別画像抽出検査は未完了です。",
            "PDFから図画像を抽出し、EXIF、重複領域、圧縮履歴、図本文参照との整合を確認してください。",
            [
                Evidence(
                    data={"pdf_image_count": pdf_inspection.get("image_count"), "implemented_for_pdf_images": False}
                )
            ],
            ["image-integrity", "pdf-image", "coverage-blocker"],
        )

    figure_mentions = len(re.findall(r"(?:\b(?:fig\.?|figure)|図)\s*\d+", text, re.IGNORECASE))
    if figure_mentions == 0:
        return _finding(
            "image_integrity",
            "Image integrity",
            "image-integrity",
            Severity.INFO,
            Status.SKIPPED,
            70,
            "図表参照を検出できませんでした。",
            "画像ファイルを添付できるようにすると、複製・不自然な圧縮・メタデータ検査を追加できます。",
            tags=["image-integrity"],
        )
    knobs = profile.get("strictness_knobs", {})
    severity_name = str(knobs.get("image_severity", "medium")).lower()
    severity = _SEVERITY_BY_NAME.get(severity_name, Severity.MEDIUM)
    score = {"info": 80, "low": 70, "medium": 60, "high": 45, "critical": 30}.get(severity_name, 60)
    return _finding(
        "image_integrity",
        "Image integrity",
        "image-integrity",
        severity,
        Status.WARNING,
        score,
        f"本文中に{figure_mentions}件の図参照を検出しましたが、画像ファイル自体は未提出です。",
        "画像ファイルまたはPDFをアップロードし、EXIF、圧縮アーティファクト、重複領域候補、図本文参照の整合を確認してください。",
        [
            Evidence(
                data={
                    "figure_mentions": figure_mentions,
                    "implemented_for_direct_image_files": True,
                    "severity_from_strictness": severity_name,
                }
            )
        ],
        ["image-integrity", "roadmap"],
    )


def check_doi_existence(text: str, profile: dict) -> Finding:
    if not profile.get("enable_network"):
        return _finding(
            "doi_existence",
            "DOI existence (Crossref)",
            "references",
            Severity.INFO,
            Status.SKIPPED,
            70,
            "Crossref問い合わせはネットワーク不要モードで無効化されています(--network で有効化)。",
            "CIで参考文献の実在性を確認したい場合は OPENRI_NETWORK=1 を設定するか、CLIで --network を指定してください。",
            tags=["citation", "doi", "crossref", "network"],
        )
    dois = list(dict.fromkeys(DOI_RE.findall(text)))
    if not dois:
        return _finding(
            "doi_existence",
            "DOI existence (Crossref)",
            "references",
            Severity.INFO,
            Status.SKIPPED,
            72,
            "DOIを検出できませんでした。",
            "参考文献にDOIを付与すると、Crossrefでの実在性検査が可能になります。",
            tags=["citation", "doi", "crossref"],
        )
    max_dois = 12
    checked_dois = dois[:max_dois]
    unchecked_dois = dois[max_dois:]
    lookups = [lookup_doi(doi) for doi in checked_dois]
    missing = [r for r in lookups if r["status"] == "missing"]
    errors = [r for r in lookups if r["status"] in {"error", "http_error", "cache_miss"}]
    found = [r for r in lookups if r["status"] == "found"]
    evidence = [Evidence(quote=r["doi"], data=r) for r in (missing + errors + found)[:max_dois]]
    if unchecked_dois:
        evidence.append(
            Evidence(
                data={
                    "reason": "doi_lookup_truncated",
                    "checked_count": len(checked_dois),
                    "total_count": len(dois),
                    "unchecked_count": len(unchecked_dois),
                    "unchecked_dois": unchecked_dois[:20],
                }
            )
        )

    if missing:
        return _finding(
            "doi_existence",
            "DOI existence (Crossref)",
            "references",
            Severity.HIGH,
            Status.FAILED,
            max(15, 80 - 15 * len(missing)),
            f"{len(dois)}件のDOIのうち最初の{len(checked_dois)}件を確認し、{len(missing)}件がCrossrefで未登録でした。未確認DOIは{len(unchecked_dois)}件です。",
            "幻覚引用または誤記の可能性があります。DOIまたは引用先メタデータを確認してください。",
            evidence,
            ["citation", "doi", "crossref"] + (["coverage-blocker"] if unchecked_dois else []),
        )
    if errors and not found:
        return _finding(
            "doi_existence",
            "DOI existence (Crossref)",
            "references",
            Severity.MEDIUM,
            Status.WARNING,
            55,
            f"{len(dois)}件のDOIのうち最初の{len(checked_dois)}件を問い合わせましたが、すべてネットワークエラーで失敗しました。未確認DOIは{len(unchecked_dois)}件です。",
            "ネットワーク接続またはCrossref APIの可用性を確認してください。",
            evidence,
            ["citation", "doi", "crossref", "network-error"] + (["coverage-blocker"] if unchecked_dois else []),
        )
    if unchecked_dois:
        return _finding(
            "doi_existence",
            "DOI existence (Crossref)",
            "references",
            Severity.INFO,
            Status.WARNING,
            70,
            f"{len(dois)}件のDOIのうち最初の{len(checked_dois)}件をCrossrefで確認しました。残り{len(unchecked_dois)}件は未検証です。",
            "長い参考文献リストは未検証DOIをcoverage blockerとして残し、追加バッチまたは外部DB照合で確認してください。",
            evidence,
            ["citation", "doi", "crossref", "coverage-blocker"],
        )
    return _finding(
        "doi_existence",
        "DOI existence (Crossref)",
        "references",
        Severity.LOW,
        Status.PASSED,
        95,
        f"{len(dois)}件のDOIのうち{len(found)}件をCrossrefで確認しました(残り{len(errors)}件はエラー)。",
        "引用文脈の検証(本文中のclaimとの整合)は別途LLM/人手で実施してください。",
        evidence,
        ["citation", "doi", "crossref"],
    )


def _scan_keyword_ruleset(text: str, ruleset: KeywordRuleset, lowered: Optional[str] = None) -> dict:
    lowered = lowered or text.lower()
    detected: list[dict] = []
    missing: list[dict] = []
    not_applicable: list[dict] = []
    for item in ruleset.items:
        matched = next((kw for kw in item.keywords if kw and kw in lowered), None)
        if matched:
            idx = lowered.find(matched)
            window = lowered[max(0, idx - 80) : idx + len(matched) + 120]
            if re.search(r"\b(?:not applicable|n/?a|not relevant)\b|該当なし|対象外", window, re.IGNORECASE):
                not_applicable.append(
                    {
                        "id": item.id,
                        "label": item.label,
                        "matched_keyword": matched,
                        "policy": item.not_applicable_policy,
                        "required_evidence": list(item.required_evidence),
                    }
                )
            else:
                detected.append(
                    {
                        "id": item.id,
                        "label": item.label,
                        "matched_keyword": matched,
                        "required_evidence": list(item.required_evidence),
                        "section_preference": list(item.section_preference),
                        "reference_url": item.reference_url,
                    }
                )
        else:
            missing.append(
                {
                    "id": item.id,
                    "label": item.label,
                    "severity": item.severity,
                    "required_evidence": list(item.required_evidence),
                    "section_preference": list(item.section_preference),
                    "reference_url": item.reference_url,
                }
            )
    return {
        "id": ruleset.id,
        "name": ruleset.name,
        "total": len(ruleset.items),
        "detected": detected,
        "not_applicable": not_applicable,
        "missing": missing,
    }


def check_ruleset_coverage(text: str, profile: dict) -> Finding:
    activated = list(profile.get("activated_rulesets") or [])
    if not activated:
        return _finding(
            "ruleset_coverage",
            "Ruleset coverage (CONSORT/PRISMA/MDAR-strict)",
            "research-integrity",
            Severity.INFO,
            Status.SKIPPED,
            72,
            "分野別rulesetは指定されていません(--ruleset consort prisma など)。",
            "分野が決まっている原稿では、CONSORT/PRISMA/MDAR-strict などの ruleset を有効化してください。",
            tags=["ruleset", "field-specific"],
        )
    available = discover_keyword_rulesets()
    summaries: list[dict] = []
    total_missing = 0
    total_items = 0
    unknown: list[str] = []
    for ruleset_id in activated:
        path = available.get(ruleset_id)
        if path is None:
            unknown.append(ruleset_id)
            continue
        try:
            ruleset = load_keyword_ruleset(path)
        except RuntimeError as exc:
            unknown.append(f"{ruleset_id} ({exc})")
            continue
        summary = _scan_keyword_ruleset(text, ruleset, profile.get("_lower_text"))
        summaries.append(summary)
        total_items += summary["total"]
        total_missing += len(summary["missing"])

    evidence = [Evidence(data={"unknown_rulesets": unknown})] if unknown else []
    evidence.extend(Evidence(data=summary) for summary in summaries)

    if not summaries:
        return _finding(
            "ruleset_coverage",
            "Ruleset coverage (CONSORT/PRISMA/MDAR-strict)",
            "research-integrity",
            Severity.MEDIUM,
            Status.WARNING,
            50,
            f"指定された ruleset {unknown} は見つかりませんでした。",
            "openri/rulesets/ 配下に YAML を配置するか、--ruleset 引数を見直してください。",
            evidence,
            ["ruleset", "field-specific"],
        )

    coverage_ratio = (total_items - total_missing) / total_items if total_items else 1.0
    if total_missing == 0:
        return _finding(
            "ruleset_coverage",
            "Ruleset coverage (CONSORT/PRISMA/MDAR-strict)",
            "research-integrity",
            Severity.LOW,
            Status.PASSED,
            min(100, 80 + int(coverage_ratio * 20)),
            f"{len(summaries)}件のrulesetで、合計{total_items}項目すべてに対応キーワードを検出しました。",
            "キーワードの存在=記載完備ではないため、各項目の内容をAI reviewer/AI editorの判断入力として確認してください。",
            evidence,
            ["ruleset", "field-specific"],
        )
    severity = Severity.HIGH if coverage_ratio < 0.6 else Severity.MEDIUM if coverage_ratio < 0.85 else Severity.LOW
    status = Status.WARNING
    score = max(15, int(coverage_ratio * 90))
    return _finding(
        "ruleset_coverage",
        "Ruleset coverage (CONSORT/PRISMA/MDAR-strict)",
        "research-integrity",
        severity,
        status,
        score,
        f"{len(summaries)}件のrulesetで、{total_items}項目中{total_missing}項目に対応キーワードがありませんでした(coverage={coverage_ratio:.0%})。",
        "missing項目は記載漏れ候補です。記載済みでもキーワードが一致しないことがあるため、各項目を確認してください。",
        evidence,
        ["ruleset", "field-specific"],
    )


def check_pdf_hidden_text(text: str, profile: dict) -> Finding:
    inspection = profile.get("pdf_inspection") or {}
    if not inspection:
        return _finding(
            "pdf_hidden_text",
            "PDF hidden text (coords, font size, color)",
            "ai-safety",
            Severity.INFO,
            Status.SKIPPED,
            72,
            "PDF不可視テキスト検査はCLIでPDFを直接渡したときのみ実行されます。",
            "openri check manuscript.pdf を使うと、白色文字・極小フォント・ページ外座標などを検査します。",
            tags=["pdf", "hidden-text"],
        )
    if not inspection.get("available", True):
        return _finding(
            "pdf_hidden_text",
            "PDF hidden text and active content",
            "ai-safety",
            Severity.INFO,
            Status.SKIPPED,
            55,
            f"PDF不可視テキスト検査を実行できませんでした: {inspection.get('reason', 'unknown')}",
            "pdfplumberを含む環境(pip install 'openri[pdf]')で再実行してください。未実行の不可視テキスト検査はpassedではなくcoverage blockerとして扱います。",
            [Evidence(data=inspection)],
            ["pdf", "hidden-text", "coverage-blocker"],
        )
    hits = inspection.get("hidden_text", []) or []
    document_risks = inspection.get("document_risks", []) or []
    if not hits and not document_risks:
        return _finding(
            "pdf_hidden_text",
            "PDF hidden text and active content",
            "ai-safety",
            Severity.LOW,
            Status.PASSED,
            96,
            f"PDF {inspection.get('page_count', '?')} ページを検査し、不可視テキストやactive content候補は検出されませんでした。",
            "スキャンPDFや画像内文字はOCRが必要なcoverage blockerとして別途確認してください。",
            tags=["pdf", "hidden-text"],
        )
    combined = [*hits, *document_risks]
    worst_name = max(
        (str(item.get("severity", "high")).lower() for item in combined),
        key=lambda name: _SEVERITY_RANK.get(name, _SEVERITY_RANK["high"]),
        default="high",
    )
    max_severity = _SEVERITY_BY_NAME.get(worst_name, Severity.HIGH)
    evidence = [
        Evidence(
            quote=(h.get("text") or "")[:200] or None,
            location=f"page {h.get('page', '?')}",
            data=h,
        )
        for h in combined[:12]
    ]
    return _finding(
        "pdf_hidden_text",
        "PDF hidden text and active content",
        "ai-safety",
        max_severity,
        Status.FAILED if max_severity in {Severity.HIGH, Severity.CRITICAL} else Status.WARNING,
        max(15, 70 - 8 * len(combined)),
        f"PDF {inspection.get('page_count', '?')} ページから {len(hits)} 件の不可視/極小/ページ外テキストと {len(document_risks)} 件のPDF構造リスクを検出しました。",
        "白色文字・極小フォント・ページ外配置、注釈、添付、JavaScript、OCR要PDFはLLM査読操作や検査漏れに使われ得ます。著者に削除、再生成、OCR付き提出、元ファイル確認を依頼してください。",
        evidence,
        ["pdf", "hidden-text", "prompt-injection", "active-content"],
    )


CHECKS: list[CheckSpec] = [
    CheckSpec(
        "statistical_consistency",
        "Statistical consistency",
        "statistics",
        "t/F/χ2/r/z検定表記(z は自由度なしの z = value 形式も対応)からp値を再計算し、有意性判定の反転や大きなズレを検出します。",
        "stable",
        check_statistical_consistency,
    ),
    CheckSpec(
        "summary_stat_plausibility",
        "Summary-stat plausibility",
        "statistics",
        "平均値とサンプルサイズから、整数項目の平均として不自然な値をGRIM風に検出します。",
        "beta",
        check_summary_stat_plausibility,
    ),
    CheckSpec(
        "effect_size_ci_coverage",
        "Effect-size and CI coverage",
        "statistics",
        "効果量と信頼区間を抽出し、未検査の相互整合をcoverage blockerとして残します。",
        "beta",
        check_effect_size_ci_coverage,
    ),
    CheckSpec(
        "reporting_transparency",
        "Reporting transparency",
        "research-integrity",
        "倫理、データ、コード、利益相反、資金の透明性項目の存在を検査します。",
        "stable",
        check_reporting_transparency,
    ),
    CheckSpec(
        "citation_integrity",
        "Citation integrity",
        "references",
        "DOI、本文中引用、参考文献セクションの機械的不整合を検出します。",
        "beta",
        check_citation_integrity,
    ),
    CheckSpec(
        "citation_context",
        "Structured reference and citation-context audit",
        "references",
        "参考文献リスト、本文中引用、claimの支えを構造化してreview_packetへ渡します。",
        "beta",
        check_citation_context,
    ),
    CheckSpec(
        "claim_evidence_alignment",
        "Claim-evidence alignment",
        "manuscript-quality",
        "主要claim候補が局所的な統計、引用、図表、限界記述で支えられているかを検査します。",
        "beta",
        check_claim_evidence_alignment,
    ),
    CheckSpec(
        "prompt_injection",
        "Hidden prompt-injection and reviewer manipulation",
        "ai-safety",
        "LLM査読を操作し得る隠し指示、不可視文字、隠しCSSを検出します。",
        "stable",
        check_prompt_injection,
    ),
    CheckSpec(
        "template_text",
        "Template or duplicate text",
        "manuscript-quality",
        "重複段落やテンプレート表現の過剰反復を検出します。",
        "beta",
        check_duplicate_or_template_text,
    ),
    CheckSpec(
        "image_integrity",
        "Image integrity",
        "image-integrity",
        "画像ファイルまたはPDF内画像候補について、EXIF、圧縮形式、重複領域候補、図参照の整合を検査します。",
        "experimental",
        check_image_integrity,
    ),
    CheckSpec(
        "doi_existence",
        "DOI existence (Crossref)",
        "references",
        "Crossref APIで本文中のDOIの実在性を確認します。--network 指定時のみ走行。",
        "experimental",
        check_doi_existence,
    ),
    CheckSpec(
        "ruleset_coverage",
        "Ruleset coverage",
        "research-integrity",
        "分野別ruleset(CONSORT/PRISMA/MDAR-strictなど)の項目キーワードを原稿で照合します。",
        "beta",
        check_ruleset_coverage,
    ),
    CheckSpec(
        "pdf_hidden_text",
        "PDF hidden text",
        "ai-safety",
        "PDFの座標/フォント色/フォントサイズを使い、不可視テキストやページ外配置を検出します(CLIでPDFを直接渡したときのみ)。",
        "experimental",
        check_pdf_hidden_text,
    ),
]
