from __future__ import annotations

from pathlib import Path


class PDFTextExtractionError(RuntimeError):
    pass


class PDFDependencyUnavailableError(PDFTextExtractionError):
    pass


def extract_text_from_pdf(path: Path) -> str:
    try:
        import pdfplumber
    except ImportError:
        return _extract_with_pypdf(path)

    try:
        with pdfplumber.open(path) as pdf:
            chunks = []
            for index, page in enumerate(pdf.pages, start=1):
                try:
                    chunks.append(page.extract_text() or "")
                except Exception as exc:  # noqa: BLE001 - keep extraction page-isolated
                    chunks.append("")
                    if len(pdf.pages) == 1:
                        raise PDFTextExtractionError(f"PDF text extraction failed on page {index}: {exc}") from exc
            return "\n\n".join(chunks)
    except PDFTextExtractionError:
        raise
    except Exception as exc:  # noqa: BLE001 - malformed PDFs should not produce raw tracebacks
        raise PDFTextExtractionError(f"PDF text extraction failed: {exc}") from exc


def _extract_with_pypdf(path: Path) -> str:
    try:
        from pypdf import PdfReader
    except ImportError as exc:
        raise PDFDependencyUnavailableError(
            "PDF text extraction requires optional PDF dependencies; install with `pip install 'openri[pdf]'`."
        ) from exc

    try:
        reader = PdfReader(str(path))
        chunks = []
        for index, page in enumerate(reader.pages, start=1):
            try:
                chunks.append(page.extract_text() or "")
            except Exception as exc:  # noqa: BLE001 - keep extraction page-isolated
                chunks.append("")
                if len(reader.pages) == 1:
                    raise PDFTextExtractionError(f"PDF text extraction failed on page {index}: {exc}") from exc
        return "\n\n".join(chunks)
    except PDFTextExtractionError:
        raise
    except Exception as exc:  # noqa: BLE001 - malformed PDFs should not produce raw tracebacks
        raise PDFTextExtractionError(f"PDF text extraction failed: {exc}") from exc
