# Maintainer Guide

This guide keeps OpenRI release and repository operations reproducible.

## Local release preflight

```bash
python3 -m pip install -e ".[pdf,image,network,server,dev]"
python3 scripts/oss_health_check.py
python3 -m ruff check backend/openri backend/tests scripts
PYTHONPATH=backend python3 -m pytest backend/tests -q --cov=openri --cov-report=term-missing
cd frontend && npm ci && npm run build
cd ..
python3 -m build
python3 -m twine check dist/*
PYTHONPATH=backend python3 -m openri.cli check samples/high_risk_manuscript.txt --fail-on high || test $? -eq 1
```

The final command should exit with status 1 because the sample intentionally contains high-severity findings.

## Version release

Update these files together:

- `pyproject.toml`
- `backend/openri/__init__.py`
- `frontend/package.json`
- `frontend/package-lock.json`
- `CITATION.cff`
- `CHANGELOG.md`
- README release wheel example if the version changes

Then tag and push:

```bash
git tag -a v0.4.0 -m "OpenRI v0.4.0"
git push origin main v0.4.0
```

The release workflow builds artifacts, checks metadata, uploads `dist/*` to the workflow run, and optionally publishes to PyPI when `PUBLISH_TO_PYPI=true` and PyPI Trusted Publishing is configured. GitHub Releases are created manually from the checked workflow artifact when needed, keeping the release workflow token read-only for repository contents.

## GitHub repository settings

Recommended settings:

- Public repository.
- Issues and Discussions enabled.
- Squash merge enabled and delete branch on merge enabled.
- Secret scanning and push protection enabled when available.
- Branch protection on `main` requiring CI status checks.

Required status checks should include:

- `Repository health`
- `Backend tests and package (3.9)`
- `Backend tests and package (3.11)`
- `Backend tests and package (3.12)`
- `Frontend build`
- `OSS health and lint`

## Triage rules

- Close or edit public issues containing confidential manuscript material.
- Convert unsupported requests into check proposals with deterministic evidence expectations.
- Require tests for check behavior, API shape, CLI output, or review-packet changes.
- Keep network and external LLM usage opt-in.
