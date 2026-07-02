# AI査読プロトコル

OpenRIの `ai_review_protocol` は、GPT-5.5、GPT-6.7、Claude、ローカルモデルなど将来変わり得るAI reviewer/AI editorに、査読で確認される論点を厳格に実行させるためのrubricです。OpenRI自体は採否判定エンジン本体ではなく、AIが自律判断する運用の前段で、分野非依存に確認できる論点、証拠、coverage blocker、監査ログ要件を固定します。

## 基本原則

- **No social leniency**: 著者、所属、共同研究関係、研究室、流行テーマで基準を緩めません。
- **Evidence first**: claim、方法、数値、引用、限界、倫理、再現性を証拠に紐づけます。
- **Blocked is not passed**: `skipped`、未検査、PDF抽出不能、ruleset未指定、network無効は安全扱いにしません。
- **External LLM off by default**: 未公開原稿を外部LLM/APIへ送ることを既定にしません。
- **Field-neutral core first**: 分野別rulesetの前に、どの研究にも共通するcore review axisを通します。
- **Model-agnostic execution**: モデル名や世代を品質の根拠にせず、同じ `review_packet`、acceptance gate、evidence ledgerで比較します。

## 現時点の限界(v0.4.0)

- 画像検査(`image_integrity`)はEXIFメタデータ(編集ソフト痕跡を含む)、圧縮形式、単純な重複領域候補の初期検査です。切り貼り境界、圧縮アーティファクト、ELA相当の深い検査はreviewer taskとして残ります。画像未提出でPDF内画像や図参照だけがある場合はcoverage blockerになります。
- rulesetはキーワード照合です。CONSORT/PRISMA/MDAR-strict/STROBE/ARRIVE等の完全な専門査読ではなく、記載漏れ候補の検出として扱います。
- 引用対応は、本文中引用(番号/著者-年)と参考文献entryの機械的照合までです。引用文脈がclaimを本当に支えるかの意味的検証はまだ行いません。DOI実在性照合も、未公開原稿の外部送信を避けるため既定では無効です。
- 効果量と信頼区間は抽出のみで、p値・サンプルサイズとの相互整合再計算は未対応です(coverage blockerとして残ります)。
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
- `model_agnostic_reviewer_contract`: AI reviewer/AI editorが満たすべき構造化出力、証拠紐づけ、coverage blocker尊重、監査ログのcapability contract。

`accountability` は、AI reviewer/AI editorが「なぜこのroute/scoreになったか」を追跡する説明責任レコードです。

- `decision_provenance`: strictness、network有無、ruleset、外部LLM不要、入力サイズ。
- `routing_explanation`: recommended route、rationale、route driver finding、coverage blocker。
- `score_explanation`: score算定式、平均finding score、strictness/failed/warning/skipped penalty、worst findings。
- `evidence_ledger`: findingごとのevidence品質、quote/location/data、primary evidence、recommendation。
- `claim_explainability`: claim数、support_status分布、risk_flag分布、support不足claim。
- `autonomous_ai_accountability`: AIが最終判断する運用で必要な判断入力、モデル実行メタデータ、fail-closed条件。
- `human_accountability`: 既存UI/API互換のため残すlegacy accountability block。主経路は `autonomous_ai_accountability` です。
- `explainability_gates`: warning/failed findingにevidenceがあるか、skippedを安全扱いしていないか。

## Review packet

`review_packet` は、rubricを実際の査読作業へ落とすための原稿固有パケットです。

- `claim_inventory`: 強いclaim候補を `id`, `quote`, `location`, `section`, `claim_type`, `support_status`, `linked_findings`, `risk_flags` で固定します。
- `reviewer_tasks`: AI reviewer roleごとに、確認すべきclaim、finding、coverage blocker、出力schema、acceptance gateを渡します。
- `adversarial_challenges`: claimやfindingに対し、反証、代替説明、著者照会、最弱の支持可能表現を強制的に返させる課題です。
- `editor_handoff`: claim数、task数、challenge数をまとめ、AI reviewer/AI editorがどこまで判断可能かを確認します。

claim抽出は不正断定ではありません。最初は保守的なheuristicで主要claim候補を出し、`support_status: needs_review` を基本にします。抽出漏れや誤検出は、AI reviewer/AI editorまたは任意の監査担当が補正する対象です。

## モデル非依存の最小入力

AI reviewerには、少なくとも次を渡してください。

1. 原稿本文または許可済み抽出テキスト。
2. OpenRIの `findings`。
3. `ai_review_protocol.universal_review_dimensions`。
4. `coverage_blockers`。
5. `review_packet.claim_inventory` と `review_packet.reviewer_tasks`。
6. `model_agnostic_reviewer_contract`。
7. `provider`, `model_name`, `model_version_or_snapshot`, `prompt_or_policy_version`, `run_id`, `timestamp`。
8. 「証拠なしにpassedへ進めない、coverage blockerを無視しない、fail-closed条件に該当したら判断を止める」という制約。

未公開原稿を外部サービスへ送る場合は、送信範囲、送信先、保存期間、削除方針、許可ログを明示してください。
