# Highest-Standard Roadmap

OpenRI aims to become a best-in-class, open, evidence-backed review system. The path is explicit so that progress can be tested instead of asserted.

## Current foundation

- Deterministic integrity checks for statistics, transparency, citations, prompt injection, duplicate text, ruleset coverage, DOI lookup, and PDF hidden text.
- AI reviewer protocol with no-social-leniency policy.
- Claim-centered review packet for AI reviewer handoff.
- Web UI, API, CLI, SARIF output, and SQLite report store.
- CI and package release workflow.

## Next benchmark layers

1. **Golden manuscript corpus**
   - clean manuscript
   - p-value mismatch
   - prompt injection
   - hidden PDF text
   - hallucinated references
   - unsupported causal claims
   - field-specific reporting omissions

2. **Cross-model review evaluation**
   - run Codex, Claude, and other AI reviewers on the same `review_packet`
   - compare high-severity finding recall
   - treat disagreement as evidence/rubric debt, not majority truth

3. **Image integrity**
   - EXIF inspection
   - duplicated region detection
   - compression artifact review
   - figure/text cross-reference consistency

4. **Citation context verification**
   - reference extraction
   - DOI/OpenAlex/Semantic Scholar metadata
   - claim-to-citation support check

5. **Editorial operations**
   - submission webhook intake
   - queue dashboard
   - author query templates
   - audit log
   - role-based access control

6. **Release maturity**
   - published PyPI package
   - signed releases
   - stable JSON schema
   - documented API versioning
   - benchmark reports in every release
