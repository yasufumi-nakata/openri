# OpenRI deployment reference

OpenRI is local-first by default. Hosted deployment must explicitly configure CORS, upload size limits, authentication, data retention, and audit policy before accepting unpublished manuscripts.

## Local Docker compose

```bash
docker compose up --build
curl http://127.0.0.1:8008/api/health
```

The frontend reads `VITE_OPENRI_API_BASE`; local development defaults to `http://127.0.0.1:8008`.

## Configuration

- `OPENRI_CORS_ORIGINS`: comma-separated allowed frontend origins.
- `OPENRI_UPLOAD_LIMIT_BYTES`: upload size limit. Default is 20 MiB.
- `OPENRI_REQUIRE_API_KEY`: set `true` to require `X-OpenRI-API-Key` for report-producing endpoints.
- `OPENRI_API_KEYS`: comma-separated accepted API keys for small hosted deployments.
- `OPENRI_RATE_LIMIT_PER_MINUTE`: in-process per-client write limit. Use gateway limits for production.
- `OPENRI_RETENTION_DAYS`: delete stored reports older than this during report-producing requests. `0` disables pruning.
- `OPENRI_DB_PATH`: SQLite report store path.
- `OPENRI_CROSSREF_MAILTO`: Crossref contact metadata.
- `OPENRI_CROSSREF_CACHE_DIR`: deterministic DOI lookup cache.

## Hosted security baseline

Use local/dev mode only for trusted local manuscripts. Hosted use should place OpenRI behind TLS, enable API keys or OIDC at the gateway, log report access, set a retention period, and isolate each journal or editorial tenant at the database/storage layer. Built-in API key mode is a small single-tenant guardrail; multi-tenant RBAC belongs at the gateway/OIDC layer. Findings are evidence-backed review tasks, not misconduct determinations.

Runtime policy is visible at:

```bash
curl http://127.0.0.1:8008/api/security-policy
```
