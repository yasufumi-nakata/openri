from __future__ import annotations

import argparse
import html
import re
from pathlib import Path
from typing import List, Optional
from urllib.parse import urlparse


ROOT = Path(__file__).resolve().parents[1]
DOCS = ROOT / "docs"

PUBLIC_DOCS = {
    "checking-your-paper.md": ("checking-your-paper", "Reading results"),
    "github-action.md": ("github-action", "GitHub Action"),
    "submitted-manuscript-workflow.md": ("submitted-manuscript-workflow", "Submitted manuscript workflow"),
    "ai-review-protocol.md": ("ai-review-protocol", "AI review protocol"),
    "deployment.md": ("deployment", "Deployment reference"),
    "distributions.md": ("distributions", "Packages and distributions"),
    "security-scorecard-triage.md": ("security-scorecard-triage", "Security Scorecard triage"),
}

GITHUB_DOC_BASE = "https://github.com/yasufumi-nakata/openri/blob/main/docs"


def rewrite_url(value: str, current_slug: str) -> str:
    parsed = urlparse(value)
    if parsed.scheme or parsed.netloc or value.startswith("#"):
        return value
    path = parsed.path
    if path.endswith(".md"):
        target = Path(path).name
        if target in PUBLIC_DOCS:
            slug = PUBLIC_DOCS[target][0]
            if slug == current_slug:
                rewritten = "./"
            else:
                rewritten = f"../{slug}/"
        else:
            rewritten = f"{GITHUB_DOC_BASE}/{path}"
        if parsed.fragment:
            rewritten = f"{rewritten}#{parsed.fragment}"
        return rewritten
    return value


def render_inline(text: str, current_slug: str) -> str:
    parts: List[str] = []
    pos = 0
    pattern = re.compile(r"(`[^`]+`|\*\*[^*]+\*\*|\[[^\]]+\]\([^)]+\))")
    for match in pattern.finditer(text):
        parts.append(html.escape(text[pos : match.start()]))
        token = match.group(0)
        if token.startswith("`"):
            parts.append(f"<code>{html.escape(token[1:-1])}</code>")
        elif token.startswith("**"):
            parts.append(f"<strong>{html.escape(token[2:-2])}</strong>")
        else:
            link_match = re.match(r"\[([^\]]+)\]\(([^)]+)\)", token)
            if link_match:
                label = render_inline(link_match.group(1), current_slug)
                href = html.escape(rewrite_url(link_match.group(2), current_slug), quote=True)
                parts.append(f'<a href="{href}">{label}</a>')
        pos = match.end()
    parts.append(html.escape(text[pos:]))
    return "".join(parts)


def render_blocks(lines: List[str], current_slug: str) -> str:
    blocks: List[str] = []
    paragraph: List[str] = []
    list_items: List[str] = []
    list_type: Optional[str] = None
    in_code = False
    code_lines: List[str] = []

    def flush_paragraph() -> None:
        if paragraph:
            text = " ".join(item.strip() for item in paragraph)
            blocks.append(f"<p>{render_inline(text, current_slug)}</p>")
            paragraph.clear()

    def flush_list() -> None:
        nonlocal list_type
        if list_items and list_type:
            rendered = "".join(f"<li>{render_inline(item, current_slug)}</li>" for item in list_items)
            blocks.append(f"<{list_type}>{rendered}</{list_type}>")
            list_items.clear()
            list_type = None

    def flush_code() -> None:
        if code_lines:
            code = html.escape("\n".join(code_lines).rstrip())
            blocks.append(f'<pre class="terminal"><code>{code}</code></pre>')
            code_lines.clear()

    for raw_line in lines:
        line = raw_line.rstrip("\n")
        if line.startswith("```"):
            if in_code:
                flush_code()
                in_code = False
            else:
                flush_paragraph()
                flush_list()
                in_code = True
            continue
        if in_code:
            code_lines.append(line)
            continue

        if not line.strip():
            flush_paragraph()
            flush_list()
            continue

        heading = re.match(r"^(#{2,4})\s+(.+)$", line)
        if heading:
            flush_paragraph()
            flush_list()
            level = len(heading.group(1))
            blocks.append(f"<h{level}>{render_inline(heading.group(2), current_slug)}</h{level}>")
            continue

        unordered = re.match(r"^-\s+(.+)$", line)
        ordered = re.match(r"^\d+\.\s+(.+)$", line)
        if unordered or ordered:
            flush_paragraph()
            item_type = "ul" if unordered else "ol"
            if list_type and list_type != item_type:
                flush_list()
            list_type = item_type
            item = unordered.group(1) if unordered else ordered.group(1)
            list_items.append(item)
            continue

        flush_list()
        paragraph.append(line)

    flush_paragraph()
    flush_list()
    if in_code:
        flush_code()
    return "\n".join(blocks)


def page_template(title: str, body: str, current_slug: str) -> str:
    return f"""<!doctype html>
<html lang="ja">
  <head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <title>{html.escape(title)} | OpenRI Tutorial</title>
    <meta name="description" content="OpenRI の公開チュートリアル関連ドキュメントです。">
    <link rel="stylesheet" href="../assets/openri-pages.css">
  </head>
  <body>
    <div class="site-shell">
      <header class="site-header">
        <nav class="nav" aria-label="Primary navigation">
          <a class="brand" href="../" aria-label="OpenRI tutorial home">
            <span class="brand-mark">RI</span>
            <span>
              <strong>OpenRI</strong>
              <span>Open Research Integrity</span>
            </span>
          </a>
          <div class="nav-links">
            <a href="../">Home</a>
            <a href="../tutorial/">Tutorial</a>
            <a href="../checking-your-paper/">Reading results</a>
            <a href="../github-action/">GitHub Action</a>
            <a href="../security-scorecard-triage/">Security</a>
            <a href="../distributions/">Packages</a>
            <a class="button" href="https://github.com/yasufumi-nakata/openri">GitHub</a>
          </div>
        </nav>
      </header>

      <main>
        <article class="article section">
          <p class="breadcrumb"><a href="../">OpenRI Tutorial</a> / {html.escape(PUBLIC_DOCS[current_slug + ".md"][1])}</p>
          <h1>{html.escape(title)}</h1>
{body}
        </article>
      </main>

      <footer class="site-footer">
        <div class="section">
          OpenRI は evidence-backed findings を返す査読前テストランナーです。不正認定や採否自動決定は行いません。
        </div>
      </footer>
    </div>
  </body>
</html>
"""


def render_markdown_page(source: Path, slug: str) -> str:
    lines = source.read_text(encoding="utf-8").splitlines()
    title = PUBLIC_DOCS[source.name][1]
    if lines and lines[0].startswith("# "):
        title = lines[0][2:].strip()
        lines = lines[1:]
    body = render_blocks(lines, slug)
    return page_template(title, body, slug)


def build_pages() -> None:
    for filename, (slug, _) in PUBLIC_DOCS.items():
        source = DOCS / filename
        target_dir = DOCS / slug
        target_dir.mkdir(parents=True, exist_ok=True)
        (target_dir / "index.html").write_text(render_markdown_page(source, slug), encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description="Build public OpenRI tutorial pages.")
    parser.parse_args()
    build_pages()
    print("OpenRI public tutorial pages built.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
