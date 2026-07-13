# ── core/memory.py ────────────────────────────────────────────────────────────
# SQLite-backed memory store with BM25 + cosine hybrid retrieval.
#
# Scoring:  final = (BM25_WEIGHT × bm25) + (COSINE_WEIGHT × cosine)
# BM25 handles keyword precision; cosine handles semantic overlap.
# Threshold applied to combined score.
# Code memories excluded from retrieval — too large for inline injection.

import re
import math
import sqlite3
import os
from contextlib import contextmanager
from app.config import MEMORY_FILE

_DB_PATH = os.path.splitext(MEMORY_FILE)[0] + ".db"

_SCHEMA = """
CREATE TABLE IF NOT EXISTS memories (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    user        TEXT    NOT NULL,
    response    TEXT    NOT NULL,
    memory      TEXT    NOT NULL,
    memory_type TEXT    NOT NULL DEFAULT 'text',
    filename    TEXT,
    created_at  TEXT    NOT NULL DEFAULT (datetime('now'))
);
"""

# ── Tuning ────────────────────────────────────────────────────────────────────

BM25_K1            = 1.5    # term frequency saturation (1.0–2.0)
BM25_B             = 0.75   # length normalization (0=none, 1=full)
BM25_WEIGHT        = 0.6    # hybrid blend weight for BM25
COSINE_WEIGHT      = 0.4    # hybrid blend weight for cosine
SIMILARITY_THRESHOLD = 0.10 # min combined score to inject a memory
TOP_K              = 3      # max memories injected per request

_STOPWORDS = {
    "a", "an", "the", "is", "it", "in", "on", "at", "to", "for",
    "of", "and", "or", "but", "not", "be", "was", "are", "with",
    "this", "that", "i", "my", "me", "we", "you", "he", "she",
    "they", "do", "did", "have", "has", "can", "will", "just",
    "what", "how", "why", "when", "so", "if", "about", "from",
}


# ── DB ────────────────────────────────────────────────────────────────────────

@contextmanager
def _db():
    conn = sqlite3.connect(_DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        conn.execute(_SCHEMA)
        conn.commit()
        yield conn
    finally:
        conn.close()


# ── Tokenizer ─────────────────────────────────────────────────────────────────

def _tokenize(text: str) -> list[str]:
    return [
        w for w in re.findall(r"[a-z]+", text.lower())
        if w not in _STOPWORDS and len(w) > 1
    ]


# ── TF-IDF helpers (for cosine) ───────────────────────────────────────────────

def _tf(tokens: list[str]) -> dict[str, float]:
    if not tokens:
        return {}
    freq: dict[str, int] = {}
    for t in tokens:
        freq[t] = freq.get(t, 0) + 1
    total = len(tokens)
    return {w: c / total for w, c in freq.items()}


def _cosine(vec_a: dict[str, float], vec_b: dict[str, float]) -> float:
    shared = set(vec_a) & set(vec_b)
    if not shared:
        return 0.0
    dot   = sum(vec_a[w] * vec_b[w] for w in shared)
    mag_a = math.sqrt(sum(v * v for v in vec_a.values()))
    mag_b = math.sqrt(sum(v * v for v in vec_b.values()))
    if mag_a == 0 or mag_b == 0:
        return 0.0
    return dot / (mag_a * mag_b)


# ── BM25 ──────────────────────────────────────────────────────────────────────

class BM25Index:
    """
    Lightweight BM25 index over a list of tokenized documents.
    Rebuilt in-memory whenever save_memory() is called.
    """

    def __init__(self, docs: list[list[str]]) -> None:
        self.docs    = docs
        self.n       = len(docs)
        self.avglen  = sum(len(d) for d in docs) / max(self.n, 1)
        self.df: dict[str, int] = {}

        for doc in docs:
            for term in set(doc):
                self.df[term] = self.df.get(term, 0) + 1

    def score(self, query_tokens: list[str], doc_idx: int) -> float:
        doc    = self.docs[doc_idx]
        doclen = len(doc)
        score  = 0.0

        tf_map: dict[str, int] = {}
        for t in doc:
            tf_map[t] = tf_map.get(t, 0) + 1

        for term in query_tokens:
            if term not in tf_map:
                continue
            tf  = tf_map[term]
            df  = self.df.get(term, 0)
            idf = math.log((self.n - df + 0.5) / (df + 0.5) + 1)
            num = tf * (BM25_K1 + 1)
            den = tf + BM25_K1 * (1 - BM25_B + BM25_B * doclen / self.avglen)
            score += idf * (num / den)

        return score

    def max_score(self) -> float:
        """Used to normalize BM25 scores into 0–1 range."""
        # Approximate upper bound: score a perfect single-term doc
        if self.n == 0:
            return 1.0
        idf_max = math.log((self.n + 0.5) / (0.5) + 1)
        num = (BM25_K1 + 1)
        den = 1 + BM25_K1 * (1 - BM25_B + BM25_B)
        return idf_max * (num / den)


# ── In-memory index ───────────────────────────────────────────────────────────
# Each entry: (memory_dict, token_list, tf_vector)

_index: list[tuple[dict, list[str], dict[str, float]]] = []
_bm25:  BM25Index = BM25Index([])


def _rebuild_index() -> None:
    global _index, _bm25
    with _db() as conn:
        rows = conn.execute(
            "SELECT * FROM memories WHERE memory_type = 'text' "
            "ORDER BY created_at ASC"
        ).fetchall()

    _index = []
    for row in rows:
        mem = dict(row)
        # Score against user prompt + response for broader recall
        combined_text = mem["user"] + " " + mem["memory"]
        tokens = _tokenize(combined_text)
        _index.append((mem, tokens, _tf(tokens)))

    _bm25 = BM25Index([tokens for _, tokens, _ in _index])


_rebuild_index()


# ── Public API ────────────────────────────────────────────────────────────────

def save_memory(
    user: str,
    Bot_response: str,
    memory_type: str = "text",
    filename: str | None = None,
) -> None:
    with _db() as conn:
        conn.execute(
            "INSERT INTO memories (user, response, memory, memory_type, filename) "
            "VALUES (?, ?, ?, ?, ?)",
            (user, Bot_response, Bot_response, memory_type, filename),
        )
        conn.commit()
    _rebuild_index()


def load_memory() -> list[dict]:
    with _db() as conn:
        rows = conn.execute(
            "SELECT * FROM memories ORDER BY created_at ASC"
        ).fetchall()
    return [dict(row) for row in rows]


def search_memory(query: str) -> list[dict]:
    if not _index:
        return []

    query_tokens = _tokenize(query)
    query_tf     = _tf(query_tokens)

    if not query_tokens:
        return []

    bm25_max = _bm25.max_score() or 1.0
    results: list[tuple[dict, float]] = []

    for i, (mem, _, tf_vec) in enumerate(_index):
        bm25_raw  = _bm25.score(query_tokens, i)
        bm25_norm = min(bm25_raw / bm25_max, 1.0)   # normalize to 0–1
        cos       = _cosine(query_tf, tf_vec)
        combined  = BM25_WEIGHT * bm25_norm + COSINE_WEIGHT * cos

        if combined >= SIMILARITY_THRESHOLD:
            results.append((mem, combined))

    results.sort(key=lambda x: x[1], reverse=True)
    return [mem for mem, _ in results[:TOP_K]]


def build_memory_context(query: str) -> str:
    hits = search_memory(query)
    if not hits:
        return ""
    lines = ["\nRELEVANT MEMORIES:\n"]
    for mem in hits:
        lines.append(f"- {mem['user']}\n  → {mem['memory']}\n")
    return "\n".join(lines)
