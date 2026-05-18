from __future__ import annotations

import sys
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urlparse


ROOT = Path(__file__).resolve().parents[1]
PAGES = [ROOT / "docs/index.html", ROOT / "docs/tutorial/index.html"]


class LinkParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.links: list[tuple[str, str]] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        attr_name = "src" if tag in {"img", "script"} else "href"
        for name, value in attrs:
            if name == attr_name and value:
                self.links.append((tag, value))


def local_target(page: Path, value: str) -> Path | None:
    parsed = urlparse(value)
    if parsed.scheme or parsed.netloc or value.startswith("#"):
        return None
    path = parsed.path
    if not path:
        return None
    target = (page.parent / path).resolve()
    if path.endswith("/"):
        target = target / "index.html"
    return target


def main() -> int:
    errors: list[str] = []
    for page in PAGES:
        if not page.is_file():
            errors.append(f"missing page: {page.relative_to(ROOT)}")
            continue
        html = page.read_text(encoding="utf-8")
        for marker in ["OpenRI", "不正認定や採否自動決定は行いません", "openri-report-preview.png"]:
            if marker not in html:
                errors.append(f"{page.relative_to(ROOT)} missing marker: {marker}")
        parser = LinkParser()
        parser.feed(html)
        for tag, value in parser.links:
            target = local_target(page, value)
            if target and not target.exists():
                errors.append(f"{page.relative_to(ROOT)} broken {tag} link: {value}")
    if errors:
        for error in errors:
            print(f"ERROR: {error}", file=sys.stderr)
        return 1
    print("OpenRI tutorial pages validated.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
