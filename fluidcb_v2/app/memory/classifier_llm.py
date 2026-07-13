# ── memory/classifier_llm.py ──────────────────────────────────────────────────
# LLM-based classifier. Single Ollama call that returns:
#   score (1–3), confidence (0–1), emotion JSON, raw_extract string
# All parsing is defensive — never crashes on bad model output.

import json
import re
import requests
from config.settings import OLLAMA_MODEL, EMOTION_SKIP_THRESHOLD

_SYSTEM_PROMPT = """
You are a memory classification engine. Given a message from a user, you must:

1. Decide how important this information is to remember long-term:
   - score 3: personal facts, health, family, identity, beliefs, values, goals, strong preferences, anything the user tells you about themselves
   - score 2: interests, observations, recent events, soft preferences, ongoing projects
   - score 1: pure throwaway (single-word replies, system noise, completely content-free messages)
   - when in doubt, score 2 — it is better to remember too much than forget something important

2. Assign a confidence (0.0–1.0) in your classification.

3. Extract the core fact in one concise sentence (raw_extract).
   - Be specific: not "user mentioned family" but "user's son diagnosed with dementia"
   - Use third person: "user thinks...", "user's ...", "user prefers..."
   - If nothing worth extracting, set raw_extract to null.

4. Tag the emotional register ONLY if score >= 2 and confidence >= {emotion_threshold}:
   - primary: one of [neutral, curious, excited, frustrated, distressed, grieving, proud, conflicted, resigned, anxious]
   - secondary: same list or null
   - intensity: 0.0–1.0

Reply ONLY with valid JSON. No explanation, no markdown. Example:
{{
  "score": 3,
  "confidence": 0.9,
  "raw_extract": "user's son was diagnosed with dementia",
  "emotion": {{
    "primary": "distressed",
    "secondary": "resigned",
    "intensity": 0.8
  }}
}}
""".strip()


def llm_classify(text: str) -> dict:
    """
    Returns dict with keys:
        score (int 1–3)
        confidence (float 0–1)
        raw_extract (str | None)
        emotion (dict | None)
    Falls back to safe defaults on any failure.
    """
    system = _SYSTEM_PROMPT.format(emotion_threshold=EMOTION_SKIP_THRESHOLD)
    try:
        from app.config import OLLAMA_URL
        resp = requests.post(
            OLLAMA_URL,
            json={
                "model": OLLAMA_MODEL,
                "messages": [
                    {"role": "system", "content": system},
                    {"role": "user",   "content": text},
                ],
                "stream": False,
                "think": False,
            },
            timeout=30,
        )
        raw = resp.json()["message"]["content"].strip()
        return _parse(raw)
    except Exception:
        return _fallback()


def _parse(raw: str) -> dict:
    # strip markdown fences if model wrapped output
    raw = re.sub(r"```(?:json)?|```", "", raw).strip()
    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        # try to extract JSON object from noisy output
        match = re.search(r"\{.*\}", raw, re.S)
        if not match:
            return _fallback()
        try:
            data = json.loads(match.group())
        except json.JSONDecodeError:
            return _fallback()

    score      = int(data.get("score", 2))
    confidence = float(data.get("confidence", 0.5))
    extract    = data.get("raw_extract") or None
    emotion    = data.get("emotion") or None

    # clamp ranges
    score      = max(1, min(3, score))
    confidence = max(0.0, min(1.0, confidence))

    # validate emotion shape
    if emotion and not isinstance(emotion, dict):
        emotion = None
    if emotion:
        emotion = {
            "primary":   emotion.get("primary", "neutral"),
            "secondary": emotion.get("secondary"),
            "intensity": float(emotion.get("intensity", 0.5)),
        }

    return {
        "score":       score,
        "confidence":  confidence,
        "raw_extract": extract,
        "emotion":     emotion,
    }


def _fallback() -> dict:
    return {
        "score":       2,
        "confidence":  0.3,
        "raw_extract": None,
        "emotion":     None,
    }
