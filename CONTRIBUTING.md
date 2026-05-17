# Contributing to OpenRI

OpenRI is a research-integrity and AI-review test runner. Contributions should preserve the central design rule: findings are evidence-backed review work items, not automatic misconduct verdicts or acceptance decisions.

## Development setup

```bash
pip install -e ".[pdf,network,server,dev]"
cd frontend && npm install
```

## Required checks

Run these before proposing changes:

```bash
PYTHONPATH=backend python3 -m pytest backend/tests -q
cd frontend && npm run build
python3 -m build
python3 -m twine check dist/*
```

## Adding a check

- Add deterministic tests with positive, negative, and borderline samples.
- Preserve `Evidence(quote, location, data)` whenever a finding is created.
- Never treat `skipped`, `unknown`, `unsupported`, or `not implemented` as passed.
- Keep network-backed checks behind explicit flags.
- Do not send unpublished manuscripts to external APIs by default.

## AI reviewer protocol changes

Changes to `ai_review_protocol` or `review_packet` must include tests that pin:

- claim inventory shape
- reviewer task shape
- coverage blocker handling
- no-social-leniency behavior
- external LLM calls remaining disabled by default
