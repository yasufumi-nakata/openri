# AGENTS.md

このディレクトリは **OpenRI (Open Research Integrity)** のプロトタイプです。Codex、Claude Code、その他のAI coding agentが作業するときは、この文書を最初に読んでください。

## 応答方針

- ユーザーへの返答は必ず日本語の敬語で行ってください。
- OpenRIのfindingは「研究不正の断定」ではなく、「人間が確認すべき証拠付きの検査結果」として扱ってください。
- OpenRIは、人間査読で確認される論点をCodex/Claude等のAI reviewerが分野非依存・証拠優先・忖度なしで再現できるようにするための基盤です。
- 未公開原稿や個人情報を外部APIへ送る変更は、明示的な許可なしに追加しないでください。
- 既存の検査範囲を狭める、サンプルを弱くする、APIレスポンスの証拠情報を落とす変更は避けてください。

## プロジェクトの目的

OpenRIは、プログラミングにおけるテストランナー/CIに近い形で、投稿システムに提出された論文に対して機械的な検査を走らせるOSS基盤です。対象は、統計不整合、研究透明性の不足、引用・参考文献の不整合、LLM査読を操作する隠し指示、PDF不可視テキスト、ruleset準拠、再現性リスクなどです。

重要なのは、OpenRIが「採否判定エンジン」や「不正認定エンジン」ではないことです。APIとUIは、検査ID、severity、status、score、message、recommendation、evidenceに加え、`submission_processing` として編集部トリアージの推奨処理ルート、`ai_review_protocol` としてAI reviewer assignment、分野非依存査読軸、忖度なしpolicy、AI開発前提のテスト設計を返します。

## 現在の構成

- `backend/openri/`: Python/FastAPIの本体です。
- `backend/openri/checks.py`: 各検査の実装と`CHECKS`登録リストです。
- `backend/openri/analyzer.py`: 原稿profile作成、check実行、summary計算を行います。
- `backend/openri/api.py`: Web UIが叩くFastAPI APIです。
- `backend/openri/cli.py`: `openri check/list/show` のCLIです。
- `backend/openri/rulesets/`: YAML rulesetです。prompt injection、CONSORT、PRISMA、MDAR strictなどをここで拡張します。
- `backend/openri/sarif.py`: GitHub Code Scanning向けSARIF変換です。
- `backend/openri/store.py`: report保存用SQLite storeです。
- `frontend/`: React + ViteのWeb UIです。
- `samples/`: 動作確認用の原稿サンプルです。
- `docs/`: GitHub Actions連携、Buffy連携、新規check作成ガイドです。
- `docs/submitted-manuscript-workflow.md`: 提出された論文をどう処理するかの中心ドキュメントです。
- `docs/ai-review-protocol.md`: Codex/Claude等のAI reviewerで人間査読の論点を再現するプロトコルです。
- `docs/testing-strategy.md`: AIが実装する前提でのfixture、golden report、adversarial/metamorphic test設計です。

## 起動と確認

API:

```bash
PYTHONPATH=backend python3 -m uvicorn openri.api:app --host 127.0.0.1 --port 8008
```

Web UI:

```bash
cd frontend
npm install
npm run dev -- --host 127.0.0.1 --port 5173
```

テスト:

```bash
PYTHONPATH=backend python3 -m pytest backend/tests -q
cd frontend && npm run build
```

CLI smoke:

```bash
PYTHONPATH=backend python3 -m openri.cli check samples/high_risk_manuscript.txt
```

## 実装ルール

- Pythonは`pyproject.toml`どおり `>=3.9` 互換を維持してください。`str | None` のようなPython 3.10+前提の型注釈は避け、必要なら `typing.Optional` / `typing.List` などを使ってください。
- 新しいcheckは、原則として `docs/writing-checks.md` の手順に従って追加してください。
- check結果には、できる限り `Evidence(quote=..., location=..., data=...)` を付けてください。単なるスコアだけの判定は避けてください。
- AIが実装した変更は、説明だけで正しい扱いにせず、deterministic test、fixture、golden report、API smoke、UI smokeのいずれかで固定してください。
- `skipped`、`unknown`、`unsupported`、`not implemented` は合格扱いにしないでください。coverage blockerまたは明示的な未対応として残してください。
- ネットワークを使う検査は、必ず明示フラグや設定で制御できるようにしてください。既定で未公開原稿を外部送信しないでください。
- PDF/画像/外部DB照合などの重い検査は、失敗しても他のcheckが止まらないように分離してください。
- UIは研究支援ツールとして、密度は保ちつつ読みやすいダッシュボードにしてください。マーケティング用ランディングページへ寄せないでください。
- API互換性を崩す場合は、READMEとUIのAPI表示も同時に更新してください。

## 追加開発の優先順位

v0.4.0までに、画像のEXIF・編集ソフト痕跡・重複領域の初期検査、APA統計表記の拡張(χ²/r/自由度なしz)、STROBE/ARRIVE/CARE/CHEERS/TRIPOD ruleset、番号・著者-年両形式の引用対応検査を実装済みです。残りの優先順位:

1. APA統計カバレッジの続き(複数行表記、表内統計量)。
2. 画像検査の深化(切り貼り境界、圧縮アーティファクト、ELA相当)。
3. 効果量・信頼区間・p値の相互整合再計算(現状はcoverage blocker)。
4. OpenAlex / Semantic Scholarによる引用文脈検証(opt-in)。
5. 参考文献リストのメタデータ抽出と引用整合クロスチェックの強化。

## 作業完了前の確認

- `PYTHONPATH=backend python3 -m pytest backend/tests -q`
- `cd frontend && npm run build`
- APIを触った場合は `GET /api/health` と `POST /api/runs` のsmoke確認。
- UIを触った場合は `http://127.0.0.1:5173/` で `Run Review Tests` が動くことを確認。
