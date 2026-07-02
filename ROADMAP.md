# Roadmap

OpenRI aims to become an open, evidence-backed review infrastructure for submitted manuscripts.

## Current release line (v0.4.0)

- CLI, FastAPI API, React Web UI, SARIF output, SQLite report storage, and a GitHub Action wrapper (`.github/actions/openri-check`).
- Statistical consistency (t/F/χ²/r/z, including df-less `z = value` reports), summary-stat plausibility, effect-size/CI coverage, transparency, citation integrity, citation-context audit (numeric and author-year reference linkage), claim-evidence alignment, prompt-injection, duplicate-text, DOI existence, ruleset coverage, image integrity (EXIF provenance and duplicate-region candidates), and PDF hidden-text/structure checks.
- Field-specific rulesets: CONSORT, PRISMA, MDAR-strict, STROBE, ARRIVE, CARE, CHEERS, TRIPOD.
- Claim-centered `ai_review_protocol.review_packet` for AI reviewer handoff.
- No-social-leniency policy, coverage blockers, reviewer tasks, adversarial challenges, and editor handoff.
- Golden manuscript corpus (`samples/golden/`) with pinned reports, an exported `RunReport` JSON schema (`schemas/`), and external peer-review corpus smoke benchmarks.
- GitHub CI, release artifacts, CodeQL, Dependency Review, OpenSSF Scorecard, Dependabot, and repository health checks.

## Near-term priorities

1. Stronger APA/statcheck coverage for tables and multi-line statistics.
2. Deeper image integrity checks: splice boundaries, compression artifacts, ELA-style analysis, and figure/text cross-reference consistency.
3. Effect-size / confidence-interval / p-value mutual-consistency recomputation (currently reported as a coverage blocker).
4. Reference-list metadata extraction and stronger citation cross-checks.

## Medium-term priorities

1. Citation context verification with explicit opt-in external lookups (OpenAlex / Semantic Scholar).
2. Cross-model review evaluation for Codex, Claude, and other AI reviewers using the same review packet.
3. API versioning and hosted deployment reference architecture.
4. Role-based editorial queue with audit log and author-query templates.

## Non-goals

- Automatic misconduct determinations.
- Automatic accept/reject decisions.
- Default submission of unpublished manuscripts to external LLMs or APIs.
- Hiding unsupported or unimplemented checks behind a passing status.
