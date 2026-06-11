from __future__ import annotations

import re

# 日本語キーワードは \b で囲まない。Python の正規表現ではかな・漢字も \w に含まれるため、
# 「結果は有意であった」のように前後が和文文字だと \b が成立せず、一致しなくなる。
CLAIM_CUE_RE = re.compile(
    r"\b(?:"
    r"we\s+(?:show|demonstrate|find|found|report|present|provide|observe|identify)|"
    r"significant|significantly|robust|novel|first|important|"
    r"suggests?|indicates?|supports?|improves?|predicts?|associated|association|"
    r"effect|caus(?:e|al|es|ed|ation)"
    r")\b"
    r"|示す|示した|有意|効果|新規|重要|関連|因果|支持",
    re.IGNORECASE,
)
STATISTIC_CUE_RE = re.compile(r"\b(t|z|F|χ2|χ\^2|chi-?square|p|CI|OR|RR|HR|β|r)\s*(?:\(|=|<|>)", re.IGNORECASE)
CITATION_CUE_RE = re.compile(
    r"(\[[0-9,\-\s]+\]|\([A-Z][A-Za-z-]+(?:\s+et\s+al\.)?,\s*20\d{2}\)|\b10\.\d{4,9}/)", re.IGNORECASE
)
FIGURE_CUE_RE = re.compile(r"(?:\b(?:fig\.?|figure|table|supplement)|図|表)\s*\d+", re.IGNORECASE)
LIMITATION_CUE_RE = re.compile(
    r"\b(?:limitation|however|although|future|may|might|could|cannot|not powered|pilot|exploratory)\b"
    r"|限界|ただし|可能性|探索的",
    re.IGNORECASE,
)
CAUSAL_CUE_RE = re.compile(
    r"\b(?:caus(?:e|al|es|ed|ation)|mechanism|drives?|leads?\s+to)\b|因果|原因|機序",
    re.IGNORECASE,
)
CAUSAL_DESIGN_RE = re.compile(
    r"\b(?:randomi[sz]ed|trial|experiment|controlled|causal inference|instrumental variable|"
    r"difference-in-differences|RCT)\b"
    r"|ランダム化|無作為化|比較試験|介入試験|因果推論|操作変数|実験",
    re.IGNORECASE,
)
NOVELTY_CUE_RE = re.compile(
    r"\b(?:novel|first|new|unprecedented|groundbreaking)\b|新規|初めて",
    re.IGNORECASE,
)
OVERGENERAL_CUE_RE = re.compile(
    r"\b(?:always|never|all|none|prove|definitive|conclusive|universal)\b|完全|必ず|全て|証明",
    re.IGNORECASE,
)
