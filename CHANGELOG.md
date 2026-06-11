# Changelog

All notable changes to OpenRI are documented here.

## Unreleased

- Fixed `pdf_hidden_text` severity aggregation that compared severity labels alphabetically, which could downgrade mixed critical/high PDF risks to a lower severity and bypass the failed status.
- Fixed `pdf_hidden_text` treating unavailable PDF inspections (missing pdfplumber or inspection errors) as passed; they are now skipped coverage blockers.
- Fixed Japanese keyword cues (claim, limitation, causal, novelty, overgeneralization, figure references, and ruleset "該当なし" detection) that never matched inside Japanese sentences because ASCII word boundaries do not exist between kana/kanji characters.
- Fixed claim-type detection for spaced statistical expressions such as `p < 0.05`.
- Ordered accountability `worst_findings` ties by severity rank instead of alphabetical severity labels.
- Coerced unknown plugin manifest maturity values to `experimental` so `/api/checks` cannot fail on third-party manifests.
- Made golden report regeneration deterministic by pinning finding ids.
- Hardened the npm client and MCP server against non-JSON API responses so HTTP status context is preserved instead of raising `SyntaxError`.
- Updated starlette to a fixed version (>= 1.0.1) in `requirements/action.txt`, `requirements/docker.txt`, and `uv.lock` (GHSA-86qp-5c8j-p5mr).

## 0.3.2 - 2026-05-18

- Included OSS governance, support, roadmap, security, contributing, and agent guidance files in source distributions.
- Fixed the OpenSSF Scorecard workflow permission layout for publishable scorecard results.
- Added branch-protection-ready CI permission hardening and repository health checks.

## 0.3.1 - 2026-05-18

- Added GitHub issue forms, pull request template, CODEOWNERS, support, governance, and public roadmap.
- Added Dependabot, CodeQL, Dependency Review, OpenSSF Scorecard, repository health checks, ruff fatal-error lint, and coverage reporting.
- Upgraded GitHub Actions workflow actions to current major versions and added release artifact upload in CI.
- Added branch-protection-ready status checks and OSS health validation for release and repository metadata.

## 0.3.0 - 2026-05-17

- Added claim-centered `ai_review_protocol.review_packet` for AI reviewer handoff.
- Added field-neutral reviewer roles, universal review dimensions, no-social-leniency policy, coverage blockers, and adversarial challenges.
- Added PDF/text upload support, PDF hidden text inspection, SARIF export, SQLite report store, Crossref DOI checks, and YAML rulesets.
- Added Web UI panels for submitted manuscript routing, AI reviewer protocol, claim inventory, reviewer tasks, evidence, and API endpoints.
- Added release-ready project metadata, CI, release workflow, security/contributing docs, and packaging checks.

## 0.1.0 - 2026-05-17

- Initial prototype of Open Research Integrity manuscript test runner.
