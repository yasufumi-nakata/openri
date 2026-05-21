from __future__ import annotations

from typing import Iterator, Tuple

SENTENCE_BOUNDARIES = {".", "!", "?", "\n", "。", "！", "？"}
PUNCTUATION_BOUNDARIES = {".", "!", "?", "。", "！", "？"}


def iter_sentence_spans(text: str) -> Iterator[Tuple[int, str]]:
    """Yield normalized sentence-like spans without regex backtracking."""
    start = 0
    index = 0
    length = len(text)
    while index < length:
        char = text[index]
        if char not in SENTENCE_BOUNDARIES:
            index += 1
            continue

        end = index + 1
        if char in PUNCTUATION_BOUNDARIES:
            while end < length and text[end] in PUNCTUATION_BOUNDARIES:
                end += 1
        yield from _normalised_span(text, start, end)
        start = end
        index = end

    if start < length:
        yield from _normalised_span(text, start, length)


def _normalised_span(text: str, start: int, end: int) -> Iterator[Tuple[int, str]]:
    chunk = text[start:end]
    stripped = chunk.strip()
    if not stripped:
        return
    leading = len(chunk) - len(chunk.lstrip())
    yield start + leading, " ".join(stripped.split())
