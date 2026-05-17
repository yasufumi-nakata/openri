# AI自動査読・論文レビュー支援ライブラリ調査

調査日: 2026-05-17  
範囲: 「論文本体のAI査読」「査読コメント生成」「査読コメントの品質評価」「投稿前チェック」「systematic review支援」「統計・引用・再現性チェック」を含めました。OSSはGitHub/公開コードが確認できるものを優先し、商用・非OSSは公開サンプルや画面例が確認できるものを別枠にしています。

重要な前提:

- 「人類が作ってきたもの全て」を文字通り完全保証することはできません。ここでは、2026-05-17時点でWeb検索、GitHub検索、一次情報、関連論文/データセットから確認できた主要OSSと商用候補を網羅的に整理しています。
- 査読者として未公開原稿を外部LLM/APIに入れることは、出版社・会議の規約違反になる場合があります。著者本人の投稿前レビュー、公開preprint、内部の安全なオンプレ/契約環境、編集部が許可した専用ツールとして使う想定を分けるべきです。
- 現状のAI査読ツールは、人間査読の代替というより「投稿前の赤入れ」「見落とし検出」「引用・統計・形式チェック」「レビュー品質の改善」に使うのが現実的です。

## 結論

まず使うなら、OSSでは次の組み合わせが一番現実的です。

