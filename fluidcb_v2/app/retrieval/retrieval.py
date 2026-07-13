# retrieval/retrieval.py
# Builds the memory context block injected into each conversation.
# v2-universal: injects permanent memories + recent normal memories always,
# plus session summaries and depth-triggered raw messages.

import re
from config.settings import (
    DEPTH_TRIGGER_THRESHOLD,
    RAW_MESSAGE_FETCH_LIMIT,
    SESSION_SUMMARY_LOAD_N,
    DEPTH_HIGH, DEPTH_MID,
)
from app.data.db import (
    get_permanent_memories,
    get_all_active_memories,
    get_recent_session_summaries,
    get_raw_session_messages,
    touch_memory,
)
from app.memory.similarity import find_similar_session

# How many recent normal memories to always inject (on top of permanents)
RECENT_NORMAL_INJECT = 20

# ── depth scoring ─────────────────────────────────────────────────────────────
# Pre-compile regex patterns for better performance
_DEEP_PATTERNS = [
    re.compile(r"\bin (full|detail|depth)\b"),
    re.compile(r"\btell me (everything|all|exactly)\b"),
    re.compile(r"\bexact(ly)?\b"),
    re.compile(r"\bmore (about|on|detail)\b"),
    re.compile(r"\bexpand\b"),
    re.compile(r"\bgo deeper\b"),
]
_SHALLOW_PATTERNS = [
    re.compile(r"\bdo you remember\b"),
    re.compile(r"\bdidn'?t i (mention|say|tell)\b"),
    re.compile(r"\byou know (that|the)\b"),
    re.compile(r"\bremember when\b"),
]
_REMEMBER_PATTERN = re.compile(r"\bremember\b")

def depth_score(text: str) -> float:
    lowered = text.lower()
    deep_hits    = sum(1 for p in _DEEP_PATTERNS    if p.search(lowered))
    shallow_hits = sum(1 for p in _SHALLOW_PATTERNS if p.search(lowered))
    if deep_hits >= 2:    return 0.9
    if deep_hits == 1:    return 0.75
    if shallow_hits >= 1: return 0.35
    if _REMEMBER_PATTERN.search(lowered): return 0.5
    return 0.0

def is_recall_query(text: str) -> bool:
    return depth_score(text) > 0.0

# ── context assembly ──────────────────────────────────────────────────────────
def build_memory_context(user_message: str, active_memories: list[dict] | None = None) -> str:
    parts: list[str] = []
    
    # Use provided memories or fetch fresh (for backward compatibility)
    if active_memories is None:
        active_memories = get_all_active_memories()

    # 1. Permanent memories — always injected, full trust
    permanents = [m for m in active_memories if m.get("permanent")]
    if permanents:
        perm_lines = []
        for mem in permanents:
            _touch(mem["id"])
            line = mem.get("summary") or mem["raw_extract"]
            perm_lines.append(f"  • {line}")
        parts.append(
            "PERMANENT USER FACTS (treat as ground truth, never contradict):\n"
            + "\n".join(perm_lines)
        )

    # 2. Recent normal memories — inject top N sorted by last_accessed
    #    This is the key change: all active memories are always in context,
    #    not just the ones that happen to score high on similarity.
    normals = [
        m for m in active_memories
        if m["tier"] == "normal" and not m.get("permanent")
    ]
    # sort by last_accessed descending, take top N
    normals_sorted = sorted(
        normals,
        key=lambda m: m.get("last_accessed") or m.get("created_at") or "",
        reverse=True
    )[:RECENT_NORMAL_INJECT]

    if normals_sorted:
        norm_lines = []
        for mem in normals_sorted:
            line = mem.get("summary") or mem["raw_extract"]
            conf = mem["confidence"]
            norm_lines.append(f"  • {line}  [conf: {conf:.2f}]")
        parts.append(
            "RECENT MEMORIES (use to inform responses, don't narrate unless asked):\n"
            + "\n".join(norm_lines)
        )

    # 3. Session summaries — only fetch if depth suggests it's needed
    depth = depth_score(user_message)
    if depth > DEPTH_TRIGGER_THRESHOLD:
        summaries = get_recent_session_summaries(SESSION_SUMMARY_LOAD_N)
        if summaries:
            sum_lines = []
            for s in summaries:
                sum_lines.append(f"  [{s['started_at'][:10]}] {s['summary']}")
            parts.append("PAST SESSION SUMMARIES:\n" + "\n".join(sum_lines))

            # 4. Depth trigger — pull raw messages from a matching past session
            matches = find_similar_session(user_message, summaries, threshold=DEPTH_TRIGGER_THRESHOLD)
            if matches:
                top = matches[0]
                raw = get_raw_session_messages(top["id"], limit=RAW_MESSAGE_FETCH_LIMIT)
                if raw:
                    raw_lines = [f"  [{m['role'].upper()}] {m['content']}" for m in raw]
                    parts.append(
                        f"DEEP CONTEXT from session {top['id']} "
                        f"(similarity {top['_sim_score']:.2f}):\n"
                        + "\n".join(raw_lines)
                    )

    return "\n\n".join(parts)


def build_recall_response_hint(user_message: str, memories: list[dict]) -> str | None:
    score = depth_score(user_message)
    if score == 0.0 or not memories:
        return None
    from app.memory.similarity import find_similar_memory
    match = find_similar_memory(user_message, memories, threshold=0.2)
    if not match:
        return None
    _touch(match["id"])
    extract = match.get("summary") or match["raw_extract"]
    conf    = match["confidence"]
    chain   = _format_contradiction_hint(match)

    if score < DEPTH_MID:
        hint = (
            f'RECALL HINT: You remember this — "{extract}" (conf: {conf:.2f}). '
            f'Respond naturally, weave it in, offer more if relevant.'
        )
    elif score < DEPTH_HIGH:
        hint = (
            f'RECALL HINT: Give a clear summary. Core memory: "{extract}". '
            f'Conf: {conf:.2f}. {chain}Offer to go deeper.'
        )
    else:
        hint = (
            f'RECALL HINT: Full detail requested. Surface everything: "{extract}". '
            f'Conf: {conf:.2f}. {chain}Use raw session context above if available.'
        )
    return hint


def _format_contradiction_hint(mem: dict) -> str:
    if not mem.get("superseded_by"):
        return ""
    return "Note: this belief has evolved — acknowledge the transition if relevant. "


def _touch(memory_id: int) -> None:
    try:
        touch_memory(memory_id)
    except Exception:
        pass
