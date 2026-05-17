# Roadmap

OpenRI aims to become an open, evidence-backed review infrastructure for submitted manuscripts.

## Current release line

- CLI, FastAPI API, React Web UI, SARIF output, and SQLite report storage.
- Statistical consistency, summary-stat plausibility, transparency, citation, prompt-injection, duplicate-text, DOI, ruleset coverage, image-placeholder, and PDF hidden-text checks.
- Claim-centered `ai_review_protocol.review_packet` for AI reviewer handoff.
- No-social-leniency policy, coverage blockers, reviewer tasks, adversarial challenges, and editor handoff.
- GitHub CI, release artifacts, CodeQL, Dependency Review, OpenSSF Scorecard, Dependabot, and repository health checks.

## Near-term priorities

1. Stable JSON schema for `RunReport`, `Finding`, and `review_packet`.
2. Golden manuscript corpus with clean, high-risk, hidden-PDF, citation-risk, and unsupported-claim fixtures.
3. Additional reporting rulesets such as STROBE and ARRIVE.
4. Stronger APA/statcheck coverage for tables and multi-line statistics.
5. GitHub Action wrapper for journal/editorial CI workflows.

## Medium-term priorities

1. Image integrity checks for metadata, duplicated regions, compression artifacts, and figure/text cross-reference consistency.
2. Reference extraction and citation context verification with explicit opt-in external lookups.
3. Cross-model review evaluation for Codex, Claude, and other AI reviewers using the same review packet.
4. API versioning and hosted deployment reference architecture.
5. Role-based editorial queue with audit log and author-query templates.

## Non-goals

- Automatic misconduct determinations.
- Automatic accept/reject decisions.
- Default submission of unpublished manuscripts to external LLMs or APIs.
- Hiding unsupported or unimplemented checks behind a passing status.
