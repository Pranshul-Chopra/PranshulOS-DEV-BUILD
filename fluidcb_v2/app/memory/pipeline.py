# ── memory/pipeline.py ────────────────────────────────────────────────────────
# Orchestrates the full memory save pipeline:
#   repeat check → classify → reconcile → extract → summarise → insert
#
# Called from a background thread after each message — never blocks streaming.
#
# Option 2 optimisation: rule_classify() runs first (pure Python, ~0ms).
# If it scores 1 (not worth remembering), we skip the LLM classify call
# entirely (~2-8s saved on ~70% of messages).

import math
import json
import requests
from config.settings import (
    LLM_WEIGHT, RULE_WEIGHT,
    TIER_ESSENTIAL_THRESHOLD, TIER_NORMAL_THRESHOLD,
    CONFIDENCE_PERMANENT_MIN, STABILITY_PERMANENT_MIN,
    STABILITY_REINFORCE_DELTA, STABILITY_INIT,
    SUMMARY_SKIP_CHARS, EMOTION_SKIP_THRESHOLD,
    OLLAMA_MODEL,
)
from app.memory.classifier_rules import rule_classify
from app.memory.classifier_llm import llm_classify
from app.memory.similarity import find_similar_memory
from app.data.db import (
    insert_memory, reinforce_memory, promote_memory,
    mark_permanent, supersede_memory, get_all_active_memories,
)


# ── public entry point ────────────────────────────────────────────────────────

def process_message(session_id: int, text: str) -> None:
    """
    Full pipeline. Called in a background thread after save_message().
    Silently classifies and stores/updates memory. Never raises to caller.
    """
    try:
        _run(session_id, text)
    except Exception as e:
        print(f"[memory pipeline error: {e}]")


# ── pipeline stages ───────────────────────────────────────────────────────────

def _run(session_id: int, text: str) -> None:

    # 1. Rule classifier first — pure Python, ~0ms
    rule_score, rule_conf = rule_classify(text)

    # ── Option 2: early-exit for clearly throwaway messages ──────────────────
    # If rules confidently say score=1 (low value), skip the LLM call.
    # This saves 2–8s on ~70% of messages (greetings, casual remarks, etc.)
    if rule_score == 1 and rule_conf >= 0.70:  # stricter — only skip if very confident
        return

    # 2. LLM classify — only runs when rules think something is worth storing
    llm_result  = llm_classify(text)

    llm_score   = llm_result["score"]
    llm_conf    = llm_result["confidence"]
    raw_extract = llm_result["raw_extract"]
    emotion     = llm_result["emotion"]

    if not raw_extract:
        return  # nothing worth extracting

    # 3. reconcile scores
    weighted = (llm_score * LLM_WEIGHT) + (rule_score * RULE_WEIGHT)
    tier, confidence = _resolve_tier(weighted, llm_score, llm_conf, rule_conf)

    # 4. emotion skip
    if tier == "not_worth" and confidence < EMOTION_SKIP_THRESHOLD:
        emotion = None

    # 5. repeat check against existing memories
    # Only load if we might store something (saves DB lookup for throwaway messages)
    existing = get_all_active_memories()
    match = find_similar_memory(raw_extract, existing)

    if match:
        _handle_repeat(match, tier, confidence, session_id, raw_extract, emotion)
        return

    # 6. summarise if needed
    summary = _summarise(raw_extract) if len(raw_extract) > SUMMARY_SKIP_CHARS else None

    # 7. insert new memory row
    new_id = insert_memory(
        session_id  = session_id,
        tier        = tier,
        confidence  = confidence,
        raw_extract = raw_extract,
        summary     = summary,
        emotion     = emotion,
        stability   = STABILITY_INIT,
    )

    # 8. check immediate permanent promotion
    _check_permanent(new_id, confidence, STABILITY_INIT)


def _handle_repeat(
    match:      dict,
    new_tier:   str,
    new_conf:   float,
    session_id: int,
    raw_extract: str,
    emotion:    dict | None,
) -> None:
    """Reinforce existing memory. Promote tier if warranted. Check permanent."""
    mem_id   = match["id"]
    cur_tier = match["tier"]
    cur_conf = match["confidence"]
    cur_stab = match["stability"]

    new_stability = cur_stab + STABILITY_REINFORCE_DELTA

    tier_rank = {"not_worth": 1, "normal": 2}
    if tier_rank[new_tier] > tier_rank[cur_tier]:
        promoted_conf = max(new_conf, cur_conf)
        promote_memory(mem_id, new_tier, promoted_conf)
        reinforce_memory(mem_id, new_stability)
        _check_permanent(mem_id, promoted_conf, new_stability)
    else:
        reinforce_memory(mem_id, new_stability)
        _check_permanent(mem_id, cur_conf, new_stability)

    if raw_extract.lower().strip() != match["raw_extract"].lower().strip():
        summary = _summarise(raw_extract) if len(raw_extract) > SUMMARY_SKIP_CHARS else None
        new_id = insert_memory(
            session_id  = session_id,
            tier        = new_tier,
            confidence  = new_conf,
            raw_extract = raw_extract,
            summary     = summary,
            emotion     = emotion,
            stability   = new_stability,
        )
        supersede_memory(mem_id, new_id)


def _resolve_tier(
    weighted:   float,
    llm_score:  int,
    llm_conf:   float,
    rule_conf:  float,
) -> tuple[str, float]:
    blended_conf = (llm_conf * LLM_WEIGHT) + (rule_conf * RULE_WEIGHT)

    if weighted >= TIER_ESSENTIAL_THRESHOLD:
        return "normal", min(blended_conf + 0.1, 1.0)

    if weighted >= TIER_NORMAL_THRESHOLD:
        if llm_score == 3:
            return "normal", blended_conf
        return "normal", blended_conf

    if llm_score == 3:
        return "normal", max(blended_conf - 0.1, 0.3)

    return "not_worth", blended_conf


def _check_permanent(memory_id: int, confidence: float, stability: float) -> None:
    if confidence >= CONFIDENCE_PERMANENT_MIN and stability >= STABILITY_PERMANENT_MIN:
        mark_permanent(memory_id)


def _summarise(text: str) -> str | None:
    """Ask the model to compress a raw extract into a useful one-liner."""
    try:
        from app.config import OLLAMA_URL
        resp = requests.post(
            OLLAMA_URL,
            json={
                "model": OLLAMA_MODEL,
                "messages": [
                    {
                        "role": "system",
                        "content": (
                            "Compress the following memory extract into one concise, useful sentence. "
                            "Keep specific facts. Use third person. "
                            "No preamble, no explanation — just the compressed sentence."
                        ),
                    },
                    {"role": "user", "content": text},
                ],
                "stream": False,
                "think": False,
            },
            timeout=30,
        )
        summary = resp.json()["message"]["content"].strip()
        return summary if summary else None
    except Exception:
        return None
