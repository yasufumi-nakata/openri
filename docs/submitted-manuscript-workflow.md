# 提出された論文の処理フロー

OpenRIの主眼は、著者が自分の原稿を軽く点検することではなく、投稿システムに提出された論文を、GPT-5.5、GPT-6.7、Claude、ローカルモデルなど将来変わり得るAI reviewer/AI editorへ渡す前に、どの証拠・制約・coverage blockerで縛るかです。

## 基本方針

- OpenRI自体は採否を自動決定しません。
- OpenRIは研究不正を自動断定しません。
- OpenRIは採否判定エンジン本体ではありませんが、AI reviewer/AI editorが自律判断する運用で、査読論点を分野非依存に再現できるプロトコルを作ります。
- OpenRIは、AI reviewer/AI editorが判断する前に必ず扱うべき機械的findingとcoverage blockerを作ります。
- 分野、著者属性、所属、評判、流行テーマではなく、検査可能な記述、証拠、欠落に対して同じ基準を適用します。
- 好意的解釈や有名著者への忖度を入れず、findingはevidenceとrecommendationで返します。

## 処理ステージ

1. **提出受付**
   - 投稿システムからPDF、本文、補足資料、メタデータを受け取ります。
   - 元ファイルは証跡として保持し、検査はコピーに対して行います。

2. **本文/PDF抽出**
   - PDF/TXT/TeX/Markdownから検査用テキストを作ります。
   - PDFでは白色文字、極小フォント、ページ外配置など、LLM査読操作に使われ得る不可視テキストも見ます。

3. **機械検査**
   - p値再計算、GRIM風の平均値/n整合性、透明性項目、引用/参考文献対応、claim-evidence対応、prompt injection、ruleset coverageを走らせます。
   - ネットワーク検査は明示的に有効化された場合だけ行います。

4. **AI査読プロトコル化**
   - `ai_review_protocol` を作り、モデル名や世代に依存しない reviewer role、universal review dimensions、no-social-leniency policy、coverage blocker、テスト設計、model-agnostic contractを固定します。
   - `skipped`、`unknown`、`unsupported` は安全扱いにせず、blockedまたは未検査として残します。
   - 未公開原稿を外部LLM/APIへ送ることは既定にしません。

5. **AI判断トリアージ**
   - `integrity_hold_before_peer_review`: AI判断前にresearch integrity確認へ保留。
   - `statistics_editor_screen`: AI判断前に統計整合性を確認。
   - `technical_check_then_peer_review`: 技術チェック後にAI査読へ回付。
   - `route_to_peer_review`: 重大findingなしとしてAI査読へ回付可能。

6. **AI判断ガードレールパケット**
   - check ID、severity、status、該当行/ページ、再計算値、recommendation、required AI reviewerをまとめてAI reviewer/AI editorに渡します。
   - `accountability` にroute driver、score算定、evidence ledger、AI判断に必要な実行メタデータ、fail-closed条件、著者照会キューを残します。
   - 著者照会、統計確認、integrity確認、AI査読継続可否をAI判断の前提条件として固定します。

## APIで見るべきフィールド

`POST /api/runs` または `POST /api/runs/upload` のレスポンスには、通常の `summary` と `findings` に加えて `submission_processing`、`ai_review_protocol`、`accountability` が入ります。

```json
{
  "submission_processing": {
    "mode": "submitted_manuscript_triage",
    "recommended_route": "statistics_editor_screen",
    "route_label": "AI判断前の統計整合性確認",
    "rationale": "報告統計量とp値の不整合があります。",
    "stages": [],
    "human_actions": [],
    "review_actions": []
  }
}
```

`ai_review_protocol` は次の形で、AI reviewerが査読を再現するためのrubricとテスト設計を返します。

```json
{
  "ai_review_protocol": {
    "mode": "ai_reviewer_replication",
    "strictness_policy": {
      "no_social_leniency": true,
      "blocked_is_not_passed": true
    },
    "required_ai_reviews": ["field_generalist", "methodology_reviewer", "adversarial_reviewer"],
    "coverage_blockers": [],
    "model_agnostic_reviewer_contract": {},
    "test_design": {}
  }
}
```

`accountability` は、AI reviewer/AI editorが判断根拠を追跡できるようにする監査用フィールドです。

```json
{
  "accountability": {
    "mode": "accountable_explainable_review_record",
    "routing_explanation": {
      "recommended_route": "integrity_hold_before_peer_review",
      "route_drivers": []
    },
    "score_explanation": {
      "formula": "mean(non-skipped finding.score) - strictness_penalty - 8*failed - 2*warnings - skipped_penalty"
    },
    "evidence_ledger": [],
    "autonomous_ai_accountability": {},
    "human_accountability": {}
  }
}
```

## 実運用での扱い

- `prompt_injection` または `pdf_hidden_text` のfailedは、AI判断前の保留対象にします。
- `statistical_consistency` のfailedは、AI判断前の統計整合性確認対象にします。
- `reporting_transparency` や `ruleset_coverage` のwarningは、著者照会や事務局チェックで解消できる可能性があります。
- `claim_evidence_alignment` のwarningは、claimを支える結果、図表、引用、限界、代替説明を1対1で確認する対象にします。
- `citation_integrity` のwarningは、placeholder DOI、参考文献entry、本文中引用番号との対応を確認する対象にします。
- `skipped` は「安全」ではありません。ネットワーク未使用、PDFでない、ruleset未指定など、検査条件が足りないことを示します。
- AI reviewer/AI editorには、著者や研究室への遠慮ではなく、同じ入力なら同じfindingとcoverage blockerを扱うという基準を守らせます。

## 今後の拡張

- 投稿システムからのwebhook intake。
- 補足資料・複数画像ファイルの同時アップロード(単一画像のEXIF・編集ソフト痕跡・重複領域検査はv0.4.0で対応済み)。
- 画像検査の深化(切り貼り境界、圧縮アーティファクト、ELA相当)。
- editor dashboardでのqueue管理。
- 著者照会テンプレートの生成。
- GPT-5.5、GPT-6.7、Claude、ローカルモデルなど複数AI reviewerによるcross-model disagreement tracking。
- 分野別rulesetを増やしても、分野非依存core reviewの閾値が崩れないregression test。
