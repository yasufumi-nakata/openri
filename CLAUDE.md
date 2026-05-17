# CLAUDE.md

このリポジトリは **OpenRI (Open Research Integrity)** です。Claude Codeで作業する場合も、まず [`AGENTS.md`](AGENTS.md) を読んでください。

## 短い要約

OpenRIは、投稿システムに提出された論文に対するOSSの研究公正テストランナーです。プログラミングのCIのように、統計不整合、透明性不足、引用リスク、PDF不可視テキスト、LLM査読操作の隠し指示、ruleset準拠などを検査し、証拠付きfindingと編集部トリアージ用の `submission_processing` を返します。

これは研究不正の断定や採否判定ではありません。ただし、人間査読で本来確認される論点をClaude/Codex等のAI reviewerが分野非依存・証拠優先・忖度なしで再現することを主目的にします。`ai_review_protocol` にはreviewer role、universal review dimensions、no-social-leniency policy、AI開発前提のテスト設計が入ります。

## よく触る場所

- `backend/openri/checks.py`: 新しい検査を追加する場所。
- `backend/openri/models.py`: API/reportのデータ構造。
- `backend/openri/analyzer.py`: checkの実行とsummary計算。
- `backend/openri/api.py`: FastAPI API。
- `frontend/src/main.jsx`: Web UI本体。
- `frontend/src/styles.css`: Web UIのスタイル。
- `backend/openri/rulesets/*.yaml`: YAML ruleset。
- `docs/writing-checks.md`: 新規check追加ガイド。
- `docs/ai-review-protocol.md`: AI reviewerで査読論点を再現するプロトコル。
- `docs/testing-strategy.md`: AIが実装する前提のテスト設計。

## 主要コマンド

```bash
PYTHONPATH=backend python3 -m pytest backend/tests -q
cd frontend && npm run build
PYTHONPATH=backend python3 -m uvicorn openri.api:app --host 127.0.0.1 --port 8008
cd frontend && npm run dev -- --host 127.0.0.1 --port 5173
```

Python 3.9互換を維持してください。未公開原稿を外部APIへ送る機能は、明示的な許可なしに既定有効化しないでください。
AIが書いた変更は、説明だけで通さず、deterministic test、fixture、golden report、API/UI smokeのいずれかで固定してください。`skipped` や未対応領域を合格扱いに変えないでください。
