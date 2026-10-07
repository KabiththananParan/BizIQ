"""Lightweight extractive summarization.

This is intentionally offline and explainable for the project baseline. It
selects the most informative sentences using word-frequency scoring.
"""
import re
from collections import Counter
from app.services import config


def summarize_text(text: str, max_sentences: int | None = None) -> str:
    sentences = [s.strip() for s in re.split(r"(?<=[.!?])\s+", text.strip()) if s.strip()]
    if len(sentences) <= 2:
        return text.strip()

    max_sentences = max_sentences or config.SUMMARY_SENTENCES
    words = re.findall(r"[A-Za-z0-9']+", text.lower())
    stop = {
        "the", "a", "an", "is", "are", "was", "were", "and", "or", "of",
        "to", "in", "on", "for", "with", "this", "that", "it", "as", "by",
        "from", "at", "be", "has", "have", "had"
    }
    freq = Counter(w for w in words if w not in stop)
    if not freq:
        return " ".join(sentences[:max_sentences])

    scored = []
    for idx, sentence in enumerate(sentences):
        sw = re.findall(r"[A-Za-z0-9']+", sentence.lower())
        score = sum(freq[w] for w in sw if w in freq) / max(1, len(sw))
        scored.append((score, idx, sentence))

    selected = sorted(scored, reverse=True)[:max_sentences]
    selected.sort(key=lambda x: x[1])
    return " ".join(s[2] for s in selected)
