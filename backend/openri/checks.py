from __future__ import annotations

import math
import re
from collections import Counter
from dataclasses import dataclass
from typing import Callable

from scipy import stats

from .crossref import lookup_doi
from .models import Evidence, Finding, Severity, Status
from .ruleset_loader import (
    KeywordRuleset,
    Pattern,
    discover_keyword_rulesets,
    load_default_ruleset,
    load_extra_rulesets,
    load_keyword_ruleset,
    merge_patterns,
)


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
    r"(?P<test>t|z|F|χ2|χ\^2|chi-?square|chi2)\s*"
    r"\(\s*(?P<df1>\d+(?:\.\d+)?)\s*(?:,\s*(?P<df2>\d+(?:\.\d+)?))?\s*\)\s*"
    r"=\s*(?P<value>-?\d+(?:\.\d+)?)"
    r"(?P<trailer>[\s\S]{0,160}?)(?:p\s*(?P<op><=|>=|<|>|=)\s*(?P<p>0?\.\d+|1(?:\.0+)?|0(?:\.0+)?))",
    re.IGNORECASE,
)

MEAN_N_RE = re.compile(
    r"(?:M|mean)\s*=\s*(?P<mean>-?\d+(?:\.\d+)?)"
    r"(?P<trailer>[\s\S]{0,120}?)(?:n|N)\s*=\s*(?P<n>\d+)",
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


def _line_number(text: str, start: int) -> str:
    return f"line {text.count(chr(10), 0, start) + 1}"


def _p_value(test: str, value: float, df1: float, df2: float | None) -> float | None:
    test_l = test.lower().replace("^", "")
    if test_l == "t":
        return float(2 * stats.t.sf(abs(value), df1))
    if test_l == "z":
        return float(2 * stats.norm.sf(abs(value)))
    if test_l == "f" and df2 is not None:
        return float(stats.f.sf(value, df1, df2))
    if test_l in {"χ2", "chi-square", "chisquare", "chi2"}:
        return float(stats.chi2.sf(value, df1))
    return None


def check_statistical_consistency(text: str, profile: dict) -> Finding:
    mismatches: list[Evidence] = []
    checked = 0
    p_tolerance = float(profile.get("strictness_knobs", {}).get("p_tolerance", 0.02))

    for match in STAT_RE.finditer(text):
        checked += 1
        test = match.group("test")
        reported = float(match.group("p"))
        op = match.group("op")
        value = float(match.group("value"))
        df1 = float(match.group("df1"))
        df2 = float(match.group("df2")) if match.group("df2") else None
        calculated = _p_value(test, value, df1, df2)
        if calculated is None or math.isnan(calculated):
            continue

        reported_passes = reported < 0.05 if op in {"<", "<=", "="} else reported > 0.05
        calculated_passes = calculated < 0.05
        materially_different = abs(calculated - reported) > p_tolerance
        threshold_flip = reported_passes != calculated_passes
        if threshold_flip or materially_different:
            mismatches.append(
                Evidence(
                    quote=match.group(0).strip(),
                    location=_line_number(text, match.start()),
                    data={
                        "test": test,
                        "statistic": value,
                        "df1": df1,
                        "df2": df2,
                        "reported_p": reported,
                        "reported_operator": op,
                        "calculated_p": round(calculated, 6),
                        "threshold_flip": threshold_flip,
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
            "t(df), F(df1, df2), χ2(df), z(df) と p 値を標準形式で記載すると自動検査できます。",
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
        "検出対象外の統計量や補足表については、追加の表形式チェックを推奨します。",
        tags=["statcheck", "p-value"],
    )


def check_summary_stat_plausibility(text: str, profile: dict) -> Finding:
    implausible: list[Evidence] = []
    checked = 0
    integer_context = bool(INTEGER_ITEM_HINT_RE.search(text))

    for match in MEAN_N_RE.finditer(text):
        checked += 1
        reported_mean = float(match.group("mean"))
        n = int(match.group("n"))
        if n <= 0:
            continue
        decimals = len(match.group("mean").split(".")[1]) if "." in match.group("mean") else 0
        if decimals == 0:
            continue
        total = reported_mean * n
        distance = abs(total - round(total))
        tolerance = 0.5 * (10 ** -decimals) * n + 1e-9
        if distance > tolerance:
            implausible.append(
                Evidence(
                    quote=match.group(0).strip(),
                    location=_line_number(text, match.start()),
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

    if checked == 0:
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
                f"{checked}件の平均値/n表記を確認し、{len(implausible)}件で整数項目仮定のGRIM違反候補を検出しました。",
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
                f"{checked}件の平均値/n表記を確認しましたが、整数項目ヒントが無いためambiguous-scaleの警告は抑制しました(lenient)。",
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
            f"{checked}件の平均値/n表記のうち{len(implausible)}件は、整数項目仮定では不整合になります。"
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
        f"{checked}件の平均値/n表記で、GRIM風の不自然さは見つかりませんでした。",
        "標準偏差、群別n、補足表に対する追加検査も検討してください。",
        tags=["grim", "summary-statistics"],
    )


def check_reporting_transparency(text: str, profile: dict) -> Finding:
    lowered = text.lower()
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


def check_citation_integrity(text: str, profile: dict) -> Finding:
    dois = DOI_RE.findall(text)
    fake_dois = [doi for doi in dois if doi.lower().startswith(("10.0000/", "10.1234/", "10.9999/"))]
    numeric_cites = INLINE_NUMERIC_CITE_RE.findall(text)
    has_references = bool(re.search(r"\n\s*(references|bibliography|参考文献)\s*\n", text, re.IGNORECASE))
    evidence = []
    if fake_dois:
        evidence.extend(Evidence(quote=doi, data={"reason": "placeholder-like DOI"}) for doi in fake_dois[:8])
    if numeric_cites and not has_references:
        evidence.append(
            Evidence(
                quote=numeric_cites[0],
                data={"reason": "numeric inline citations detected without a references section"},
            )
        )
    if evidence:
        return _finding(
            "citation_integrity",
            "Citation integrity",
            "references",
            Severity.MEDIUM,
            Status.WARNING,
            55,
            "引用・参考文献に不整合またはplaceholderらしい表記を検出しました。",
            "DOIの実在性、参考文献リスト、本文中引用との対応をCrossref等で確認してください。",
            evidence,
            ["citation", "doi"],
        )
    return _finding(
        "citation_integrity",
        "Citation integrity",
        "references",
        Severity.LOW,
        Status.PASSED if dois or has_references else Status.SKIPPED,
        90 if dois or has_references else 70,
        "引用の機械的な不整合は検出されませんでした。" if dois or has_references else "引用/参考文献セクションを検出できませんでした。",
        "次段ではCrossref/OpenAlex/Semantic Scholar APIで全参考文献の実在性と引用文脈を検証してください。",
        [Evidence(data={"doi_count": len(dois), "numeric_citation_groups": len(numeric_cites), "has_references": has_references})],
        ["citation", "doi"],
    )


_SEVERITY_RANK = {"info": 0, "low": 1, "medium": 2, "high": 3, "critical": 4}


def _prompt_injection_patterns() -> list[Pattern]:
    rulesets = []
    default = load_default_ruleset("prompt_injection")
    if default is not None:
        rulesets.append(default)
    rulesets.extend(load_extra_rulesets("OPENRI_PROMPT_INJECTION_RULES"))
    return merge_patterns(rulesets)


def _scan_pattern(text: str, lowered: str, pattern: Pattern) -> list[Evidence]:
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
                    location=_line_number(text, idx),
                    data={"pattern_id": pattern.id, "type": "phrase", "value": pattern.value, "severity": pattern.severity},
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
                    location=_line_number(text, match.start()),
                    data={"pattern_id": pattern.id, "type": "regex", "value": pattern.value, "severity": pattern.severity},
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
                    location=_line_number(text, idx),
                    data={"pattern_id": pattern.id, "type": "codepoint", "codepoint": hex(codepoint), "severity": pattern.severity},
                )
            )
            start = idx + 1
    return evidence


def check_prompt_injection(text: str, profile: dict) -> Finding:
    patterns = _prompt_injection_patterns()
    lowered = text.lower()
    evidence: list[Evidence] = []
    max_rank = 0

    for pattern in patterns:
        hits = _scan_pattern(text, lowered, pattern)
        if hits:
            max_rank = max(max_rank, _SEVERITY_RANK.get(pattern.severity, 2))
        evidence.extend(hits)

    if evidence:
        severity = (
            Severity.CRITICAL if max_rank >= 4
            else Severity.HIGH if max_rank >= 3
            else Severity.MEDIUM if max_rank >= 2
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
            "PDF/HTML抽出テキスト、不可視テキスト、白色文字、ゼロ幅文字を除去し、人間が確認できる原稿だけを検査対象にしてください。",
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


def check_image_integrity_placeholder(text: str, profile: dict) -> Finding:
    figure_mentions = len(re.findall(r"\b(fig\.?|figure|図)\s*\d+", text, re.IGNORECASE))
    if figure_mentions == 0:
        return _finding(
            "image_integrity_placeholder",
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
        "image_integrity_placeholder",
        "Image integrity",
        "image-integrity",
        severity,
        Status.WARNING,
        score,
        f"本文中に{figure_mentions}件の図参照を検出しましたが、この初期版では画像そのものは未検査です。",
        "次段で画像アップロード、EXIF/圧縮アーティファクト、類似領域、切り貼り検出を追加してください。",
        [Evidence(data={"figure_mentions": figure_mentions, "implemented": False, "severity_from_strictness": severity_name})],
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
    lookups = [lookup_doi(doi) for doi in dois[:max_dois]]
    missing = [r for r in lookups if r["status"] == "missing"]
    errors = [r for r in lookups if r["status"] in {"error", "http_error"}]
    found = [r for r in lookups if r["status"] == "found"]
    evidence = [Evidence(quote=r["doi"], data=r) for r in (missing + errors + found)[:max_dois]]

    if missing:
        return _finding(
            "doi_existence",
            "DOI existence (Crossref)",
            "references",
            Severity.HIGH,
            Status.FAILED,
            max(15, 80 - 15 * len(missing)),
            f"{len(dois)}件のDOIのうち{len(missing)}件がCrossrefで未登録でした。",
            "幻覚引用または誤記の可能性があります。DOIまたは引用先メタデータを確認してください。",
            evidence,
            ["citation", "doi", "crossref"],
        )
    if errors and not found:
        return _finding(
            "doi_existence",
            "DOI existence (Crossref)",
            "references",
            Severity.MEDIUM,
            Status.WARNING,
            55,
            f"{len(dois)}件のDOI問い合わせがすべてネットワークエラーで失敗しました。",
            "ネットワーク接続またはCrossref APIの可用性を確認してください。",
            evidence,
            ["citation", "doi", "crossref", "network-error"],
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


def _scan_keyword_ruleset(text: str, ruleset: KeywordRuleset) -> dict:
    lowered = text.lower()
    detected: list[str] = []
    missing: list[dict] = []
    for item in ruleset.items:
        matched = next((kw for kw in item.keywords if kw and kw in lowered), None)
        if matched:
            detected.append(item.id)
        else:
            missing.append({"id": item.id, "label": item.label, "severity": item.severity})
    return {
        "id": ruleset.id,
        "name": ruleset.name,
        "total": len(ruleset.items),
        "detected": detected,
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
        summary = _scan_keyword_ruleset(text, ruleset)
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
            "キーワードの存在=記載完備ではないため、各項目の内容を人間が確認してください。",
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
    hits = inspection.get("hidden_text", []) or []
    if not hits:
        return _finding(
            "pdf_hidden_text",
            "PDF hidden text (coords, font size, color)",
            "ai-safety",
            Severity.LOW,
            Status.PASSED,
            96,
            f"PDF {inspection.get('page_count', '?')} ページを検査し、不可視テキストは検出されませんでした。",
            "PDFの埋め込みフォントやJavaScriptなど、座標・色以外のチャネルは別途確認してください。",
            tags=["pdf", "hidden-text"],
        )
    severity_rank = {"low": Severity.LOW, "medium": Severity.MEDIUM, "high": Severity.HIGH}
    max_severity = max((severity_rank.get(h.get("severity", "high"), Severity.HIGH) for h in hits), default=Severity.HIGH)
    evidence = [
        Evidence(
            quote=(h.get("text") or "")[:200] or None,
            location=f"page {h.get('page', '?')}",
            data=h,
        )
        for h in hits[:12]
    ]
    return _finding(
        "pdf_hidden_text",
        "PDF hidden text (coords, font size, color)",
        "ai-safety",
        max_severity,
        Status.FAILED if max_severity in {Severity.HIGH, Severity.CRITICAL} else Status.WARNING,
        max(15, 70 - 8 * len(hits)),
        f"PDF {inspection.get('page_count', '?')} ページから {len(hits)} 件の不可視/極小/ページ外テキストを検出しました。",
        "白色文字・極小フォント・ページ外配置はLLM査読操作や隠し指示に使われ得ます。著者に削除と再生成を依頼してください。",
        evidence,
        ["pdf", "hidden-text", "prompt-injection"],
    )


CHECKS: list[CheckSpec] = [
    CheckSpec(
        "statistical_consistency",
        "Statistical consistency",
        "statistics",
        "t/F/χ2/z検定表記からp値を再計算し、有意性判定の反転や大きなズレを検出します。",
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
        "image_integrity_placeholder",
        "Image integrity",
        "image-integrity",
        "図表参照を検出し、画像完全性検査が未実装であることを明示します。",
        "experimental",
        check_image_integrity_placeholder,
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

