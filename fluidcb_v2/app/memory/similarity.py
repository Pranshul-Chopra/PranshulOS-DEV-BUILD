# ── memory/similarity.py ──────────────────────────────────────────────────────
# Lightweight cosine similarity for repeat detection and depth triggering.
# Pure stdlib — no numpy, no faiss. Fast enough for < 50k memories on SQLite.
# Swap this module for a faiss/hnswlib backend when scale demands it.

import math
import re
from collections import Counter


def cosine_sim(a: str, b: str) -> float:
    """Bag-of-words cosine similarity between two strings. Returns 0–1."""
    va = _vectorise_cached(a)
    vb = _vectorise_cached(b)
    if not va or not vb:
        return 0.0
    dot      = sum(va.get(t, 0) * vb.get(t, 0) for t in va)
    mag_a    = math.sqrt(sum(v * v for v in va.values()))
    mag_b    = math.sqrt(sum(v * v for v in vb.values()))
    if mag_a == 0 or mag_b == 0:
        return 0.0
    return dot / (mag_a * mag_b)


def find_similar_memory(
    text:      str,
    memories:  list[dict],
    threshold: float = 0.55,
) -> dict | None:
    """
    Return the most similar active memory above threshold, or None.
    Compares against raw_extract field.
    Lower threshold than depth trigger — repeat detection should be generous.
    """
    best_score = threshold
    best_match = None
    for mem in memories:
        extract = mem.get("raw_extract", "")
        if not extract:
            continue
        score = cosine_sim(text, extract)
        if score > best_score:
            best_score = score
            best_match = mem
    return best_match


def find_similar_session(
    query:    str,
    sessions: list[dict],
    threshold: float = 0.35,
) -> list[dict]:
    """
    Return sessions whose summary scores above threshold against query.
    Uses bag-of-words cosine similarity with a lowered threshold for
    better recall on short or paraphrased queries.
    """
    results = []
    for session in sessions:
        summary = session.get("summary", "")
        if not summary:
            continue
        score = cosine_sim(query, summary)
        if score >= threshold:
            results.append({**session, "_sim_score": score})
    return sorted(results, key=lambda x: x["_sim_score"], reverse=True)


# ── internals ─────────────────────────────────────────────────────────────────

_STOPWORDS = {
    "a","an","the","and","or","but","in","on","at","to","for","of","with",
    "is","was","are","were","be","been","being","have","has","had","do","does",
    "did","will","would","could","should","may","might","i","you","he","she",
    "it","we","they","my","your","his","her","its","our","their","this","that",
    "these","those","me","him","us","them","what","which","who","how","when",
    "where","why","not","no","so","if","as","by","from","up","about","into",
    "through","during","before","after","above","below","between","out","off",
}

# Pre-compile regex pattern for performance
_TOKEN_PATTERN = re.compile(r"[a-z]+")

# Vector cache for repeated comparisons within a request
_vector_cache: dict = {}

def _vectorise(text: str) -> Counter:
    tokens = _TOKEN_PATTERN.findall(text.lower())
    tokens = [t for t in tokens if t not in _STOPWORDS and len(t) > 2]
    return Counter(tokens)

def _vectorise_cached(text: str) -> Counter:
    """Vectorize with caching to avoid recomputation within a request."""
    # Use the text itself as key (could use hash for larger texts)
    if text not in _vector_cache:
        _vector_cache[text] = _vectorise(text)
    return _vector_cache[text]

def clear_vector_cache() -> None:
    """Clear the cache after processing completes. Called after each request."""
    global _vector_cache
    _vector_cache.clear()
