# 自分の論文をOpenRIでチェックすると何が起きるか

OpenRIにPDFまたはテキスト原稿を渡すと、採否判定や不正断定ではなく、機械的に再確認できるfindingを返します。
同時に、GPT-5.5、GPT-6.7、Claude、ローカルモデルなど将来変わり得るAI reviewer/AI editorが、査読論点を分野非依存・証拠優先・忖度なしで見るための `ai_review_protocol` も返します。

## PDFの場合

1. サーバー側でPDF本文を抽出します。
2. 抽出テキストに対して、p値再計算、GRIM風の平均値/n整合性、透明性項目、引用/DOI、prompt injection、重複表現、rulesetなどを検査します。
3. PDFそのものに対して、白色文字、極小フォント、ページ外配置などの不可視/隠しテキスト候補を検査します。
4. 結果はWeb UIとAPIの同じJSON reportで確認できます。

スキャン画像だけのPDFや、本文抽出できないPDFは現時点では検査できません。その場合はOCRを先に通すか、本文テキストも併せて入力してください。

## 出る結果

- `score`: 0-100の目安です。低いほどAI判断前の追加検査やcoverage blocker解消が必要です。
- `passed`: 既知の機械検査で問題が見つからなかった項目です。
- `warning`: 不足・不整合・未実装範囲など、確認すべき項目です。
- `failed`: p値不整合や隠し指示など、重大な再確認対象です。
- `skipped`: ネットワーク検査やPDF専用検査など、条件不足で走らなかった項目です。
- `evidence`: 原稿中の該当引用、行番号、再計算値、検出パターンなどです。
- `ai_review_protocol`: AI reviewer role、universal review dimensions、coverage blocker、model-agnostic contract、AI開発前提のテスト設計です。

## 現時点で検出できる代表例

- `t(58) = 2.15, p = 0.003` のような報告p値を再計算し、実際のp値との差を示します。
- `M = 2.34, n = 17` のような平均値/n表記が、整数項目の平均としてあり得るかを確認します。
- ethics、data availability、code availability、conflict of interest、fundingの記載漏れ候補を出します。
- placeholder DOIや参考文献セクション不足を検出します。
- `Ignore previous instructions` のようなLLM査読操作の隠し指示を検出します。
- PDF内の白色文字・極小フォント・ページ外テキストを検出します。

## Web UIでの使い方

1. http://127.0.0.1:5173/ を開きます。
2. `PDF / text upload` でPDFを選択します。
3. `Run PDF/File` を押します。
4. Findings Summary、Review Checks、Evidenceを確認します。

## APIでの使い方

```bash
curl -X POST http://127.0.0.1:8008/api/runs/upload \
  -F file=@manuscript.pdf \
  -F strictness=standard
```

PDFではなくテキストを直接送る場合:

```bash
curl -X POST http://127.0.0.1:8008/api/runs \
  -H 'Content-Type: application/json' \
  --data '{"title":"paper","manuscript_text":"Results\n t(58) = 2.15, p = 0.003.","strictness":"standard"}'
```

## 注意

OpenRIは「不正です」と断定しません。あくまで、AI reviewer/AI editorが判断前に扱うべき場所を証拠付きで出すテストランナーです。特にp値、引用、透明性項目、PDF不可視テキストは、原稿の文脈や分野ルールに応じてAI判断の入力として明示的に処理してください。
ただし、`ai_review_protocol.strictness_policy` は、著者名、所属、評判、流行テーマによる好意的な閾値変更を禁止します。`skipped` や未対応領域は安全ではなく、coverage blockerとして扱ってください。
