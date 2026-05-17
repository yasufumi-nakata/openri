# 新しい check の書き方

OpenRI のすべての check は `backend/openri/checks.py` の `CHECKS` リストに登録された
`CheckSpec` から呼ばれる。実装の最小単位は次の通り。

## 1. check 関数

```python
def check_my_thing(text: str, profile: dict) -> Finding:
    knobs = profile.get("strictness_knobs", {})
    # ... do mechanical detection on `text` ...
    return _finding(
        "my_thing",                       # check_id
        "My thing",                       # title
        "manuscript-quality",             # category
        Severity.MEDIUM,                  # severity
        Status.WARNING,                   # status
        60,                               # score 0-100
        "human-readable message",
        "actionable recommendation",
        evidence=[Evidence(quote="...", location="line 12", data={...})],
        tags=["my-thing"],
    )
```

`profile` は `analyzer.manuscript_profile()` が作る dict で、`strictness_knobs`、
`activated_rulesets`、`enable_network`、`pdf_inspection` を含む。strictness や
ネットワーク有無を見て挙動を変えるときはここを参照する。

## 2. 登録

```python
CHECKS.append(
    CheckSpec(
        "my_thing",
        "My thing",
        "manuscript-quality",
        "短い説明。",
        "experimental",   # stable | beta | experimental
        check_my_thing,
    )
)
```

`experimental` は `RunRequest.include_experimental_checks=False` のときに除外される。
CLI からは `--no-experimental` で同様にスキップできる。

## 3. テストの足場

```python
from openri.analyzer import analyze_manuscript
from openri.models import RunRequest

def test_my_thing_flags_obvious_violation():
    text = "..."
    report = analyze_manuscript(RunRequest(manuscript_text=text))
    finding = next(f for f in report.findings if f.check_id == "my_thing")
    assert finding.status.value == "failed"
```

新しいcheckは、AIが実装する前提でも挙動が揺れないように、最低限次のfixtureを用意する。

- **positive sample**: 明らかに検出すべき原稿。`status`、`severity`、`evidence` を固定する。
- **negative sample**: 似た表現だが検出してはいけない原稿。過検出を防ぐ。
- **borderline sample**: 丸め、曖昧表現、短い文脈など、strictnessで結果が変わり得る原稿。
- **identity-invariance sample**: 著者名、所属、謝辞、研究室名だけを変えてもfindingが変わらない原稿。
- **unsupported-is-not-pass sample**: PDF未検査、network無効、ruleset未指定などが`passed`に変換されないことを確認する原稿。

AI coding agentが追加したcheckは、説明文だけで正しい扱いにしない。少なくとも1つのdeterministic testで、同じ入力なら同じfindingが返ることを固定する。

## 4. YAML ruleset を使う場合

検出ロジックがキーワードや正規表現の集合で表現できるなら、`backend/openri/rulesets/`
配下に YAML を追加し、`ruleset_loader.load_keyword_ruleset()` または
`load_default_ruleset()` を使って読み込むのが望ましい。新しい Python コードを書くよりも
ユーザーが拡張しやすい。

例: `backend/openri/rulesets/my_ruleset.yaml` を置けば、`--ruleset my_ruleset` で
`ruleset_coverage` check が拾う。

## 5. SARIF 出力との互換

`Evidence.location` は `"line 12"` のように行番号を含む文字列にすると、
`sarif.py` がそれを `startLine` として GitHub Code Scanning に橋渡しする。
PDF の場合は `"page 3"` でも問題ないが、Code Scanning は行番号のみ拾う。
