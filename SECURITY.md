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
- Public deployments must use explicit `OPENRI_CORS_ORIGINS`; wildcard CORS is rejected. Keep `OPENRI_CORS_ALLOW_CREDENTIALS=false` unless a trusted same-site cookie deployment requires it.
- Reverse proxies should enforce upload and rate limits before OpenRI. If `X-Forwarded-For` is trusted, the proxy must strip spoofed inbound forwarding headers and uvicorn should use `--forwarded-allow-ips` scoped to trusted proxy addresses; otherwise prefer API-key-based rate limiting.
- The built-in rate limiter is in-process and per worker. Public deployments should pair it with gateway limits and should not treat it as a global distributed quota.
- `OPENRI_DB_PATH` is a single-node SQLite store. Put it on durable local storage with restrictive permissions and backups; do not share the same database file across multiple application nodes.

## Threat model

OpenRI explicitly considers the following hostile inputs:

- hidden reviewer instructions in PDF/text/HTML
- invisible Unicode control characters
- white or off-page PDF text
- placeholder or hallucinated references
- unsupported or overstated claims
- attempts to weaken reviewer thresholds through author identity or prestige cues
