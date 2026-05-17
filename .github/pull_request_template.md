## Summary

Describe what changed and why.

## Review integrity impact

- [ ] Findings keep `quote`, `location`, `data`, `message`, and `recommendation` evidence.
- [ ] `skipped`, `unknown`, `unsupported`, and `not implemented` are not converted to `passed`.
- [ ] Unpublished manuscript text is not sent to external services by default.
- [ ] Claim inventory, reviewer tasks, and coverage blockers remain compatible with the API/UI contract.

## Tests

- [ ] `PYTHONPATH=backend python -m pytest backend/tests -q`
- [ ] `python -m ruff check backend/openri backend/tests scripts`
- [ ] `python scripts/oss_health_check.py`
- [ ] `cd frontend && npm run build`
- [ ] `python -m build && python -m twine check dist/*`

## Notes for reviewers

Call out any known limitations, intentionally skipped checks, or follow-up issues.
