# Architecture

OpenRI has one canonical report object: `RunReport`.

## Data flow

1. Input arrives through the CLI, `POST /api/runs`, or `POST /api/runs/upload`.
2. PDF inputs are converted to text and inspected for hidden text.
3. `analyze_manuscript()` builds a manuscript profile and runs registered checks.
4. Findings are summarized into score, severity counts, and submission routing.
5. `ai_review_protocol` adds the field-neutral AI review rubric.
6. `review_packet` adds manuscript-specific claim inventory, reviewer tasks, adversarial challenges, and editor handoff.
7. `accountability` explains route drivers, score inputs, evidence quality, coverage blockers, and autonomous AI decision inputs.
8. Reports can be saved to SQLite and exported as JSON or SARIF.

## Extension points

- `backend/openri/checks.py`: deterministic checks (register in `CHECKS`).
- `backend/openri/cues.py`: shared claim/citation/limitation cue regexes reused across checks.
- `backend/openri/references.py`: reference-list extraction and numeric/author-year citation linkage.
- `backend/openri/rulesets/*.yaml`: keyword/ruleset coverage checks.
- `backend/openri/pdf_inspect.py`: PDF layout, hidden text, and document-structure risk checks.
- `backend/openri/image_inspect.py`: image EXIF provenance and duplicate-region candidates.
- `backend/openri/plugin_loader.py`: declarative JSON check plugins via `OPENRI_CHECK_PLUGIN_PATHS`.
- `backend/openri/analyzer.py`: AI review packet and routing logic.
- `backend/openri/sarif.py`: GitHub Code Scanning bridge.

## Non-goals

- Automatic misconduct verdicts.
- Automatic acceptance or rejection decisions.
- Sending unpublished manuscripts to external LLMs by default.
- Treating skipped or unsupported checks as safe.
