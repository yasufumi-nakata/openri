# OpenRIのテスト設計

OpenRIは、システム開発もAI reviewer運用も、GPT-5.5、GPT-6.7、Claude、ローカルモデルなど将来変わり得るAI agentで進む前提です。そのため、AIの説明や自己評価ではなく、deterministic test、fixture、golden report、adversarial/metamorphic testで挙動を固定します。

## テストの原則

- 同じ入力なら同じfinding、同じseverity、同じroutingを返す。
- `skipped`、`unknown`、`unsupported`、`not implemented` を `passed` に変換しない。
- 著者名、所属、謝辞、評判、研究室名だけを変えてもfindingが変わらない。
- 外部APIやネットワーク検査は、既定では無効で、明示フラグでだけ実行する。
- PDF、テキスト、API、UIのどの入口でも同じRunReport semanticsを保つ。

## 必須fixture classes

- `clean_transparent_manuscript`: 透明性項目と整合した統計表記を持つ原稿。
- `p_value_mismatch_manuscript`: 検定統計量とp値が一致しない原稿。
- `missing_transparency_manuscript`: ethics/data/code/COI/fundingが不足した原稿。
- `prompt_injection_manuscript`: AI査読を操作する隠し指示を含む原稿。
- `hidden_text_pdf_manuscript`: 白色文字、極小文字、ページ外文字を含むPDF。
- `placeholder_citation_manuscript`: placeholder DOIや参考文献不整合を含む原稿。
- `field_ruleset_omission_manuscript`: CONSORT/PRISMA/MDAR-strict等の必須項目が欠ける原稿。
- `borderline_rounding_manuscript`: strictnessで結果が変わる丸め境界の原稿。

## Golden reports

代表fixtureの `RunReport` JSONを保存し、次を固定します。

- `summary.score`、`failed`、`warnings`、`skipped`。
- `findings[].check_id/status/severity/evidence`。
- `submission_processing.recommended_route`。
- `ai_review_protocol.run_readiness`、`required_ai_reviews`、`coverage_blockers`。
- `ai_review_protocol.model_agnostic_reviewer_contract`。
- `ai_review_protocol.review_packet.claim_inventory`、`reviewer_tasks`、`adversarial_challenges`。
- `accountability.routing_explanation`、`score_explanation`、`evidence_ledger`、`explainability_gates`。
- SARIFの `ruleId` とlocation。

## Adversarial tests

- 本文、PDF不可視文字、ゼロ幅文字、隠しCSSに、AI査読を褒めさせる指示を混ぜる。
- 有名著者、著名大学、高インパクト誌、流行語を入れてもseverityが緩まないことを確認する。
- unsupported claimを曖昧表現で隠した原稿を、warning以上またはcoverage blockerにする。
- 参考文献に実在しないDOI、placeholder DOI、本文claimを支えない引用を混ぜる。
- causal/novel/robust/all users などの強いclaimが、`review_packet.claim_inventory` の `risk_flags` と `support_status` に反映されることを確認する。

## Metamorphic tests

- 著者名・所属・謝辞だけを変えてもfindingが変わらない。
- 段落順序を変えても統計・引用・prompt injection findingが保たれる。
- 同じ本文をTXTとPDFから入力して、検査可能な範囲のfindingが一致する。
- strictnessを上げたとき、検出が弱くならない。
- 著者名・所属だけを変えても `claim_inventory` と `reviewer_tasks` の実質内容が変わらない。

## Regression gates

ローカルで最低限実行するgateです。

```bash
PYTHONPATH=backend python3 -m pytest backend/tests -q
cd frontend && npm run build
```

APIやUIを触った場合は、追加で次を確認します。

- `GET /api/health`
- `GET /api/ai-review-protocol`
- `POST /api/runs`
- Web UIの `Run Text`
- PDF対応を触った場合は `POST /api/runs/upload`

## Cross-model reviewer tests

GPT-5.5、GPT-6.7、Claude、ローカルモデルなど複数のAI reviewerに同じ `ai_review_protocol` を渡して査読させる場合は、多数決で正解にしません。重大findingの不一致は、モデル差ではなく、rubric不足、evidence不足、fixture不足として扱い、テストケースを追加してください。モデル名や世代は監査メタデータであり、閾値や合格条件の分岐に使いません。
# Golden corpus and benchmark gate

The checked-in golden corpus lives under `samples/golden/`, with generated expected reports under `backend/tests/golden_reports/`.

Regenerate after intentional schema/finding changes:

```bash
PYTHONPATH=backend python scripts/update_golden_reports.py
PYTHONPATH=backend python scripts/benchmark_openri.py
```

The benchmark report records recall proxy, precision proxy, routing accuracy proxy, and coverage blocker count. A drop in those metrics should be treated as rubric debt unless the corresponding fixture and acceptance criteria are intentionally changed.

## External peer-review corpus smoke benchmark

Public peer-review datasets do not provide ground-truth labels for OpenRI's integrity findings. Use them as smoke tests for whether OpenRI can process real submissions/reviews and produce useful `review_packet`, routing, and coverage-blocker records.

```bash
PYTHONPATH=backend python scripts/benchmark_peer_review_corpus.py --corpus all --limit 10
```

This benchmark fetches small slices from ReviewBench and PeerSum through the Hugging Face datasets server. The `review_concern_overlap_proxy` is a heuristic comparison between categories mentioned in reviewer text and the categories surfaced by OpenRI findings/tasks. Treat it as an external-corpus coverage signal, not precision/recall for misconduct detection.
