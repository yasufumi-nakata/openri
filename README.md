# OpenRI: Open Research Integrity

[![CI](https://github.com/yasufumi-nakata/openri/actions/workflows/ci.yml/badge.svg)](https://github.com/yasufumi-nakata/openri/actions/workflows/ci.yml)
[![Repository Health](https://github.com/yasufumi-nakata/openri/actions/workflows/oss-health.yml/badge.svg)](https://github.com/yasufumi-nakata/openri/actions/workflows/oss-health.yml)
[![CodeQL](https://github.com/yasufumi-nakata/openri/actions/workflows/codeql.yml/badge.svg)](https://github.com/yasufumi-nakata/openri/actions/workflows/codeql.yml)
[![Tutorial](https://img.shields.io/badge/tutorial-GitHub%20Pages-087f78)](https://www.yasufumi.net/openri/)
[![Packages](https://img.shields.io/badge/packages-Pages%20registry-2f64b8)](https://www.yasufumi.net/openri/packages/)
[![Benchmark](https://img.shields.io/badge/benchmark-golden%20corpus-blue)](benchmark/openri-benchmark.md)
[![Release](https://img.shields.io/github/v/release/yasufumi-nakata/openri)](https://github.com/yasufumi-nakata/openri/releases)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

OpenRIは、投稿システムに提出された論文に対する「査読前テストシステム」です。プログラミングでCIがテスト失敗を返すように、原稿に対して統計不整合、研究透明性の不足、引用・参考文献の不整合、LLM査読を操作する隠し指示、画像検査の未実施リスクなどを、証拠付きfindingとして返します。

このプロトタイプの目的は、査読で本来確認されてきた論点を、GPT-5.5、GPT-6.7、Claude、ローカルモデルなど将来変わり得るAI reviewer/AI editorが、分野非依存・証拠優先・忖度なしで実行できるテスト設計に落とし込むことです。OpenRI自体は不正断定や採否判定の本体にはならず、AIが自律判断する運用の前段で潰すべき論点、coverage blocker、reviewer assignment、再現可能な検査結果、監査可能な判断材料をAPIレスポンスとして返します。処理フローの詳細は [`docs/submitted-manuscript-workflow.md`](docs/submitted-manuscript-workflow.md) と [`docs/ai-review-protocol.md`](docs/ai-review-protocol.md) を参照してください。

## 初期スコープ

- `statistical_consistency`: t/F/χ2/z検定表記からp値を再計算し、報告p値とのズレや有意性判定の反転を検出します。strictness で許容ズレを切り替えます。
- `summary_stat_plausibility`: 平均値とnから、整数項目の平均として不自然な値をGRIM風に検出します。整数項目ヒントの有無で severity を切り替えます。
- `reporting_transparency`: ethics, data availability, code availability, conflicts, funding の存在を確認します。
- `citation_integrity`: DOI、本文中引用、参考文献セクションの機械的不整合を確認します。
- `prompt_injection`: LLM査読を操作する隠し指示、不可視文字、隠しCSSを YAML ruleset から検出します。`OPENRI_PROMPT_INJECTION_RULES` で追加ruleset可。
- `template_text`: 重複段落、近接重複(shingle-Jaccard)、テンプレ表現の過剰反復を検出します。
- `image_integrity`: 画像アップロード時にEXIF、画像形式、重複領域候補を確認し、PDF内画像や本文図参照はcoverage blockerとして残します。
- `doi_existence` (experimental, network): Crossref で本文中のDOIが実在するか確認します。`--network` で有効化。
- `ruleset_coverage` (beta): CONSORT/PRISMA/MDAR-strict など分野別 YAML ruleset の項目キーワードを照合します。`--ruleset` で指定。
- `pdf_hidden_text` (experimental): CLIでPDFを直接渡したとき、白色文字・極小フォント・ページ外配置を検出します。
- `citation_context`: 参考文献リスト、本文中引用、claim-support markerを構造化し、AI review packetへ渡します。

## 構成

- `backend/openri`: FastAPI API、CLI、検査エンジン、SARIF/Crossref/PDF-inspection、SQLite store。
- `backend/openri/rulesets/`: YAML 駆動のruleset (prompt_injection, consort, prisma, mdar_strict)。
- `frontend`: Web UI。原稿テキストを貼り付けて検査を実行し、findings/evidence/API例を確認できます。
- `samples`: 動作確認用サンプル原稿。
- `docs/`: GitHub Action / Buffy 連携サンプル、check 開発ガイド。
- `docs/ai-review-protocol.md`: モデル名や世代に依存しないAI reviewer/AI editorで査読論点を再現するためのプロトコル。
- `docs/testing-strategy.md`: AIが開発する前提でのfixture、golden report、adversarial/metamorphic test設計。

## インストール

GitHub Pages の wheel を使う場合:

```bash
pip install openri-0.3.2-py3-none-any.whl
```

GitHub Pages の配布目録 URL を直接指定する場合:

```bash
pip install https://www.yasufumi.net/openri/packages/python/openri-0.3.2-py3-none-any.whl
```

npm client、MCP server、Codex skill archive は [`Packages and distributions`](https://www.yasufumi.net/openri/distributions/) にまとめています。

PyPI公開後に使う場合:

```bash
pip install "openri[pdf,image,server]"
```

開発版をこのリポジトリから使う場合:

```bash
pip install -e ".[pdf,image,network,server,dev]"
```

`image` extra と PDF不可視テキスト検査は Pillow 12.2 以上を使うため Python 3.10 以上で有効です。Python 3.9 ではコア検査と `pypdf` ベースの PDF テキスト抽出を維持し、画像ファイル単体の画素検査は coverage blocker として返します。

## CLI

```bash
openri check samples/high_risk_manuscript.txt
openri check manuscript.pdf --strictness strict --ruleset consort --ruleset mdar_strict
openri check figure.png --strictness strict
openri check paper.tex --out report.json --sarif out.sarif.json --fail-on high
openri check paper.md --network          # Crossref DOI lookup
openri eval-reviewers codex-review.json claude-review.json --out reviewer-eval.json
openri list --limit 10
openri show <report_id> --json
```

終了コード: 0 = OK / 1 = `--fail-on` 閾値以上の finding あり / 2 = 入力エラー。

## API

```bash
PYTHONPATH=backend uvicorn openri.api:app --reload --port 8008
```

- `GET /api/health` / `GET /api/purpose` / `GET /api/checks`
- `POST /api/runs` / `POST /api/runs/upload`
- `GET /api/ai-review-protocol`
- `GET /api/submission-workflow`
- `GET /api/reports` / `GET /api/reports/{report_id}` / `GET /api/reports/{report_id}/sarif`

報告は SQLite (`OPENRI_DB_PATH`、デフォルト `~/.openri/reports.sqlite3`) に保存されます。

## Web UI

```bash
cd frontend
npm install
npm run dev -- --host 127.0.0.1 --port 5173
```

Web UIでは、本文貼り付けに加えてPDF/TXT/MD/TeXのアップロード検査にも対応しています。PDFの場合は本文抽出に加え、白色文字・極小フォント・ページ外配置などの不可視テキスト候補も検査します。自分の論文を通したときの読み方は [`docs/checking-your-paper.md`](docs/checking-your-paper.md) を参照してください。

公開チュートリアルは GitHub Pages の [`OpenRI Tutorial`](https://www.yasufumi.net/openri/) に置いています。ローカル実行、CLI、Web UI、API、GitHub Actions 連携を順番に確認できます。

実行後のreportには `ai_review_protocol` と `accountability` が入り、次を確認できます。

- `reviewer_pool`: field-generalist、methodology、statistics、reproducibility、ethics/integrity、adversarial reviewerの役割。
- `model_agnostic_reviewer_contract`: GPT-5.5からGPT-6.7のようにモデル世代が変わっても同じ入力・証拠・acceptance gateで扱うためのcapability contract。
- `universal_review_dimensions`: claim-evidence、method validity、statistics、reproducibility、citation support、ethics、limitations、adversarial failure modes。
- `strictness_policy`: 著者名・所属・評判で閾値を変えない、skippedをpassedにしない、未公開原稿を外部LLM/APIへ送らない既定。
- `test_design`: AIが実装する前提でのunit/fixture/golden/adversarial/metamorphic/cross-model/regression gate。
- `review_packet`: 原稿固有のclaim inventory、AI reviewer task、adversarial challenge、editor handoff。
- `accountability.routing_explanation`: recommended routeの理由、route driverになったfinding、coverage blocker。
- `accountability.score_explanation`: score算定式、平均finding score、strictness/failed/warning/skipped penalty。
- `accountability.evidence_ledger`: findingごとのevidence数、quote/location/dataの有無、primary evidence。
- `accountability.autonomous_ai_accountability`: AI reviewer/AI editorが最終判断する運用で必要な入力、モデル実行メタデータ、fail-closed条件。
- `accountability.human_accountability`: 既存UI/API互換のため残すlegacy accountability block。主経路は `autonomous_ai_accountability` です。

## ロードマップ

1. 画像ファイルのEXIF、重複領域、切り貼り、圧縮アーティファクト検査。
2. statcheck相当のAPA統計表記カバレッジ拡張(複数行表記、表内統計量)。
3. STROBE/ARRIVE など追加 ruleset。
4. 分野非依存 core review と分野別 ruleset review の分離を強化。
5. OpenAlex / Semantic Scholar 連携(引用文脈の検証)。
6. 参考文献本体(reference list)のメタデータ抽出と引用整合のクロスチェック。

詳細は [`ROADMAP.md`](ROADMAP.md) と [`docs/`](docs/) を参照(GitHub Actionsへの組み込み、Buffyボット連携、checkの書き方)。

## Benchmark / regression

Golden corpus は `samples/golden/`、固定reportは `backend/tests/golden_reports/` に置きます。公開用の簡易benchmarkは次で生成します。

```bash
PYTHONPATH=backend python scripts/benchmark_openri.py
```

出力は `benchmark/openri-benchmark.json` と `benchmark/openri-benchmark.md` です。CIではrecall proxy、precision proxy、route distribution、coverage blocker countをartifactとして保存します。

公開査読コーパスに対する smoke benchmark は次で生成できます。これは不正検出の正解率ではなく、OpenRIが実際の投稿原稿/査読ログに対して、claim inventory、reviewer tasks、coverage blocker、AI判断トリアージを作れるかを見る外部コーパス検証です。

```bash
PYTHONPATH=backend python scripts/benchmark_peer_review_corpus.py --corpus all --limit 10
```

出力は `benchmark/peer-review-corpus-benchmark.json` と `benchmark/peer-review-corpus-benchmark.md` です。既定では Hugging Face の ReviewBench と PeerSum から少数行だけ取得し、OpenRI finding と実査読コメント中の論点カテゴリの重なりを heuristic proxy として記録します。
取得行は `.openri/benchmark-cache/` にキャッシュされるため、同じ条件の再実行ではネットワーク取得を省略できます。最新行を取り直す場合は `--refresh-cache` を指定してください。

## OSS運用

- 参加方法: [`CONTRIBUTING.md`](CONTRIBUTING.md)
- セキュリティ報告: [`SECURITY.md`](SECURITY.md)
- サポート窓口: [`SUPPORT.md`](SUPPORT.md)
- ガバナンス: [`GOVERNANCE.md`](GOVERNANCE.md)
- メンテナ手順: [`docs/maintainer-guide.md`](docs/maintainer-guide.md)
- Scorecard triage: [`docs/scorecard-triage.md`](docs/scorecard-triage.md)

GitHub上では、CI、Repository Health、CodeQL、Dependency Review、OpenSSF Scorecard、Dependabotを有効化しています。`main` はbranch protectionでCI成功を必須にする運用を想定しています。

## 既知の限界

- 画像検査はEXIF、形式、単純な重複ブロック候補の初期検査です。専門的なELA、raw履歴、顕微鏡画像固有の検査はreviewer taskとして残ります。
- ruleset coverageはevidence-awareなキーワード照合です。否定文やnot applicable方針は記録しますが、記載の品質判定はAI reviewer/AI editor側の文脈確認が必要です。
- 引用文脈の意味的検証はclaim-support markerの構造化までです。Crossref DOI照合は `--network` またはAPIの `enable_network` 明示時だけ実行します。
- OpenRIは不正認定や採否判定エンジン本体にはなりません。重大findingは、AI reviewer/AI editorが自律判断する前に必ず処理すべき証拠付きガードレールとして扱います。

## AI coding agent向け

Codex、Claude Code、その他のcoding agentでこのディレクトリを扱う場合は、まず [`AGENTS.md`](AGENTS.md) と [`CLAUDE.md`](CLAUDE.md) を参照してください。プロジェクト目的、構成、起動方法、検査追加ルール、注意点をまとめています。