| 目的 | 第一候補 | 理由 |
|---|---|---|
| 汎用の投稿前AI査読 | [OpenAIReview](https://github.com/ChicagoHAI/OpenAIReview) | PDF/DOCX/TeX/Markdown/arXiv URL、複数LLM provider、OCR、可視化、ベンチマークまで揃っています。 |
| 複数LLMの独立査読とメタレビュー | [poldrack/ai-peer-review](https://github.com/poldrack/ai-peer-review) | 個別レビュー、メタレビュー、懸念表を作る用途に素直です。 |
| ML/AI会議論文に特化した査読生成 | [OpenReviewer](https://github.com/maxidl/openreviewer) | ICLR/NeurIPS等のレビューでfine-tuneされた8Bモデルを中心にした研究システムです。 |
| 根拠・引用・未支持主張の検査 | [Draft Detective](https://github.com/agencyenterprise/draft-detective) + [RefChecker](https://github.com/markrussinovich/refchecker) | 「査読コメント生成」より、論文の弱い根拠・引用不整合・幻覚引用を見つけるのに強いです。 |
| 文献レビュー/スクリーニング | [ASReview](https://github.com/asreview/asreview), [ReviewAid](https://github.com/aurumz-rgb/ReviewAid), [LatteReview](https://github.com/PouriaRouzrokh/LatteReview) | systematic reviewのスクリーニング・抽出に特化しています。 |
| 統計・再現性の機械チェック | [statcheck](https://github.com/MicheleNuijten/statcheck), [scrutiny](https://github.com/lhdjung/scrutiny), [showyourwork](https://github.com/showyourwork/showyourwork), [repo2docker](https://github.com/jupyterhub/repo2docker) | 査読者が見るべき「p値整合性」「平均値整合性」「再現環境」を自動チェックできます。 |

## OSS: 論文本体のAI査読・査読生成

| 名称 | URL | License | stars / 更新 | 何をするか | 入力 | 成熟度/注意 |
|---|---|---:|---:|---|---|---|
| OpenAIReview | [GitHub](https://github.com/ChicagoHAI/OpenAIReview), [Web](https://openaireview.org/) | MIT | 137 / 2026-05 | 論文の技術的・論理的問題をレビューし、結果を可視化。OCR、arXiv HTML、複数LLM provider、ベンチマーク付き。 | PDF, DOCX, TeX, MD/TXT, arXiv URL | 現時点の第一候補。API/OCRコストと機密性に注意。 |
| Ai-Review | [GitHub](https://github.com/NeuroDong/Ai-Review) | MIT | 524 / 2026-05 | 大規模モデルによる論文レビュー、VLMレビュー、Agent skill。 | PDF, LaTeX, Word等 | starsは多い。Web/skill寄りで、運用形態の確認が必要。 |
| LLM-scientific-feedback | [GitHub](https://github.com/Weixin-Liang/LLM-scientific-feedback), [paper](https://arxiv.org/abs/2310.01783) | CC-BY-4.0 | 531 / 2026-04 | GPT-4で研究論文PDFに科学的フィードバックを生成した大規模実証研究のコード。 | PDF/抽出テキスト | 研究コード寄り。ScienceBeam等の制約あり。 |
| ai-peer-review | [GitHub](https://github.com/poldrack/ai-peer-review) | 未記載 | 143 / 2026-05 | 複数LLMで独立レビューを作り、メタレビューと懸念表を生成。 | PDF | neuroscience向けデフォルトprompt。ライセンス未記載。 |
| OpenReviewer | [GitHub](https://github.com/maxidl/openreviewer), [paper](https://arxiv.org/abs/2412.11948), [demo](https://huggingface.co/spaces/maxidl/openreviewer) | 未記載 | 10 / 2026-03 | Llama-OpenReviewer-8Bを中心としたML/AI会議論文向け査読生成。 | PDF -> Markdown | ML/AI会議向け。ライセンス未記載。 |
| ReviewGrounder | [GitHub](https://github.com/EigenTom/ReviewGrounder), [paper](https://arxiv.org/abs/2604.14261) | 未記載 | 12 / 2026-05 | ルーブリック、関連研究検索、結果分析で根拠付きレビューを生成。Python APIとGradio demoあり。 | title/abstract/content等 | 新しい研究実装。根拠付き設計は有望。 |
| TreeReview | [GitHub](https://github.com/YuanChang98/tree-review), [paper](https://arxiv.org/abs/2506.07642) | 未記載 | 14 / 2026-02 | 質問木を動的に展開し、深いLLM査読を生成。 | MMD化された論文 | 研究コード。入力変換が必要。 |
| ReviewAdvisor / ASAP-Review | [GitHub](https://github.com/neulab/ReviewAdvisor), [paper](https://arxiv.org/abs/2102.00176) | Apache-2.0 | 203 / 2026-03 | 論文から一次査読コメントを生成、観点タグ付け、レビュー評価指標、バイアス分析。 | ASAP-Review dataset等 | 古典的研究コードとして重要。demoは停止中。 |
| ReviewRobot | [GitHub](https://github.com/EagleW/ReviewRobot), [paper](https://aclanthology.org/2020.inlg-1.27/) | MIT | 30 / 2025-11 | KGベースでスコア予測と査読コメント生成。 | 専用dataset/KG | 古めの研究コード。Windows非推奨など制約あり。 |
| DeepReview / DeepReviewer | [GitHub](https://github.com/zhu-minjun/Researcher), [model](https://huggingface.co/WestlakeNLP/DeepReviewer-14B), [data](https://huggingface.co/datasets/WestlakeNLP/DeepReview-13K) | 非標準/要確認 | 382 / 2026-05 | 多視点・多段階の自動査読生成と自己検証。 | paper text等 | 研究用途。公式査読での利用禁止条件など利用条件を要確認。 |
| AgentReview | [GitHub](https://github.com/Ahren09/AgentReview), [project](https://agentreview.github.io/) | Apache-2.0 | 114 / 2026-05 | 複数LLM agentで査読ダイナミクスをシミュレーション。OpenReview APIからICLRデータ利用。 | OpenReview data | 生成査読ツールというより査読過程の研究基盤。 |
| AnnotateGPT | [GitHub](https://github.com/onekin/AnnotateGPT) | 未記載 | 6 / 2026-04 | Chrome拡張でPDFにLLM/人間の基準別ハイライト、査読ドラフト生成。 | ブラウザ上のPDF | 査読者支援UIとして独自性あり。ライセンス未記載。 |
| Draft Detective | [GitHub](https://github.com/agencyenterprise/draft-detective), [docs](https://agencyenterprise.github.io/draft-detective/) | MIT | 14 / 2026-05 | claim-reference alignment、未支持主張、引用検証、文献提案、文献調査。 | PDF/DOCX/MD等 | production readyではない明記あり。根拠検証に強い。 |
| Review Feedback Agent | [GitHub](https://github.com/zou-group/review_feedback_agent), [paper](https://arxiv.org/abs/2504.09737) | MIT | 32 / 2026-05 | 論文と既存レビューを入力し、レビューをより具体的・有用にするフィードバックを生成。 | review text + paper PDF/OpenReview ID | 「論文を査読する」のではなく「査読文を査読する」。 |
| FactReview / Review-Assistant | [GitHub](https://github.com/DEFENSE-SEU/FactReview), [paper](https://huggingface.co/papers/2604.04074) | AGPL-3.0 | 57 / 2026-05 | 文献位置づけ、実行ベースのclaim verification、根拠付きレビュー。 | 論文+関連文献/実験情報 | 新しい研究コード。実用にはセットアップ確認が必要。 |
| Rigorous | [GitHub](https://github.com/Agentic-Systems-Lab/rigorous), [service](https://www.rigorous.review/) | MIT | 249 / 2026-05 | Agent1_Peer_Review等を含む科学論文分析/レビュー suite。 | 原稿 | OSS部分とサービス部分の境界を要確認。 |
| PaperClaw extension | [GitHub](https://github.com/Agnuxo1/paperclaw-extension) | MIT | 4 / 2026-05 | 研究アイデアから論文化、AI Tribunal review、PDF exportにつなぐVS Code拡張。 | VS Code project/idea | 新興・小規模。査読単体ライブラリではない。 |
| paper-rebuttal-skill | [GitHub](https://github.com/guzy0324/paper-rebuttal-skill) | MIT | 4 / 2026-05 | レビュー分析、反論・改稿ログ、LaTeX安全編集のhuman-in-the-loop workflow。 | reviewer comments + manuscript | 自動査読ではなく査読後対応支援。 |

## OSS: systematic review / evidence synthesis

| 名称 | URL | License | stars / 更新 | 何をするか | 査読との距離 |
|---|---|---:|---:|---|---|
| ASReview LAB | [GitHub](https://github.com/asreview/asreview), [site](https://asreview.nl/) | Apache-2.0 | 900 / 2026-05 | active learningで大量文献のscreeningを効率化。 | 論文査読ではなくsystematic review支援。 |
| ReviewAid | [GitHub](https://github.com/aurumz-rgb/ReviewAid), [site](https://reviewaid.github.io/) | Apache-2.0 | 8 / 2026-05 | LLMで全文screeningとdata extraction。PICO等に対応。 | systematic reviewの補助 reviewer。 |
| AiReview | [GitHub](https://github.com/ielab/ai-review), [paper](https://arxiv.org/abs/2504.04193) | AGPL-3.0 | 4 / 2025-11 | LLM-assisted title/abstract screeningのframework/UI。 | systematic literature review向け。 |
| LatteReview | [GitHub](https://github.com/PouriaRouzrokh/LatteReview), [docs](https://pouriarouzrokh.github.io/LatteReview/) | 非標準/要確認 | 105 / 2026-05 | multi-agentでsystematic reviewのscreening/data abstraction等を自動化。 | 文献レビュー自動化。 |
| RobotReviewer | [GitHub](https://github.com/ijmarshall/robotreviewer), [site](https://www.robotreviewer.net/) | GPL-3.0 | 174 / 2026-04 | RCT論文からPICO抽出、Cochrane RoB推定等。 | 医学RCTの品質評価/ evidence synthesis向け。 |

## OSS: 査読研究データセット・評価基盤

| 名称 | URL | License | stars / 更新 | 用途 |
|---|---|---:|---:|---|
| OpenReview Python library | [GitHub](https://github.com/openreview/openreview-py), [API docs](https://docs.openreview.net/reference/api-v2) | MIT | 244 / 2026-05 | OpenReview上の論文・レビュー・決定・コメント取得。 |
| PeerRead | [GitHub](https://github.com/allenai/PeerRead), [paper](https://arxiv.org/abs/1804.09635) | 未記載 | 428 / 2026-05 | 査読データセット。採否/スコア予測やレビュー分析。 |
| NLPeer | [GitHub](https://github.com/UKPLab/nlpeer), [paper](https://arxiv.org/abs/2211.06651) | Apache-2.0 | 33 / 2026-05 | 複数peer review datasetの統一表現とタスク実装。 |
| PeerSum | [GitHub](https://github.com/oaimli/PeerSum), [paper](https://arxiv.org/abs/2305.01498), [HF](https://huggingface.co/datasets/oaimli/PeerSum) | 未記載 | 16 / 2025-10 | 複数レビューからメタレビューを生成するデータ/研究コード。 |
| PeerPrism | [GitHub](https://github.com/Reviewerly-Inc/PeerPrism), [paper](https://arxiv.org/abs/2604.14513) | 未記載 | 4 / 2026-04 | human/LLM/hybridレビュー由来判定ベンチマーク。 |
| RichardLRC/Peer-Review | [GitHub](https://github.com/RichardLRC/Peer-Review), [paper](https://arxiv.org/abs/2509.19326) | 未記載 | 3 / 2026-04 | LLM査読生成の長所/欠点を評価するコード・結果。 |

## OSS: 統計・引用・再現性・編集ワークフロー

| 名称 | URL | License | stars / 更新 | 何を自動チェックするか | 注意点 |
|---|---|---:|---:|---|---|
| statcheck | [GitHub](https://github.com/MicheleNuijten/statcheck), [web](https://statcheck.io/) | GPL系/CRAN要確認 | 186 / 2026-04 | APA形式の検定統計量・df・p値の整合性。 | APA形式中心。誤検出/検出漏れあり。 |
| statcheck_python | [GitHub](https://github.com/hplisiecki/statcheck_python) | GPL-3.0 | 5 / 2025-10 | statcheckのPython実装。 | R本家より新しく小規模。 |
| scrutiny | [GitHub](https://github.com/lhdjung/scrutiny) | 非標準/要確認 | 8 / 2026-03 | GRIM/GRIMMER/DEBIT等、要約統計の整合性。 | 値入力/整形が必要。 |
| RefChecker | [GitHub](https://github.com/markrussinovich/refchecker) | MIT | 366 / 2026-05 | 参考文献の実在性、著者/年/DOI/venue不一致、幻覚引用。 | 「未確認」は必ずしも誤りではない。 |
| Manubot | [GitHub](https://github.com/manubot/manubot) | BSD-2 + Patent/要確認 | 474 / 2026-05 | DOI/PubMed等から引用メタデータ生成、原稿ビルド。 | 引用の科学的妥当性までは見ない。 |
| showyourwork! | [GitHub](https://github.com/showyourwork/showyourwork), [site](https://show-your.work/) | MIT | 641 / 2026-05 | 論文PDFをコード・データ・環境からCI再生成。 | LaTeX/Snakemake前提。 |
| repo2docker | [GitHub](https://github.com/jupyterhub/repo2docker) | BSD-3 | 1722 / 2026-05 | 研究repoから実行環境コンテナを構築。 | 結果一致検証は別途必要。 |
| Buffy | [GitHub](https://github.com/openjournals/buffy), [docs](https://buffy.readthedocs.io/) | MIT | 29 / 2026-05 | JOSS等のeditorial bot生成。 | 査読内容ではなく査読運営自動化。 |
| Inara | [GitHub](https://github.com/openjournals/inara) | MIT | 37 / 2026-04 | JOSS/JOSEのPDF/JATS/Crossref artifact生成。 | 出版artifact作成支援。 |
| textlint | [GitHub](https://github.com/textlint/textlint) | MIT | 3122 / 2026-05 | 自然言語lint。独自ルールで学術文書チェック可能。 | 研究特化ではない。 |
| proselint | [GitHub](https://github.com/amperser/proselint) | BSD-3 | 4531 / 2026-05 | 英文の冗長表現・文体・用語lint。 | 科学的妥当性は見ない。 |

## 商用・非OSS・公開サンプルあり

| サービス | URL | 公開サンプル/デモ | 主機能 | 査読への近さ | 注意点 |
|---|---|---:|---|---|---|
| ReviewerZero | [AI Review](https://www.reviewerzero.ai/features/ai-review), [Docs](https://www.reviewerzero.ai/docs) | 画面例 | 構造化査読レポート、再現性予測、投稿先推薦、guideline check。 | 高 | 新興。実績・データ取扱い確認が必要。 |
| PeerGenius.ai | [公式](https://peergenius.ai/), [samples](https://peergenius.ai/samples) | full sample review導線あり | 最大7 specialist reviewers、統計/方法/分野/結果/懐疑的レビュー、editor-style decision。 | 高 | 著者向けpre-submission。分野専門性は人間確認が必要。 |
| review.fun | [公式](https://www.review.fun/) | Chrome拡張/無料枠 | PDFをアップロードして短いhuman-style feedback。 | 高 | シンプルな投稿前フィードバック向け。 |
| Jenni AI Reviews | [AI Peer Review](https://jenni.ai/reviews/ai-peer-review) | 画面例/動画 | 標準査読基準で採点し、本文に直接コメント。 | 高 | 著者向け。科学的妥当性の最終判断は不可。 |
| Paperpal Preflight / PeerPilot | [Preflight](https://paperpal.com/preflight), [sample PDF](https://preflight.paperpal.com/Sample_Electronics%20and%20Electrical%20Engg%20SES%20%28Paperpal%20Edit%29.pdf) | サンプルPDF | SmartScreen, IntegrityGuard, PeerPilot, DigitalEdit, DetectAI, ImageCheck, PlagCheck。 | 高 | publisher/institution向け色が強い。科学的妥当性より投稿準備・整合性。 |
| Rigor / Karl | [公式](https://www.rigor.pub/) | recent reviews一覧 | fully agentic AI peer reviewerを標榜。 | 高 | 詳細仕様・OSS性は限定的。 |
| PeerReviewerAI | [公式](https://aipeerreviewer.com/) | サンプルレビュー掲載 | 6評価セクション、エラー検出、方法評価、推薦判定。 | 高 | 商用。品質検証は別途必要。 |
| CheckMyManuscript | [AI Manuscript Review](https://checkmymanuscript.com/ai-manuscript-review) | example導線 | 80+ checks、構造/言語/引用/メタデータ/形式。 | 中〜高 | 明示的に「peer reviewの代替ではない」。 |
| Peereply | [公式](https://www.peereply.com/) | 画面例/例文 | 査読コメントへのresponse letter、redline、引用検証。 | 中〜高 | 査読後対応支援。査読生成ではない。 |
| PaperReview.ai | [tech overview](https://paperreview.ai/tech-overview) | Webサービス | arXiv関連研究を使う高速レビュー/フィードバック。 | 中〜高 | OSSライブラリ未確認。 |
| SciScore | [公式](https://sciscore.com/), [sample report](https://www.sciscore.com/media/core_report.pdf) | sample report | MDAR/rigor/transparency、材料・方法の品質チェック。 | 中 | 商用/非OSS。生命科学寄り。 |
| Trinka Publication Readiness / Technical Checks | [technical checks](https://www.trinka.ai/features/technical-checks), [日本語ページ](https://www.trinka.ai/jp/features/publication-readiness-checks) | sample report導線 | 出版適正、参考文献、図表、臨床試験情報、要約/キーワード。 | 中 | 投稿前形式/技術チェック中心。 |
| Scite Assistant | [Assistant](https://scite.org/assistant), [Scite](https://scite.ai/) | 画面例/PDF資料 | Smart Citations、支持/反証/言及分類、Reference Check。 | 中 | 引用・文献根拠の検証支援。査読コメント生成ではない。 |
| Scholarcy | [features](https://www.scholarcy.com/scholarcy-features/), [API](https://scholarcy.github.io/slate/) | 画面例/API | 論文要約、Flashcards、研究品質指標、比較、文献マトリクス。 | 中 | 読解・スクリーニング支援。 |
| SciSpace | [Chrome extension](https://chromewebstore.google.com/detail/scispace-do-hours-of-rese/cipccbpjpemcnijhjcdjmkjhmhniiick) | 画面例 | PDF Q&A、文献レビュー、引用付き回答。 | 中 | 査読ではなく読解/調査支援。 |
| Writefull | [Revise](https://www.writefull.com/writefull-revise), [Publishers](https://www.writefull.com/for-publishers), [API](https://www.writefull.com/language-api) | guide/API | 学術英語校正、言語品質、メタデータ抽出、投稿原稿分類。 | 中 | 言語・編集・トリアージ中心。 |
| EditorialPilot / Editorial Manager連携 | [EditorialPilot](https://editorialpilot.integranxt.com/), [Aries release](https://www.ariessys.com/news-and-events/press-releases/aries-systems-partners-with-integra-to-bring-ai-driven-quality-and-integrity-checks-to-the-editorial-workflow/) | demo申込/画面例 | Editorial Manager内で技術・言語・研究公正チェック。 | 高 | 編集部・出版社向け。 |
| Springer Nature AI editorial checks | [press release](https://group.springernature.com/us/group/media/press-releases/ai-tool-to-help-streamline-integrity-and-ethics-checks/27730892) | 公開デモなし | 品質・倫理・適合性チェック、査読前保留判断支援。 | 高 | 内製/対象誌限定。 |
| AJE / Research Square系 | [AJE editing](https://www.aje.com/services/editing-services), [Digital Editing](https://www.aje.com/go/digital-eye) | sample edit | AI支援英文編集、人手編集、presubmission review。 | 中 | 自動査読というより編集/投稿準備。 |
| ResearchRabbit | [公式](https://www.researchrabbit.ai/) | 画面例 | 文献探索、引用ネットワーク、Zotero連携。 | 低〜中 | 文献探索。査読ではない。 |
| Atypon AI Suite | [Wiley/Atypon](https://www.wiley.com/en-us/business/partner-solutions/solutions/atypon) | 限定的 | 出版プラットフォーム上のAI要約/読解/発見支援。 | 低 | 査読支援というより閲覧・発見支援。 |

## 使い分け

### 著者が投稿前に自分の原稿を叩く

1. OpenAIReviewで全体レビューを走らせる。
2. Draft Detective / RefCheckerで引用と未支持主張を潰す。
3. statcheck / scrutinyで統計表記の機械的不整合を潰す。
4. showyourwork / repo2dockerで再現環境と再生成可能性を確認する。
5. 最後にPaperpal, Jenni, PeerGenius, ReviewerZero等の商用サービスを比較的安価な外部チェックとして使う。

### 編集部・研究室内の投稿前ゲートを作る

1. 形式・言語・引用: Paperpal Preflight / Trinka / Writefull / RefChecker。
2. integrity・画像・AI検出: Paperpal IntegrityGuard/ImageCheck, ReviewerZero, SciScore等。
3. 内容レビュー: OpenAIReview, OpenReviewer, ReviewGrounder。
4. human-in-the-loop: AIの指摘をそのまま判定に使わず、重大度・根拠・再現手順を人間が確認する。

### systematic reviewを自動化する

1. screeningならASReview。
2. LLM full-text screening/data extractionならReviewAidまたはLatteReview。
3. 医学RCTのPICO/RoBならRobotReviewer。
4. 研究用データ基盤ならOpenReview API, PeerRead, NLPeer。

## リスク・規約

- Elsevierは、peer reviewの科学的評価に生成AI/AI支援技術を使うべきではない、という立場を明記しています。機密性の問題もあります。
- Nature Portfolio系は、査読者が未公開原稿を生成AIツールにアップロードしないよう求め、AI支援を使った場合の透明な申告を求めています。
- ICML 2026のように、会議によってはLLMレビュー利用ポリシーを分岐・実験している例があります。つまり「AI査読ツールがある」ことと「任命された査読で使ってよい」ことは別です。
- hidden prompt injection、AI生成レビュー検出の誤判定、LLMレビューのrating compression、引用幻覚は実際に研究対象になっています。安全な運用には、PDF内の不可視テキスト検査、prompt injection除去、外部LLM投入禁止設定、ログ監査が必要です。

## 採用候補の短評

- **本命OSS**: OpenAIReview。現時点では実用の入り口として最もまとまっています。
- **軽い自作に向くOSS**: poldrack/ai-peer-review。構造が単純で、複数モデル査読とメタレビューを組みやすいです。
- **研究開発に向くOSS**: ReviewGrounder, TreeReview, OpenReviewer, ReviewAdvisor, AgentReview, NLPeer。
- **査読品質を上げる補助**: Review Feedback Agent。査読者のレビュー文をより具体的にする用途です。
- **形式・根拠の堅いチェック**: RefChecker, statcheck, scrutiny, showyourwork。
- **商用で近いもの**: ReviewerZero, PeerGenius, Jenni Reviews, Paperpal PeerPilot/Preflight, Rigor, PeerReviewerAI。

## 未確認・境界事例

- GitHubには「paper review」「peer review」「review agent」を名乗る小規模repoが多数ありますが、コードレビュー用、読書メモ用、一般文書レビュー用が多く、論文査読に使える根拠がないものは主要表から外しました。
- SciScore, Penelope.ai, Code Ocean等は査読・投稿前チェックに近い機能がありますが、OSSとしてのコード公開は確認できないため商用/非OSS扱いです。
- ReviewRLは論文上ではGitHub公開予定とされていますが、調査時点で安定した実装公開を確認できなかったため「候補」に留めました。
- PaperReview.aiは公開Webサービスとしては査読に近いですが、OSSライブラリとしては未確認です。

## 参考にした主要一次情報

- [OpenAIReview GitHub](https://github.com/ChicagoHAI/OpenAIReview)
- [Ai-Review GitHub](https://github.com/NeuroDong/Ai-Review)
- [LLM-scientific-feedback GitHub](https://github.com/Weixin-Liang/LLM-scientific-feedback)
- [poldrack/ai-peer-review GitHub](https://github.com/poldrack/ai-peer-review)
- [OpenReviewer GitHub](https://github.com/maxidl/openreviewer)
- [Draft Detective GitHub](https://github.com/agencyenterprise/draft-detective)
- [Review Feedback Agent GitHub](https://github.com/zou-group/review_feedback_agent)
- [AnnotateGPT GitHub](https://github.com/onekin/AnnotateGPT)
- [ReviewAdvisor GitHub](https://github.com/neulab/ReviewAdvisor)
- [ReviewRobot GitHub](https://github.com/EagleW/ReviewRobot)
- [ReviewGrounder GitHub](https://github.com/EigenTom/ReviewGrounder)
- [ASReview GitHub](https://github.com/asreview/asreview)
- [ReviewAid GitHub](https://github.com/aurumz-rgb/ReviewAid)
- [LatteReview GitHub](https://github.com/PouriaRouzrokh/LatteReview)
- [OpenReview API docs](https://docs.openreview.net/reference/api-v2)
- [PeerRead GitHub](https://github.com/allenai/PeerRead)
- [NLPeer GitHub](https://github.com/UKPLab/nlpeer)
- [statcheck GitHub](https://github.com/MicheleNuijten/statcheck)
- [RefChecker GitHub](https://github.com/markrussinovich/refchecker)
- [ReviewerZero AI Review](https://www.reviewerzero.ai/features/ai-review)
- [PeerGenius.ai](https://peergenius.ai/)
- [review.fun](https://www.review.fun/)
- [Jenni AI Peer Review](https://jenni.ai/reviews/ai-peer-review)
- [Paperpal Preflight](https://paperpal.com/preflight)
- [PeerReviewerAI](https://aipeerreviewer.com/)
- [CheckMyManuscript AI Manuscript Review](https://checkmymanuscript.com/ai-manuscript-review)
- [Elsevier generative AI policies for journals](https://www.elsevier.com/en-au/about/policies-and-standards/generative-ai-policies-for-journals)
- [Nature Portfolio peer review policy](https://www.nature.com/nclimate/editorial-policies/peer-review)
- [ICML 2026 LLM Policy](https://icml.cc/Conferences/2026/LLM-Policy)
