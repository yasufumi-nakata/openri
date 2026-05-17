# OpenRI と Buffy (JOSS / openjournals) の連携

Buffy は openjournals / JOSS / JOSE が使う editorial bot で、`@editor-bot openri-check`
のような issue コマンドからアクションを起動する。下は OpenRI を呼ぶサンプル設定。

## 1. Buffy 側の responder 追加

`buffy/config.yml`(Buffy リポジトリ側) にカスタム responder を追加する例:

```yaml
- responder: openri_check
  command: openri-check
  description: Run OpenRI on the submitted manuscript
  template_file: openri_check.md.erb
  external_call:
    command: bash .buffy/openri.sh "{{ checkpoint.url }}" "{{ issue_id }}"
    timeout: 300
    log_file: tmp/openri.log
```

## 2. 実行スクリプト

`.buffy/openri.sh`:

```bash
#!/usr/bin/env bash
set -euo pipefail

REPO_URL="$1"
ISSUE_ID="$2"

WORK=$(mktemp -d)
git clone --depth 1 "$REPO_URL" "$WORK/manuscript"
cd "$WORK/manuscript"

# manuscript path 慣行: paper.md (JOSS) / paper.pdf (JOSE)
TARGET="paper.md"
[ -f paper.pdf ] && TARGET="paper.pdf"

openri check "$TARGET" \
  --strictness standard \
  --ruleset mdar_strict \
  --json > "$WORK/report.json"

python - <<'PY' > "$WORK/comment.md"
import json, pathlib, os
report = json.loads(pathlib.Path(os.environ["WORK"] + "/report.json").read_text())
findings = report["findings"]
summary = report["summary"]
print(f"### OpenRI report (score {summary['score']}/100)")
print()
print(f"failed={summary['failed']} warnings={summary['warnings']} passed={summary['passed']} skipped={summary['skipped']}")
print()
for f in findings:
    if f["status"] in {"warning", "failed"}:
        print(f"- **{f['title']}** ({f['severity']}): {f['message']}")
PY

WORK="$WORK" cat "$WORK/comment.md"
```

## 3. issue へのコメント

Buffy はスクリプトの stdout を issue にコメントとして投稿する。`paper.md` に
prompt-injection や統計不整合があれば、JOSS editor が気付ける形になる。

## メモ

- 公開 preprint / 投稿原稿が対象なら、Crossref/OpenAlex連携(--network)も解禁してよい。
- 査読中の未公開原稿に対して外部 API を叩く場合は、出版社/会議のポリシーを確認のこと。
- editorial bot 経由なら、bot のホスト環境が信頼境界の内側にあるので、機密性の制約は緩い。
