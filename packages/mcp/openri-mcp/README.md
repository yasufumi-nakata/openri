# @openri/mcp

MCP server for running OpenRI checks through a local OpenRI API.

```bash
OPENRI_API_BASE=http://127.0.0.1:8008 npx openri-mcp
```

Tools:

- `openri_health`: checks `/api/health`.
- `openri_check_text`: submits manuscript text to `/api/runs`.

The server calls the configured OpenRI API only. It does not add external LLM or external manuscript transfer behavior.
