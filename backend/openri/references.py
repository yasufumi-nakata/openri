from __future__ import annotations

import re
from typing import Dict, List


REFERENCE_HEADING_RE = re.compile(r"^\s*(references|bibliography|参考文献)\s*$", re.IGNORECASE | re.MULTILINE)
NUMERIC_CITATION_RE = re.compile(r"\[(?P<items>\d{1,3}(?:\s*(?:,|-)\s*\d{1,3})*)\]")
AUTHOR_YEAR_CITATION_RE = re.compile(r"\(([A-Z][A-Za-z-]+(?:\s+et\s+al\.)?),\s*(20\d{2}|19\d{2})\)")
DOI_RE = re.compile(r"\b10\.\d{4,9}/[-._;()/:A-Z0-9]+\b", re.IGNORECASE)
CLAIM_RE = re.compile(
    r"\b(significant|significantly|novel|first|caus(?:e|al|es|ed|ation)|"
    r"robust|prove|definitive|conclusive|improves?|predicts?|associated|"
    r"有意|新規|初めて|因果|証明|改善|関連)\b",
    re.IGNORECASE,
)


def reference_section(text: str) -> str:
    match = REFERENCE_HEADING_RE.search(text)
    if not match:
        return ""
    return text[match.end():].strip()


def extract_reference_items(text: str) -> List[Dict[str, object]]:
    section = reference_section(text)
    if not section:
        return []
    items: List[Dict[str, object]] = []
    current: List[str] = []
    for raw_line in section.splitlines():
        line = raw_line.strip()
        if not line:
            if current:
                items.append(_reference_item(len(items) + 1, " ".join(current)))
                current = []
            continue
        starts_item = bool(re.match(r"^(\[\d+\]|\d+[\).]|[A-Z][A-Za-z-]+,\s)", line))
        if starts_item and current:
            items.append(_reference_item(len(items) + 1, " ".join(current)))
            current = [line]
        else:
            current.append(line)
    if current:
        items.append(_reference_item(len(items) + 1, " ".join(current)))
    return items


def _reference_item(index: int, text: str) -> Dict[str, object]:
    doi_match = DOI_RE.search(text)
    year_match = re.search(r"\b(19\d{2}|20\d{2})\b", text)
    return {
        "index": index,
        "text": text[:500],
        "doi": doi_match.group(0) if doi_match else None,
        "year": int(year_match.group(1)) if year_match else None,
        "has_placeholder_doi": bool(doi_match and doi_match.group(0).lower().startswith(("10.0000/", "10.1234/", "10.9999/"))),
    }


def extract_inline_citations(text: str) -> List[Dict[str, object]]:
    citations: List[Dict[str, object]] = []
    for match in NUMERIC_CITATION_RE.finditer(text):
        citations.append(
            {
                "style": "numeric",
                "quote": match.group(0),
                "items": _expand_numeric_items(match.group("items")),
                "start": match.start(),
            }
        )
    for match in AUTHOR_YEAR_CITATION_RE.finditer(text):
        citations.append(
            {
                "style": "author-year",
                "quote": match.group(0),
                "author": match.group(1),
                "year": int(match.group(2)),
                "start": match.start(),
            }
        )
    return sorted(citations, key=lambda item: int(item["start"]))


def _expand_numeric_items(raw: str) -> List[int]:
    values: List[int] = []
    for part in re.split(r"\s*,\s*", raw):
        if "-" in part:
            left, right = [int(v.strip()) for v in part.split("-", 1)]
            if left <= right and right - left <= 50:
                values.extend(range(left, right + 1))
        else:
            values.append(int(part.strip()))
    return values


def citation_context_audit(text: str) -> Dict[str, object]:
    refs = extract_reference_items(text)
    cites = extract_inline_citations(text)
    ref_count = len(refs)
    unresolved = []
    for cite in cites:
        if cite["style"] != "numeric":
            continue
        missing = [item for item in cite["items"] if item > ref_count]
        if missing:
            unresolved.append({"quote": cite["quote"], "missing_reference_numbers": missing})

    unsupported_claims = []
    for match in re.finditer(r"[^.!?\n。！？]+(?:[.!?。！？]+|\n|$)", text):
        sentence = " ".join(match.group(0).split())
        if len(sentence) < 35 or not CLAIM_RE.search(sentence):
            continue
        has_citation = bool(NUMERIC_CITATION_RE.search(sentence) or AUTHOR_YEAR_CITATION_RE.search(sentence) or DOI_RE.search(sentence))
        has_stat = bool(re.search(r"\b(t|F|z|p|CI|OR|RR|HR|β|r)\s*(?:\(|=|<|>)", sentence, re.IGNORECASE))
        if not has_citation and not has_stat:
            unsupported_claims.append({"quote": sentence[:300], "reason": "claim lacks local citation/statistic marker"})
        if len(unsupported_claims) >= 8:
            break

    return {
        "reference_count": ref_count,
        "references": refs[:30],
        "inline_citations": [{k: v for k, v in item.items() if k != "start"} for item in cites[:50]],
        "unresolved_numeric_citations": unresolved,
        "placeholder_references": [item for item in refs if item.get("has_placeholder_doi")],
        "unsupported_claims": unsupported_claims,
        "external_lookup_policy": "Crossref/OpenAlex/Semantic Scholar checks require explicit network opt-in.",
    }
