# Security Policy

## Supported versions

OpenRI is currently an alpha project. Security fixes are applied to the latest released version.

## Reporting vulnerabilities

Please report security issues privately through GitHub private vulnerability reporting:

https://github.com/yasufumi-nakata/openri/security/advisories/new

Do not open public issues for vulnerabilities involving unpublished manuscripts, prompt-injection bypasses, PDF hidden text bypasses, or credential exposure.

## Manuscript data handling

- OpenRI does not send unpublished manuscripts to external LLMs or external APIs by default.
- Network checks, such as Crossref DOI lookup, are opt-in.
- Local reports are stored in SQLite under `OPENRI_DB_PATH` or `~/.openri/reports.sqlite3`.
- Treat report JSON as potentially sensitive because it may contain manuscript quotes.

## Threat model

OpenRI explicitly considers the following hostile inputs:

- hidden reviewer instructions in PDF/text/HTML
- invisible Unicode control characters
- white or off-page PDF text
- placeholder or hallucinated references
- unsupported or overstated claims
- attempts to weaken reviewer thresholds through author identity or prestige cues
