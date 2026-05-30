from __future__ import annotations

import re

CLAIM_CUE_RE = re.compile(
    r"\b("
    r"we\s+(show|demonstrate|find|found|report|present|provide|observe|identify)|"
    r"significant|significantly|robust|novel|first|important|"
    r"suggests?|indicates?|supports?|improves?|predicts?|associated|association|"
    r"effect|caus(?:e|al|es|ed|ation)|"
    r"示す|示した|有意|効果|新規|重要|関連|因果|支持"
    r")\b",
    re.IGNORECASE,
)
STATISTIC_CUE_RE = re.compile(r"\b(t|z|F|χ2|χ\^2|chi-?square|p|CI|OR|RR|HR|β|r)\s*(?:\(|=|<|>)", re.IGNORECASE)
CITATION_CUE_RE = re.compile(
    r"(\[[0-9,\-\s]+\]|\([A-Z][A-Za-z-]+(?:\s+et\s+al\.)?,\s*20\d{2}\)|\b10\.\d{4,9}/)", re.IGNORECASE
)
FIGURE_CUE_RE = re.compile(r"\b(fig\.?|figure|table|supplement|図|表)\s*\d+", re.IGNORECASE)
LIMITATION_CUE_RE = re.compile(
    r"\b(limitation|however|although|future|may|might|could|cannot|not powered|pilot|exploratory|限界|ただし|可能性|探索的)\b",
    re.IGNORECASE,
)
CAUSAL_CUE_RE = re.compile(
    r"\b(caus(?:e|al|es|ed|ation)|mechanism|drives?|leads?\s+to|因果|原因|機序)\b", re.IGNORECASE
)
CAUSAL_DESIGN_RE = re.compile(
    r"\b(randomi[sz]ed|trial|experiment|controlled|causal inference|instrumental variable|difference-in-differences|RCT)\b",
    re.IGNORECASE,
)
NOVELTY_CUE_RE = re.compile(r"\b(novel|first|new|unprecedented|groundbreaking|新規|初めて)\b", re.IGNORECASE)
OVERGENERAL_CUE_RE = re.compile(
    r"\b(always|never|all|none|prove|definitive|conclusive|universal|完全|必ず|全て|証明)\b", re.IGNORECASE
)
