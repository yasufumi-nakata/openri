from __future__ import annotations

from pathlib import Path


def extract_text_from_pdf(path: Path) -> str:
    try:
        import pdfplumber
    except ImportError:
        return _extract_with_pypdf(path)

    with pdfplumber.open(path) as pdf:
        return "\n\n".join(page.extract_text() or "" for page in pdf.pages)


def _extract_with_pypdf(path: Path) -> str:
    from pypdf import PdfReader

    reader = PdfReader(str(path))
    return "\n\n".join(page.extract_text() or "" for page in reader.pages)

