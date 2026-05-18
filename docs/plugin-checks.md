# OpenRI declarative check plugins

OpenRI can load external checks from JSON manifests through `OPENRI_CHECK_PLUGIN_PATHS`.

This first plugin boundary is intentionally declarative: plugins do not execute arbitrary Python code and cannot call external APIs. They emit the same `Finding` schema as built-in checks, so API, CLI, SARIF, golden reports, and review packets can consume them without a separate response shape.

```bash
OPENRI_CHECK_PLUGIN_PATHS=samples/plugin_checks.json \
  openri check samples/high_risk_manuscript.txt
```

Minimal manifest:

```json
{
  "schema": "openri-declarative-check-plugin-v1",
  "checks": [
    {
      "id": "journal_requires_data_accession",
      "title": "Journal data accession policy",
      "category": "journal-policy",
      "description": "Flag journal-specific data availability wording.",
      "maturity": "experimental",
      "severity": "medium",
      "keywords": ["data available on request only"]
    }
  ]
}
```

Security boundary:

- JSON manifests are data only; OpenRI does not import plugin Python modules by default.
- Findings preserve `quote`, `evidence.data.plugin_source`, severity, and recommendation.
- Network-backed plugin behavior requires a future audited adapter and explicit opt-in.
- Journal or field policies should document acceptance criteria and false-positive examples beside the plugin manifest.
