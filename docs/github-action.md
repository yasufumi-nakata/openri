# OpenRI を GitHub Actions で走らせる

論文原稿(Markdown / TeX / PDF)を含むリポジトリで pull request ごとに OpenRI を走らせ、
findings を SARIF として **GitHub Code Scanning** に投げ込むと、PR 上で finding が
インラインアノテーションとして表示されます。

```yaml
# .github/workflows/openri.yml
name: OpenRI

on:
  pull_request:
    paths:
      - "**/*.md"
      - "**/*.tex"
      - "**/*.pdf"
      - "manuscript/**"

permissions:
  contents: read
  security-events: write  # SARIF upload

jobs:
  openri:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v6
      - uses: actions/setup-python@v6
        with:
          python-version: "3.11"

      - name: Install OpenRI
        run: |
          python -m pip install --upgrade pip
          pip install "openri[pdf] @ git+https://github.com/your-org/openri@main"

      - name: Run OpenRI
        id: openri
        run: |
          openri check manuscript/main.tex \
            --strictness strict \
            --ruleset consort --ruleset mdar_strict \
            --sarif openri.sarif.json \
            --fail-on high
        continue-on-error: true  # SARIFは常にuploadしたい

      - name: Upload SARIF
        if: always()
        uses: github/codeql-action/upload-sarif@v4
        with:
          sarif_file: openri.sarif.json
          category: openri

      - name: Fail PR if check failed
        if: steps.openri.outcome == 'failure'
        run: |
          echo "OpenRI flagged high-severity findings. See the Code Scanning tab."
          exit 1
```

## 使い分け

- `--strictness strict`: 統計の p 値ズレ tolerance を 0.005、透明性 1 項目欠落で warning。
- `--ruleset consort prisma mdar_strict`: 分野別の項目キーワードを照合。
- `--network`: Crossref で DOI の実在性を確認(レート制限とプライバシーに注意)。
- `--fail-on high`: high 以上の finding があれば exit 1 にする。warning level で止めたい場合は `medium` に。

## ローカルでの再現

```bash
pip install -e ".[pdf,network]"
openri check manuscript/main.pdf --strictness strict --ruleset consort --sarif out.sarif.json
```
