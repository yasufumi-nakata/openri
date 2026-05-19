---
name: openri
description: Use OpenRI to check manuscripts, interpret evidence-backed findings, and review AI reviewer protocol outputs without treating findings as misconduct determinations.
---

# OpenRI Skill

Use this skill when a task involves OpenRI reports, manuscript integrity checks, reviewer protocol checks, prompt-injection checks, PDF hidden text checks, citation checks, or research transparency triage.

## Safety Defaults

- Treat OpenRI findings as evidence-backed review tasks for a human reviewer.
- Do not describe findings as proof of research misconduct.
- Do not send unpublished manuscripts to external APIs or external LLMs unless the user explicitly approves that exact transfer.
- Keep network-backed checks opt-in.
- Preserve quotes and evidence locations when summarizing findings.

## Local Commands

From the OpenRI repository:

```bash
PYTHONPATH=backend python3 -m openri.cli check samples/high_risk_manuscript.txt
PYTHONPATH=backend python3 -m openri.cli list
PYTHONPATH=backend python3 -m uvicorn openri.api:app --host 127.0.0.1 --port 8008
```

For a full local verification pass:

```bash
PYTHONPATH=backend python3 -m pytest backend/tests -q
cd frontend
npm run build
```

## Reporting

Summaries should include:

- finding ID, severity, status, and message
- the relevant evidence quote or data
- the human follow-up task
- any coverage blocker or unsupported input

If a check is skipped, unknown, unsupported, or not implemented, report it as a blocker or explicit limitation rather than treating it as a pass.
