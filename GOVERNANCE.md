# Governance

OpenRI is currently maintained by the repository owner. The project is intentionally conservative: it returns evidence-backed review findings and review packets, not misconduct verdicts or automatic accept/reject decisions.

## Decision principles

- Evidence fields are part of the public contract. Findings should preserve quotes, locations, structured data, messages, recommendations, and status.
- `skipped`, `unknown`, `unsupported`, and `not implemented` must remain visible as coverage blockers or explicit limitations.
- External network or LLM use must be opt-in. Unpublished manuscripts are not sent to external services by default.
- New checks need deterministic fixtures, adversarial tests where relevant, and documentation.
- Project changes should favor reproducible review workflows over one-off heuristics.

## Maintainer responsibilities

- Keep CI, release, and security workflows passing on `main`.
- Review dependency updates from Dependabot.
- Triage issues into bug, feature, check proposal, review case, security, or documentation work.
- Reject public issues that include confidential manuscript content and ask reporters to submit a synthetic reproduction.
- Keep `README.md`, `CHANGELOG.md`, `CITATION.cff`, and release notes aligned with each tagged release.

## Contribution path

1. Open an issue or discussion unless the change is small and obvious.
2. Add or update deterministic tests for behavior changes.
3. Submit a pull request with the PR checklist completed.
4. Maintainers merge only after required checks pass and the review-integrity contract is preserved.
