# 提出された論文の処理フロー

OpenRIの主眼は、著者が自分の原稿を軽く点検することではなく、投稿システムに提出された論文を編集部側でどのように扱い、Codex/Claude等のAI reviewerにどの論点を厳格に査読させるかです。

## 基本方針

- OpenRIは採否を自動決定しません。
- OpenRIは研究不正を自動断定しません。
- OpenRIは採否を自動決定する査読者ではありませんが、人間査読で本来確認される論点をAI reviewerが分野非依存に再現できるプロトコルを作ります。
- OpenRIは、通常査読またはAI査読へ回す前に編集部が確認すべき機械的findingとcoverage blockerを作ります。
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
   - `ai_review_protocol` を作り、Codex/Claude等へ渡す reviewer role、universal review dimensions、no-social-leniency policy、coverage blocker、テスト設計を固定します。
   - `skipped`、`unknown`、`unsupported` は安全扱いにせず、blockedまたは未検査として残します。
   - 未公開原稿を外部LLM/APIへ送ることは既定にしません。

5. **編集部トリアージ**
   - `integrity_hold_before_peer_review`: 通常査読前にresearch integrity担当へ保留。
   - `statistics_editor_screen`: 統計担当またはhandling editorが先に確認。
   - `technical_check_then_peer_review`: 事務局/編集部の技術チェック後に通常査読。
   - `route_to_peer_review`: 重大findingなしとしてAI査読/通常査読へ回付可能。

6. **確認パケット**
   - check ID、severity、status、該当行/ページ、再計算値、recommendation、required AI reviewerをまとめてhandling editorに渡します。
   - `accountability` にroute driver、score算定、evidence ledger、責任分担、著者照会キューを残します。
   - 著者照会、統計確認、integrity確認、AI査読/通常査読への回付を決めます。

## APIで見るべきフィールド

`POST /api/runs` または `POST /api/runs/upload` のレスポンスには、通常の `summary` と `findings` に加えて `submission_processing`、`ai_review_protocol`、`accountability` が入ります。

```json
{
  "submission_processing": {
    "mode": "submitted_manuscript_triage",
    "recommended_route": "statistics_editor_screen",
    "route_label": "統計担当/handling editorの事前確認",
    "rationale": "報告統計量とp値の不整合があります。",
    "stages": [],
    "human_actions": []
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
    "test_design": {}
  }
}
```

`accountability` は、編集部が説明責任を果たすための監査用フィールドです。

```json
{
  "accountability": {
    "mode": "accountable_explainable_review_record",
    "routing_explanation": {
      "recommended_route": "integrity_hold_before_peer_review",
      "route_drivers": []
    },
    "score_explanation": {
      "formula": "mean(finding.score) - strictness_penalty - 8*failed - 2*warnings"
    },
    "evidence_ledger": [],
    "human_accountability": {}
  }
}
```

## 実運用での扱い

- `prompt_injection` または `pdf_hidden_text` のfailedは、通常査読前の保留対象にします。
- `statistical_consistency` のfailedは、統計担当またはhandling editorの事前確認対象にします。
- `reporting_transparency` や `ruleset_coverage` のwarningは、著者照会や事務局チェックで解消できる可能性があります。
- `claim_evidence_alignment` のwarningは、claimを支える結果、図表、引用、限界、代替説明を1対1で確認する対象にします。
- `citation_integrity` のwarningは、placeholder DOI、参考文献entry、本文中引用番号との対応を確認する対象にします。
- `skipped` は「安全」ではありません。ネットワーク未使用、PDFでない、ruleset未指定など、検査条件が足りないことを示します。
- AI reviewerには、著者や研究室への遠慮ではなく、同じ入力なら同じfindingを出すという基準を守らせます。

## 今後の拡張

- 投稿システムからのwebhook intake。
- 補足資料・画像ファイルの同時アップロード。
- 画像のEXIF、重複領域、切り貼り、圧縮アーティファクト検査。
- editor dashboardでのqueue管理。
- 著者照会テンプレートの生成。
- Codex/Claude等の複数AI reviewerによるcross-model disagreement tracking。
- 分野別rulesetを増やしても、分野非依存core reviewの閾値が崩れないregression test。
