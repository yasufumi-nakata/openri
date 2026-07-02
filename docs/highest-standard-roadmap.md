# Highest-Standard Roadmap

OpenRI aims to become a best-in-class, open, evidence-backed review system. The path is explicit so that progress can be tested instead of asserted.

## Current foundation (v0.4.0)

- Deterministic integrity checks for statistics (t/F/χ²/r/z), transparency, citation integrity and reference linkage (numeric and author-year), claim-evidence alignment, prompt injection, duplicate text, ruleset coverage, DOI lookup, image EXIF/duplicate-region inspection, and PDF hidden-text/structure risks.
- Golden manuscript corpus with pinned reports (clean, p-value mismatch, prompt injection, placeholder citations, unsupported causal claims, ruleset omission, borderline rounding, missing transparency) plus hidden-PDF-text fixtures in the test suite.
- Model-agnostic AI reviewer protocol with no-social-leniency policy.
- Claim-centered review packet for AI reviewer handoff, with `openri eval-reviewers` for cross-model disagreement records.
- Web UI, API, CLI, SARIF output, SQLite report store, GitHub Action wrapper, and exported `RunReport` JSON schema.
- CI and package release workflow.

## Next benchmark layers

1. **Cross-model review evaluation at scale**
   - run GPT-5.5, GPT-6.7, Claude, local, and future AI reviewers on the same `review_packet`
   - compare high-severity finding recall
   - treat disagreement as evidence/rubric debt, not majority truth
   - treat model names and versions as audit metadata, not acceptance thresholds

2. **Deeper image integrity**
   - splice-boundary and compression-artifact analysis (ELA-style)
   - figure/text cross-reference consistency
   - multi-image and PDF-embedded-image extraction

3. **Citation context verification**
   - reference metadata extraction
   - DOI/OpenAlex/Semantic Scholar metadata (explicit opt-in)
   - claim-to-citation support check beyond mechanical linkage

4. **Statistics depth**
   - table and multi-line APA statistics
   - effect-size / CI / p-value mutual-consistency recomputation

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
