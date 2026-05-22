# OpenRI deployment reference

OpenRI is local-first by default. Hosted deployment must explicitly configure CORS, upload size limits, authentication, data retention, and audit policy before accepting unpublished manuscripts.

## Local Docker compose

```bash
docker compose up --build
curl http://127.0.0.1:8008/api/health
```

The frontend reads `VITE_OPENRI_API_BASE`; local development defaults to `http://127.0.0.1:8008`.

## Configuration

- `OPENRI_CORS_ORIGINS`: comma-separated allowed frontend origins. Wildcard `*` is rejected; configure explicit trusted origins.
- `OPENRI_CORS_ALLOW_CREDENTIALS`: set `true` only when a trusted same-site deployment intentionally uses cookies. Default is `false`; API-key deployments should keep it disabled.
- `OPENRI_UPLOAD_LIMIT_BYTES`: upload size limit. Default is 20 MiB.
- `OPENRI_REQUIRE_API_KEY`: set `true` to require `X-OpenRI-API-Key` for report-producing endpoints.
- `OPENRI_API_KEYS`: comma-separated accepted API keys for small hosted deployments.
- `OPENRI_RATE_LIMIT_PER_MINUTE`: in-process per-client write limit. Use gateway limits for production.
- `OPENRI_RATE_LIMIT_KEY`: `client_ip` by default, or `api_key` to bucket authenticated requests by `X-OpenRI-API-Key`. `api_key` bucketing only applies when `OPENRI_REQUIRE_API_KEY=true` and the key is in `OPENRI_API_KEYS`; otherwise OpenRI falls back to the client IP bucket.
- `OPENRI_TRUST_X_FORWARDED_FOR`: set `true` only behind a trusted reverse proxy that strips untrusted incoming `X-Forwarded-For` headers.
- `OPENRI_RETENTION_DAYS`: delete stored reports older than this during report-producing requests. `0` disables pruning.
- `OPENRI_DB_PATH`: SQLite report store path.
- `OPENRI_CROSSREF_MAILTO`: Crossref contact metadata.
- `OPENRI_CROSSREF_CACHE_DIR`: deterministic DOI lookup cache.

## Hosted security baseline

Use local/dev mode only for trusted local manuscripts. Hosted use should place OpenRI behind TLS, enable API keys or OIDC at the gateway, log report access, set a retention period, and isolate each journal or editorial tenant at the database/storage layer. Built-in API key mode is a small single-tenant guardrail; multi-tenant RBAC belongs at the gateway/OIDC layer. Findings are evidence-backed review tasks, not misconduct determinations.

Reverse proxies should enforce request-size limits before traffic reaches OpenRI. For nginx, set `client_max_body_size` to the same or lower value than `OPENRI_UPLOAD_LIMIT_BYTES`; for other gateways, configure the equivalent total request-body limit. OpenRI also checks `Content-Length`, streams upload reads in chunks, and rejects oversized file payloads, but the gateway remains the first line of defense for very large multipart bodies.

When rate limiting behind a load balancer, prefer `OPENRI_REQUIRE_API_KEY=true` with `OPENRI_RATE_LIMIT_KEY=api_key` for authenticated hosted deployments. Do not rely on arbitrary client-supplied `X-OpenRI-API-Key` values for throttling when API-key authentication is disabled; OpenRI will fall back to the IP bucket in that mode. Use `OPENRI_TRUST_X_FORWARDED_FOR=true` only if the proxy is trusted and removes spoofed client-supplied forwarding headers before forwarding to OpenRI. The built-in limiter is process-local and per worker; production deployments should still enforce gateway-level rate limits.

Do not set `OPENRI_CORS_ORIGINS=*` for public deployments. OpenRI rejects the wildcard at startup because credentials, browser cookies, and API keys must be scoped to explicit trusted origins.

## Production checklist

- Terminate TLS and authentication at a trusted gateway. Run uvicorn with forwarded headers only for proxy IPs you control, for example `uvicorn openri.api:app --proxy-headers --forwarded-allow-ips 127.0.0.1,10.0.0.0/8`, and keep `OPENRI_TRUST_X_FORWARDED_FOR=false` unless that proxy strips untrusted inbound forwarding headers.
- Treat `OPENRI_RATE_LIMIT_PER_MINUTE` as a per-process, per-worker limit. With four workers, the effective built-in limit can be roughly four times the configured value, so keep a gateway or WAF rate limit as the public control.
- Keep `OPENRI_CORS_ORIGINS` to exact browser origins such as `https://editorial.example.org`; wildcard origins are rejected and should not be reintroduced for credentialed deployments.
- Match gateway body limits to `OPENRI_UPLOAD_LIMIT_BYTES`. For nginx, set `client_max_body_size 20m;` or lower. The app-level limit is a second check after the gateway has accepted the request.
- Put `OPENRI_DB_PATH` on durable local storage with restrictive file permissions and backups. The SQLite store uses short-lived connections with WAL and a busy timeout for single-node use; do not point multiple independent nodes at the same database file over network storage.

Runtime policy is visible at:

```bash
curl http://127.0.0.1:8008/api/security-policy
```
