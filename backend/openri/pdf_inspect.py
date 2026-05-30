from __future__ import annotations

from pathlib import Path
from typing import Any

_NEAR_WHITE_THRESHOLD = 0.95


def _normalize_channel(value: Any) -> float | None:
    if value is None:
        return None
    if isinstance(value, (list, tuple)):
        return None
    try:
        v = float(value)
    except (TypeError, ValueError):
        return None
    if v > 1.0:
        v = v / 255.0
    return v


def _is_near_white(color: Any) -> bool:
    if color is None:
        return False
    if isinstance(color, (list, tuple)):
        if not color:
            return False
        values = [_normalize_channel(c) for c in color]
        if any(v is None for v in values):
            return False
        return all(v >= _NEAR_WHITE_THRESHOLD for v in values)
    v = _normalize_channel(color)
    if v is None:
        return False
    return v >= _NEAR_WHITE_THRESHOLD


def _classify_char(char: dict, page_width: float, page_height: float) -> str | None:
    size = char.get("size") or 0
    if size and size < 1.0:
        return "tiny-font"
    if _is_near_white(char.get("non_stroking_color")):
        return "white-on-white"
    x0 = char.get("x0", 0)
    x1 = char.get("x1", 0)
    top = char.get("top", 0)
    bottom = char.get("bottom", 0)
    if x1 < 0 or top < 0 or x0 > page_width + 1 or bottom > page_height + 1:
        return "off-page"
    return None


def _group_runs(chars: list[dict]) -> list[dict]:
    runs: list[dict] = []
    current: dict | None = None
    for char in chars:
        kind = char["_kind"]
        if (
            current is not None
            and current["kind"] == kind
            and current["page"] == char["_page"]
            and abs(char.get("x0", 0) - current["end_x"]) < (char.get("size") or 6)
            and abs((char.get("top", 0)) - current["top"]) < 3
        ):
            current["text"] += char.get("text", "")
            current["end_x"] = char.get("x1", current["end_x"])
        else:
            if current is not None:
                runs.append(current)
            current = {
                "kind": kind,
                "page": char["_page"],
                "text": char.get("text", ""),
                "start_x": char.get("x0", 0),
                "end_x": char.get("x1", 0),
                "top": char.get("top", 0),
                "size": char.get("size", 0),
            }
    if current is not None:
        runs.append(current)
    return runs


def inspect_pdf(path: Path) -> dict:
    try:
        import pdfplumber  # type: ignore
    except ImportError:
        return {"available": False, "reason": "pdfplumber-not-installed", "hidden_text": [], "page_count": 0}

    hidden_chars: list[dict] = []
    document_risks: list[dict] = []
    page_count = 0
    image_count = 0
    total_chars = 0
    with pdfplumber.open(path) as pdf:
        page_count = len(pdf.pages)
        for page_index, page in enumerate(pdf.pages, start=1):
            width = float(page.width or 0)
            height = float(page.height or 0)
            try:
                chars = page.chars
            except Exception:
                continue
            total_chars += len(chars)
            try:
                image_count += len(page.images or [])
            except Exception:
                pass
            for char in chars:
                kind = _classify_char(char, width, height)
                if kind is None:
                    continue
                marked = dict(char)
                marked["_kind"] = kind
                marked["_page"] = page_index
                hidden_chars.append(marked)

    document_risks.extend(_pdf_structure_risks(path))
    if page_count and total_chars == 0:
        severity = "medium" if image_count else "low"
        document_risks.append(
            {
                "kind": "ocr-required-or-empty-text-layer",
                "severity": severity,
                "page": None,
                "text": None,
                "image_count": image_count,
                "message": "PDF has no extractable text layer; image-only or scanned submissions need OCR before AI review.",
            }
        )

    runs = _group_runs(hidden_chars)
    hits = []
    for run in runs:
        text = run["text"].strip()
        if not text:
            continue
        severity = {
            "tiny-font": "high",
            "white-on-white": "high",
            "off-page": "medium",
        }.get(run["kind"], "medium")
        hits.append(
            {
                "kind": run["kind"],
                "severity": severity,
                "page": run["page"],
                "text": text,
                "font_size": round(float(run.get("size") or 0), 3),
                "x_range": [round(run["start_x"], 2), round(run["end_x"], 2)],
                "top": round(run.get("top", 0), 2),
            }
        )
    return {
        "available": True,
        "page_count": page_count,
        "hidden_text": hits,
        "document_risks": document_risks,
        "image_count": image_count,
        "text_char_count": total_chars,
    }


def _pdf_structure_risks(path: Path) -> list[dict]:
    try:
        from pypdf import PdfReader  # type: ignore
    except ImportError:
        return []
    try:
        reader = PdfReader(str(path))
    except Exception as exc:  # noqa: BLE001 - malformed PDFs are reported as a coverage blocker
        return [{"kind": "pdf-structure-read-failed", "severity": "medium", "message": str(exc)[:160]}]

    risks: list[dict] = []
    root = getattr(reader, "trailer", {}).get("/Root", {})
    names = root.get("/Names", {}) if hasattr(root, "get") else {}
    if names and names.get("/EmbeddedFiles"):
        risks.append({"kind": "embedded-files", "severity": "high", "message": "PDF contains embedded files."})
    if names and names.get("/JavaScript"):
        risks.append({"kind": "javascript", "severity": "high", "message": "PDF contains JavaScript name tree."})
    if root.get("/OCProperties") if hasattr(root, "get") else False:
        risks.append(
            {
                "kind": "optional-content-groups",
                "severity": "medium",
                "message": "PDF contains optional content/layer properties.",
            }
        )

    annotated_pages = []
    for index, page in enumerate(reader.pages, start=1):
        try:
            annotations = page.get("/Annots")
        except Exception:
            annotations = None
        if annotations:
            annotated_pages.append(index)
    if annotated_pages:
        risks.append(
            {
                "kind": "annotations",
                "severity": "medium",
                "pages": annotated_pages[:20],
                "page_count": len(annotated_pages),
                "message": f"PDF has annotations on {len(annotated_pages)} page(s).",
            }
        )
    return risks
