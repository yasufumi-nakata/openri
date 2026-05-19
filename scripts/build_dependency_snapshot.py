from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, Set
from urllib.parse import quote

try:
    import tomllib
except ModuleNotFoundError:  # pragma: no cover - exercised only on Python 3.9/3.10
    import tomli as tomllib  # type: ignore[no-redef]


ROOT = Path(__file__).resolve().parents[1]
PYPI_REGISTRY = "https://pypi.org/simple"


def normalize_name(name: str) -> str:
    return name.lower().replace("_", "-").replace(".", "-")


def purl(name: str, version: str) -> str:
    return f"pkg:pypi/{quote(normalize_name(name))}@{quote(version)}"


def load_toml(path: Path) -> Dict[str, Any]:
    with path.open("rb") as handle:
        return tomllib.load(handle)


def package_source_is_pypi(package: Dict[str, Any]) -> bool:
    source = package.get("source")
    if not isinstance(source, dict):
        return False
    return source.get("registry") == PYPI_REGISTRY


def dependency_names(entries: Iterable[Dict[str, Any]]) -> Set[str]:
    names: Set[str] = set()
    for entry in entries:
        name = entry.get("name")
        if isinstance(name, str):
            names.add(normalize_name(name))
    return names


def project_direct_names(packages: Iterable[Dict[str, Any]]) -> tuple[Set[str], Set[str]]:
    runtime: Set[str] = set()
    development: Set[str] = set()
    for package in packages:
        if package.get("name") != "openri":
            continue
        for entry in package.get("requires-dist", []):
            name = entry.get("name")
            if not isinstance(name, str):
                continue
            marker = str(entry.get("marker", ""))
            normalized = normalize_name(name)
            if "extra == 'dev'" in marker or 'extra == "dev"' in marker:
                development.add(normalized)
            else:
                runtime.add(normalized)
        break
    return runtime, development


def build_resolved(packages: list[Dict[str, Any]]) -> Dict[str, Dict[str, Any]]:
    runtime_direct, dev_direct = project_direct_names(packages)
    direct = runtime_direct | dev_direct
    resolved: Dict[str, Dict[str, Any]] = {}

    for package in packages:
        name = package.get("name")
        version = package.get("version")
        if not isinstance(name, str) or not isinstance(version, str):
            continue
        if normalize_name(name) == "openri" or not package_source_is_pypi(package):
            continue

        key = purl(name, version)
        normalized = normalize_name(name)
        entry: Dict[str, Any] = {
            "package_url": key,
            "relationship": "direct" if normalized in direct else "indirect",
            "scope": "development" if normalized in dev_direct else "runtime",
        }
        dependencies = dependency_names(package.get("dependencies", []))
        if dependencies:
            entry["dependencies"] = sorted(dependencies)
        resolved[key] = entry

    return dict(sorted(resolved.items()))


def build_snapshot(args: argparse.Namespace) -> Dict[str, Any]:
    lock = load_toml(ROOT / "uv.lock")
    project = load_toml(ROOT / "pyproject.toml")["project"]
    packages = lock.get("package", [])
    if not isinstance(packages, list):
        raise ValueError("uv.lock package table is missing")

    snapshot: Dict[str, Any] = {
        "version": 0,
        "sha": args.sha,
        "ref": args.ref,
        "job": {
            "correlator": args.correlator,
            "id": args.run_id,
            "html_url": args.run_url,
        },
        "detector": {
            "name": "openri-uv-lock-snapshot",
            "version": str(project["version"]),
            "url": "https://github.com/yasufumi-nakata/openri",
        },
        "scanned": datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z"),
        "manifests": {
            "uv.lock": {
                "name": "uv.lock",
                "file": {"source_location": "uv.lock"},
                "metadata": {"ecosystem": "pypi"},
                "resolved": build_resolved(packages),
            }
        },
    }
    return snapshot


def main() -> int:
    parser = argparse.ArgumentParser(description="Build a GitHub dependency-submission snapshot from uv.lock.")
    parser.add_argument("--sha", required=True)
    parser.add_argument("--ref", required=True)
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--run-url", required=True)
    parser.add_argument("--correlator", default="openri-uv-lock-snapshot")
    parser.add_argument("--output", default="-")
    args = parser.parse_args()

    payload = json.dumps(build_snapshot(args), indent=2, sort_keys=True)
    if args.output == "-":
        sys.stdout.write(payload)
        sys.stdout.write("\n")
    else:
        Path(args.output).write_text(payload + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
