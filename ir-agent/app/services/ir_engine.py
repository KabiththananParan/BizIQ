"""
ir_engine.py
Core retrieval logic of the IR Agent: TF-IDF + cosine similarity.

Pipeline (NLP techniques used): lowercasing -> tokenisation -> stop-word
removal -> light suffix stemming -> TF-IDF weighting -> cosine ranking.

Design notes
- The vectorizer is fit on the DOCUMENTS ONLY; the query is transformed
  afterwards, so a query never distorts IDF weights.
- Each user's index is cached and rebuilt only when their active data
  changes (checked via a cheap DB fingerprint, so it is also correct when
  several uvicorn workers share one database).
- Results are explainable: we return the best-matching passage and the
  query terms that matched.
- Tiny corpora / stop-word-only queries return [] instead of crashing.
"""

import re
import threading
from dataclasses import dataclass

from sklearn.feature_extraction.text import ENGLISH_STOP_WORDS, TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

from database.db import get_connection

_TOKEN_RE = re.compile(r"[a-z0-9]+")
_SENTENCE_SPLIT_RE = re.compile(r"(?<=[.!?])\s+|\n+")
SNIPPET_CHARS = 300


# ---------------------------------------------------------------- NLP helpers
def _stem(word: str) -> str:
    """Very light suffix stemmer (enough to unify sale/sales, drop/dropped/dropping)."""
    if len(word) <= 3 or word.isdigit():
        return word
    if word.endswith("ies") and len(word) > 4:
        word = word[:-3] + "y"
    elif word.endswith("ing") and len(word) > 5:
        word = word[:-3]
        if len(word) > 2 and word[-1] == word[-2] and word[-1] not in "lsz":
            word = word[:-1]
    elif word.endswith("ed") and len(word) > 4:
        word = word[:-2]
        if len(word) > 2 and word[-1] == word[-2] and word[-1] not in "lsz":
            word = word[:-1]
    elif word.endswith("s") and not word.endswith(("ss", "us", "is")):
        word = word[:-1]
    if len(word) > 3 and word.endswith("e"):
        word = word[:-1]
    return word


def analyze(text: str) -> list[str]:
    """Text -> list of normalised terms (stop words removed, stemmed)."""
    tokens = _TOKEN_RE.findall(text.lower())
    return [_stem(t) for t in tokens if t not in ENGLISH_STOP_WORDS]


def _query_term_map(query: str) -> dict[str, str]:
    """stem -> original query word, for readable `matched_terms`."""
    mapping: dict[str, str] = {}
    for tok in _TOKEN_RE.findall(query.lower()):
        if tok in ENGLISH_STOP_WORDS:
            continue
        mapping.setdefault(_stem(tok), tok)
    return mapping


# ---------------------------------------------------------------- index cache
@dataclass
class _Index:
    fingerprint: tuple
    ids: list[int]
    names: list[str]
    contents: list[str]
    vectorizer: TfidfVectorizer | None
    matrix: object | None


_cache: dict[str, _Index] = {}
_cache_lock = threading.Lock()


def invalidate(owner: str | None = None) -> None:
    """Drop cached index for one user (or everyone). Call after any write."""
    with _cache_lock:
        if owner is None:
            _cache.clear()
        else:
            _cache.pop(owner, None)


def _fingerprint(conn, owner: str) -> tuple:
    row = conn.execute(
        "SELECT COUNT(*), COALESCE(MAX(id), 0), COALESCE(MAX(updated_at), '') "
        "FROM datasources WHERE owner = ? AND status = 'active'",
        (owner,),
    ).fetchone()
    return tuple(row)


def _get_index(owner: str) -> _Index:
    with get_connection() as conn:
        fp = _fingerprint(conn, owner)
        with _cache_lock:
            cached = _cache.get(owner)
        if cached is not None and cached.fingerprint == fp:
            return cached

        rows = conn.execute(
            "SELECT id, name, content FROM datasources "
            "WHERE owner = ? AND status = 'active' ORDER BY id",
            (owner,),
        ).fetchall()

    ids = [r["id"] for r in rows]
    names = [r["name"] for r in rows]
    contents = [r["content"] for r in rows]

    vectorizer = matrix = None
    if contents:
        try:
            vectorizer = TfidfVectorizer(analyzer=analyze)
            matrix = vectorizer.fit_transform(contents)  # documents only
        except ValueError:  # empty vocabulary (e.g. only stop words / symbols)
            vectorizer = matrix = None

    index = _Index(fp, ids, names, contents, vectorizer, matrix)
    with _cache_lock:
        _cache[owner] = index
    return index


# ---------------------------------------------------------------- snippets
def _best_snippet(content: str, query_stems: set[str]) -> str:
    """Return the passage of `content` that overlaps most with the query."""
    passages = [p.strip() for p in _SENTENCE_SPLIT_RE.split(content) if p and p.strip()]
    if not passages:
        passages = [content.strip()]

    best, best_score = passages[0], -1
    for p in passages:
        score = len(query_stems & set(analyze(p)))
        if score > best_score:
            best, best_score = p, score

    if len(best) > SNIPPET_CHARS:
        best = best[:SNIPPET_CHARS].rstrip() + "..."
    return best


# ---------------------------------------------------------------- public API
def search(query: str, owner: str, top_k: int = 3) -> list[dict]:
    """
    Rank the owner's active data sources against `query`.
    Returns dicts: datasource_id, name, snippet, score, matched_terms.
    """
    index = _get_index(owner)
    if index.vectorizer is None or index.matrix is None:
        return []

    query_vec = index.vectorizer.transform([query])
    if query_vec.nnz == 0:  # no query term exists in the vocabulary
        return []

    scores = cosine_similarity(query_vec, index.matrix).ravel()
    term_map = _query_term_map(query)
    query_stems = set(term_map)

    # stable ranking: score desc, then id asc
    order = sorted(range(len(scores)), key=lambda i: (-scores[i], index.ids[i]))[:top_k]

    results = []
    for i in order:
        if scores[i] <= 0:
            continue
        doc_stems = set(analyze(index.contents[i]))
        matched = [term_map[s] for s in term_map if s in doc_stems]
        results.append(
            {
                "datasource_id": index.ids[i],
                "name": index.names[i],
                "snippet": _best_snippet(index.contents[i], query_stems),
                "score": round(float(scores[i]), 4),
                "matched_terms": matched,
            }
        )
    return results
