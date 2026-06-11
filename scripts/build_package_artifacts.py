from __future__ import annotations

import argparse
import gzip
import hashlib
import html
import json
import shutil
import subprocess
import sys
import tarfile
from pathlib import Path
from typing import Iterable

ROOT = Path(__file__).resolve().parents[1]
DIST = ROOT / "dist"
DOCS_PACKAGES = ROOT / "docs" / "packages"


def read_version() -> str:
    for line in (ROOT / "pyproject.toml").read_text(encoding="utf-8").splitlines():
        if line.startswith("version = "):
            return line.split('"', 2)[1]
    raise RuntimeError("pyproject.toml version is missing")


def run(command: list[str], cwd: Path = ROOT) -> subprocess.CompletedProcess[str]:
    # Windows resolves npm/node to npm.cmd/node.exe only through a PATH lookup.
    executable = shutil.which(command[0]) if sys.platform == "win32" else None
    resolved = [executable or command[0], *command[1:]]
    return subprocess.run(resolved, cwd=cwd, text=True, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def copy_python_artifacts(version: str, entries: list[dict[str, object]]) -> None:
    if DIST.exists():
        shutil.rmtree(DIST)
    run([sys.executable, "-m", "build"])

    wheel = DIST / f"openri-{version}-py3-none-any.whl"
    sdist = DIST / f"openri-{version}.tar.gz"

    target = DOCS_PACKAGES / "python"
    target.mkdir(parents=True, exist_ok=True)
    copied: list[Path] = []
    for source in [wheel, sdist]:
        destination = target / source.name
        shutil.copy2(source, destination)
        copied.append(destination)

    checksum_lines = [f"{sha256(path)}  {path.name}" for path in copied]
    (target / "SHA256SUMS").write_text("\n".join(checksum_lines) + "\n", encoding="utf-8")
    sbom = {
        "spdxVersion": "SPDX-2.3",
        "dataLicense": "CC0-1.0",
        "SPDXID": "SPDXRef-DOCUMENT",
        "name": "openri-pages-python-artifacts",
        "documentNamespace": "https://www.yasufumi.net/openri/packages/python",
        "creationInfo": {"creators": ["Tool: OpenRI package artifact builder"]},
        "packages": [
            {"fileName": path.name, "checksums": [{"algorithm": "SHA256", "checksumValue": sha256(path)}]}
            for path in copied
        ],
    }
    (target / "openri-release.spdx.json").write_text(json.dumps(sbom, indent=2), encoding="utf-8")

    for path in copied + [target / "SHA256SUMS", target / "openri-release.spdx.json"]:
        entries.append(
            {
                "kind": "python",
                "name": path.name,
                "path": f"python/{path.name}",
                "sha256": sha256(path),
                "size": path.stat().st_size,
            }
        )


def npm_pack(package_dir: Path, destination: Path) -> Path:
    destination.mkdir(parents=True, exist_ok=True)
    result = run(["npm", "pack", "--json", "--pack-destination", str(destination), str(package_dir)])
    payload = json.loads(result.stdout)
    filename = payload[0]["filename"]
    return destination / filename


def copy_npm_artifacts(entries: list[dict[str, object]]) -> None:
    packages = [
        ("npm", ROOT / "packages" / "npm" / "openri-client"),
        ("mcp", ROOT / "packages" / "mcp" / "openri-mcp"),
    ]
    for kind, package_dir in packages:
        path = npm_pack(package_dir, DOCS_PACKAGES / kind)
        entries.append(
            {
                "kind": kind,
                "name": path.name,
                "path": f"{kind}/{path.name}",
                "sha256": sha256(path),
                "size": path.stat().st_size,
            }
        )


def copy_skill_artifact(version: str, entries: list[dict[str, object]]) -> None:
    source_dir = ROOT / "packages" / "codex-skill" / "openri"
    target_dir = DOCS_PACKAGES / "skill"
    target_dir.mkdir(parents=True, exist_ok=True)
    target = target_dir / f"openri-codex-skill-{version}.tar.gz"
    with target.open("wb") as raw:
        with gzip.GzipFile(fileobj=raw, mode="wb", mtime=0) as compressed:
            with tarfile.open(fileobj=compressed, mode="w") as archive:
                for path in sorted(source_dir.rglob("*")):
                    if path.is_file():
                        info = archive.gettarinfo(str(path), arcname=str(Path("openri") / path.relative_to(source_dir)))
                        info.uid = 0
                        info.gid = 0
                        info.uname = ""
                        info.gname = ""
                        info.mtime = 0
                        with path.open("rb") as handle:
                            archive.addfile(info, handle)
    entries.append(
        {
            "kind": "skill",
            "name": target.name,
            "path": f"skill/{target.name}",
            "sha256": sha256(target),
            "size": target.stat().st_size,
        }
    )


def render_table(entries: Iterable[dict[str, object]]) -> str:
    rows = []
    for entry in entries:
        rows.append(
            "<tr>"
            f"<td>{html.escape(str(entry['kind']))}</td>"
            f'<td><a href="{html.escape(str(entry["path"]))}">{html.escape(str(entry["name"]))}</a></td>'
            f"<td><code>{html.escape(str(entry['sha256'])[:16])}</code></td>"
            f"<td>{entry['size']}</td>"
            "</tr>"
        )
    return "\n".join(rows)


def write_index(version: str, entries: list[dict[str, object]]) -> None:
    table = render_table(entries)
    html_text = f"""<!doctype html>
<html lang="ja">
  <head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <title>OpenRI Packages</title>
    <meta name="description" content="OpenRI の Python、npm、MCP、Codex skill 配布物です。">
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
            <a href="../tutorial/">Tutorial</a>
            <a href="../checking-your-paper/">Reading results</a>
            <a href="../github-action/">GitHub Action</a>
            <a href="../distributions/">Packages</a>
            <a class="button" href="https://github.com/yasufumi-nakata/openri">GitHub</a>
          </div>
        </nav>
      </header>

      <main>
        <article class="article section">
          <p class="breadcrumb"><a href="../">OpenRI Tutorial</a> / Packages</p>
          <h1>OpenRI package registry</h1>
          <p>GitHub Pages から取得できる OpenRI の配布物です。未公開原稿を外部 API へ送らない既定値と、モデル非依存のAI判断ガードレールは、CLI、API、MCP、Codex skill の各入口で維持します。</p>
          <div class="package-grid">
            <section class="package-card">
              <h2>Python</h2>
              <p>wheel と source distribution、checksum、SPDX metadata を公開します。</p>
              <pre class="terminal"><code>pip install https://www.yasufumi.net/openri/packages/python/openri-{version}-py3-none-any.whl</code></pre>
            </section>
            <section class="package-card">
              <h2>npm client</h2>
              <p>OpenRI API を呼ぶ軽量 ESM client です。</p>
              <pre class="terminal"><code>npm install https://www.yasufumi.net/openri/packages/npm/openri-client-{version}.tgz</code></pre>
            </section>
            <section class="package-card">
              <h2>MCP server</h2>
              <p>ローカル OpenRI API を MCP tool として公開します。</p>
              <pre class="terminal"><code>npm install https://www.yasufumi.net/openri/packages/mcp/openri-mcp-{version}.tgz</code></pre>
            </section>
            <section class="package-card">
              <h2>Codex skill</h2>
              <p>原稿検査、report 解釈、AI reviewer protocol 確認用の skill です。</p>
              <pre class="terminal"><code>curl -LO https://www.yasufumi.net/openri/packages/skill/openri-codex-skill-{version}.tar.gz</code></pre>
            </section>
          </div>
          <h2>Artifacts</h2>
          <table class="artifact-table">
            <thead><tr><th>Kind</th><th>File</th><th>SHA256 prefix</th><th>Bytes</th></tr></thead>
            <tbody>
{table}
            </tbody>
          </table>
          <p><a href="manifest.json">manifest.json</a> contains the full hashes and sizes for automation.</p>
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
    (DOCS_PACKAGES / "index.html").write_text(html_text, encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description="Build OpenRI package artifacts for GitHub Pages.")
    parser.parse_args()
    version = read_version()
    if DOCS_PACKAGES.exists():
        shutil.rmtree(DOCS_PACKAGES)
    DOCS_PACKAGES.mkdir(parents=True)

    entries: list[dict[str, object]] = []
    copy_python_artifacts(version, entries)
    copy_npm_artifacts(entries)
    copy_skill_artifact(version, entries)
    (DOCS_PACKAGES / "manifest.json").write_text(
        json.dumps({"version": version, "artifacts": entries}, indent=2), encoding="utf-8"
    )
    write_index(version, entries)
    print("OpenRI package artifacts built.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
