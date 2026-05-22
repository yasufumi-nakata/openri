# AI査読プロトコル

OpenRIの `ai_review_protocol` は、Codex、Claude、その他のAI reviewerに、人間査読で本来確認される論点を厳格に実行させるためのrubricです。目的は採否の自動決定ではなく、分野非依存に確認できる論点を証拠付きで潰し、著者名・所属・評判・人間関係による閾値変更を排除することです。

## 基本原則

- **No social leniency**: 著者、所属、共同研究関係、研究室、流行テーマで基準を緩めません。
- **Evidence first**: claim、方法、数値、引用、限界、倫理、再現性を証拠に紐づけます。
- **Blocked is not passed**: `skipped`、未検査、PDF抽出不能、ruleset未指定、network無効は安全扱いにしません。
- **External LLM off by default**: 未公開原稿を外部LLM/APIへ送ることを既定にしません。
- **Field-neutral core first**: 分野別rulesetの前に、どの研究にも共通するcore review axisを通します。

## 初回公開時の限界

- 画像改ざん検査は未実装です。図表参照がある場合は `image_integrity_placeholder` として、未検査領域をcoverage blockerに残します。
- rulesetはキーワード照合です。CONSORT/PRISMA/MDAR-strict等の完全な専門査読ではなく、記載漏れ候補の検出として扱います。
- 引用文脈がclaimを本当に支えるかの意味的検証はまだ行いません。DOI実在性照合も、未公開原稿の外部送信を避けるため既定では無効です。
- AI reviewerへの外部LLM送信は既定で不要です。送信する場合は、許可、送信範囲、送信先、保存期間、削除方針を別途固定してください。

## AI reviewer roles

- `field_generalist`: claim、論理構造、先行研究との位置づけ、結論の強さを見ます。
- `methodology_reviewer`: 研究デザイン、測定、サンプリング、除外、交絡、代替説明を見ます。
- `statistics_reviewer`: 検定、効果量、信頼区間、サンプルサイズ、丸め、表本文の整合性を見ます。
- `reproducibility_reviewer`: データ、コード、材料、プロトコル、補足資料、実行環境を見ます。
- `ethics_integrity_reviewer`: 倫理、同意、COI、資金、画像/PDF/引用/AI safetyを見ます。
- `adversarial_reviewer`: 反証、欠落、過剰claim、隠し指示、再現不能な部分を探します。

## Universal review dimensions

1. `claim_evidence_alignment`: 主要claimが結果、図表、引用、限界記述で支えられているか。
2. `method_validity`: 研究デザイン、対象、測定、除外、交絡、代替説明がclaimに見合うか。
3. `statistical_soundness`: 数値、検定、効果量、丸め、表本文の整合性に破綻がないか。
4. `reproducibility`: データ、コード、材料、プロトコル、実行環境を第三者が追跡できるか。
5. `citation_support`: 引用が実在し、引用文脈が本文claimを本当に支えているか。
6. `ethics_transparency`: 倫理、同意、COI、資金、登録、透明性項目が明示されているか。
7. `limitations_and_scope`: 限界、外的妥当性、失敗条件、反証可能性がclaimを適切に縛っているか。
8. `adversarial_failure_modes`: prompt injection、不可視テキスト、画像/PDF加工、重複、過剰claimを含まないか。

## Report fields

`POST /api/runs` と `POST /api/runs/upload` のreportには `ai_review_protocol` と `accountability` が入ります。

- `run_readiness`: AI査読へ進めるか、重大findingで止めるか、coverage blocker付きで進めるか。
- `required_ai_reviews`: 実行すべきAI reviewer role。
- `coverage_blockers`: 未検査・不明・unsupportedな領域。
- `finding_review_instructions`: findingごとにAI reviewerへ渡す確認指示。
- `test_design`: AIが開発・査読する前提のunit、fixture、golden、adversarial、metamorphic、cross-model、regression gate。
- `review_packet`: この原稿固有のclaim inventory、reviewer tasks、adversarial challenges、editor handoff。

`accountability` は、AI reviewerや編集部が「なぜこのroute/scoreになったか」を追跡する説明責任レコードです。

- `decision_provenance`: strictness、network有無、ruleset、外部LLM不要、入力サイズ。
- `routing_explanation`: recommended route、rationale、route driver finding、coverage blocker。
- `score_explanation`: score算定式、平均finding score、strictness/failed/warning/skipped penalty、worst findings。
- `evidence_ledger`: findingごとのevidence品質、quote/location/data、primary evidence、recommendation。
- `claim_explainability`: claim数、support_status分布、risk_flag分布、support不足claim。
- `human_accountability`: handling editor、統計担当、research integrity担当、著者への確認責任と照会キュー。
- `explainability_gates`: warning/failed findingにevidenceがあるか、skippedを安全扱いしていないか。

## Review packet

`review_packet` は、rubricを実際の査読作業へ落とすための原稿固有パケットです。

- `claim_inventory`: 強いclaim候補を `id`, `quote`, `location`, `section`, `claim_type`, `support_status`, `linked_findings`, `risk_flags` で固定します。
- `reviewer_tasks`: AI reviewer roleごとに、確認すべきclaim、finding、coverage blocker、出力schema、acceptance gateを渡します。
- `adversarial_challenges`: claimやfindingに対し、反証、代替説明、著者照会、最弱の支持可能表現を強制的に返させる課題です。
- `editor_handoff`: claim数、task数、challenge数をまとめ、編集部がどこまでAI査読に回せるかを確認します。

claim抽出は不正断定ではありません。最初は保守的なheuristicで主要claim候補を出し、`support_status: needs_review` を基本にします。抽出漏れや誤検出は、人間またはAI reviewerが補正する対象です。

## Codex/Claudeに渡すときの最小入力

AI reviewerには、少なくとも次を渡してください。

1. 原稿本文または許可済み抽出テキスト。
2. OpenRIの `findings`。
3. `ai_review_protocol.universal_review_dimensions`。
4. `coverage_blockers`。
5. `review_packet.claim_inventory` と `review_packet.reviewer_tasks`。
6. 「採否ではなく、証拠付きの査読論点、重大欠落、著者照会案を返す」という制約。

未公開原稿を外部サービスへ送る場合は、送信範囲、送信先、保存期間、削除方針、許可ログを明示してください。
