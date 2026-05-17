# Release Process

OpenRI releases are built from the GitHub repository and attached to a GitHub Release.

## Local preflight

```bash
python3 scripts/oss_health_check.py
python3 -m ruff check backend/openri backend/tests scripts
PYTHONPATH=backend python3 -m pytest backend/tests -q --cov=openri --cov-report=term-missing
cd frontend && npm run build
python3 -m build
python3 -m twine check dist/*
PYTHONPATH=backend python3 -m openri.cli check samples/high_risk_manuscript.txt --fail-on high
```

The final command should exit with status `1` for the high-risk fixture because it intentionally contains high-severity findings.

## Version bump

Update all version-bearing files:

- `pyproject.toml`
- `backend/openri/__init__.py`
- `frontend/package.json`
- `frontend/package-lock.json`
- `CITATION.cff`

Then update `CHANGELOG.md`.

## GitHub release

```bash
git tag -a v0.3.2 -m "OpenRI v0.3.2"
git push origin main --tags
```

The release workflow builds the package and attaches `dist/*` to the GitHub Release.

## PyPI

The release workflow already contains an optional PyPI Trusted Publishing step. It runs only when the repository variable `PUBLISH_TO_PYPI` is set to `true`.

Before enabling it, a maintainer must create or claim the PyPI project and configure Trusted Publisher for:

- repository: `yasufumi-nakata/openri`
- workflow: `.github/workflows/release.yml`
- environment: not required by the current workflow

Keep `PUBLISH_TO_PYPI` unset or `false` until that configuration is complete.
