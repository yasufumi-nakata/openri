from __future__ import annotations

import re
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


REQUIRED_FILES = [
    "README.md",
    "LICENSE",
    "CHANGELOG.md",
    "CITATION.cff",
    "CONTRIBUTING.md",
    "CODE_OF_CONDUCT.md",
    "SECURITY.md",
    "SUPPORT.md",
    "GOVERNANCE.md",
    "ROADMAP.md",
    "AGENTS.md",
    "CLAUDE.md",
    ".github/CODEOWNERS",
    ".github/dependabot.yml",
    ".github/pull_request_template.md",
    ".github/ISSUE_TEMPLATE/bug_report.yml",
    ".github/ISSUE_TEMPLATE/check_proposal.yml",
    ".github/ISSUE_TEMPLATE/feature_request.yml",
    ".github/ISSUE_TEMPLATE/review_case.yml",
    ".github/actions/openri-check/action.yml",
    ".github/workflows/ci.yml",
    ".github/workflows/pages.yml",
    ".github/workflows/release.yml",
    ".github/workflows/codeql.yml",
    ".github/workflows/dependency-review.yml",
    ".github/workflows/scorecard.yml",
    ".github/workflows/oss-health.yml",
    "docs/maintainer-guide.md",
    "docs/index.html",
    "docs/tutorial/index.html",
    "docs/distributions.md",
    "packages/npm/openri-client/package.json",
    "packages/mcp/openri-mcp/package.json",
    "packages/codex-skill/openri/SKILL.md",
    "requirements/action.txt",
    "requirements/docker.txt",
    "scripts/build_pages.py",
    "scripts/build_package_artifacts.py",
    "scripts/build_dependency_snapshot.py",
    "scripts/validate_pages.py",
]


README_MARKERS = [
    "actions/workflows/ci.yml/badge.svg",
    "actions/workflows/oss-health.yml/badge.svg",
    "actions/workflows/codeql.yml/badge.svg",
    "www.yasufumi.net/openri",
    "CONTRIBUTING.md",
    "SECURITY.md",
    "SUPPORT.md",
    "GOVERNANCE.md",
    "ROADMAP.md",
]


def read(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


def project_version() -> str:
    match = re.search(r'^version = "([^"]+)"$', read("pyproject.toml"), re.MULTILINE)
    if not match:
        raise AssertionError("pyproject.toml version is missing")
    return match.group(1)


def package_version() -> str:
    match = re.search(r'^__version__ = "([^"]+)"$', read("backend/openri/__init__.py"), re.MULTILINE)
    if not match:
        raise AssertionError("backend/openri/__init__.py __version__ is missing")
    return match.group(1)


def assert_contains(path: str, markers: list[str]) -> list[str]:
    text = read(path)
    return [f"{path} missing marker: {marker}" for marker in markers if marker not in text]


def main() -> int:
    errors: list[str] = []
    for path in REQUIRED_FILES:
        if not (ROOT / path).is_file():
            errors.append(f"missing required OSS file: {path}")

    version = project_version()
    if package_version() != version:
        errors.append("pyproject.toml and openri.__version__ disagree")

    citation = read("CITATION.cff")
    if f'version: "{version}"' not in citation:
        errors.append("CITATION.cff does not match project version")

    frontend_package = read("frontend/package.json")
    if f'"version": "{version}"' not in frontend_package:
        errors.append("frontend/package.json does not match project version")

    for package_path in ["packages/npm/openri-client/package.json", "packages/mcp/openri-mcp/package.json"]:
        package_text = read(package_path)
        if f'"version": "{version}"' not in package_text:
            errors.append(f"{package_path} does not match project version")

    errors.extend(assert_contains("README.md", README_MARKERS))
    errors.extend(
        assert_contains(
            ".github/workflows/ci.yml",
            [
                "permissions:",
                "contents: read",
                "Repository health",
                "ruff check",
                "--cov=openri",
                "actions/upload-artifact",
                "Install wheel smoke",
                "uv run --locked",
            ],
        )
    )
    errors.extend(
        assert_contains(
            "MANIFEST.in",
            [
                "include GOVERNANCE.md",
                "include SUPPORT.md",
                "include ROADMAP.md",
                "include SECURITY.md",
                "include CONTRIBUTING.md",
            ],
        )
    )
    errors.extend(
        assert_contains(
            ".github/workflows/release.yml",
            [
                "pypa/gh-action-pypi-publish",
                "actions/upload-artifact",
                "id-token: write",
                "contents: read",
            ],
        )
    )

    for ruleset in ["consort", "prisma", "mdar_strict", "prompt_injection"]:
        if not (ROOT / f"backend/openri/rulesets/{ruleset}.yaml").is_file():
            errors.append(f"missing packaged ruleset: {ruleset}")

    if errors:
        for error in errors:
            print(f"ERROR: {error}", file=sys.stderr)
        return 1
    print(f"OpenRI OSS health check passed for version {version}.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
