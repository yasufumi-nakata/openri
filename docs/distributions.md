# Packages and distributions

OpenRI の配布物は GitHub Releases と GitHub Pages の両方で確認できます。Pages 側は、CI や MCP client から直接取得できる固定 URL を用意するための公開目録です。

## GitHub Pages package registry

配布目録は次の URL です。

https://www.yasufumi.net/openri/packages/

公開対象は次の4種類です。

- Python wheel と source distribution
- npm client package
- MCP server package
- Codex skill archive

## Python package

Python 版は CLI、FastAPI API、ruleset、PDF 検査と Python 3.10 以上向けの PDF 不可視テキスト・画像検査 extra を含みます。

```bash
pip install https://www.yasufumi.net/openri/packages/python/openri-0.3.2-py3-none-any.whl
openri --version
```

checksum と SPDX metadata は `SHA256SUMS` と `openri-release.spdx.json` で公開します。

## npm client package

`@openri/client` は OpenRI API を呼ぶ軽量 ESM client です。Web UI や外部 dashboard から `/api/health` と `/api/runs` を同じ型で扱うために使います。

```bash
npm install https://www.yasufumi.net/openri/packages/npm/openri-client-0.3.2.tgz
```

## MCP server package

`@openri/mcp` はローカル OpenRI API を MCP tool として公開します。既定では `http://127.0.0.1:8008` だけを呼び、未公開原稿を外部 API に送る挙動は追加しません。

```bash
npm install https://www.yasufumi.net/openri/packages/mcp/openri-mcp-0.3.2.tgz
OPENRI_API_BASE=http://127.0.0.1:8008 npx openri-mcp
```

## Codex skill archive

Codex skill は、原稿検査、finding の証拠確認、AI reviewer protocol の読み取りを OpenRI の安全方針に沿って実行するための入口です。

```bash
curl -LO https://www.yasufumi.net/openri/packages/skill/openri-codex-skill-0.3.2.tar.gz
```

## Safety defaults

OpenRI は採否判定や研究不正認定を自動化しません。配布パッケージでも、finding は人間が確認すべき証拠付き検査結果として扱います。ネットワーク照合は opt-in とし、未公開原稿を外部 LLM や外部 API に送る既定値は追加しません。
