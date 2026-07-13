# ── memory/classifier_rules.py ────────────────────────────────────────────────
# Fast keyword/pattern-based classifier.
# Returns a score 1–3 and a rough confidence.
# 3 = normal (high value), 2 = normal, 1 = not_worth

import re

# ── pattern banks ──────────────────────────────────────────────────────────────

# Strong signals → score 3
_HIGH_PATTERNS = [
    r"\b(diagnosed|diagnosis|condition|disorder|disease|syndrome|illness)\b",
    r"\b(allerg(y|ic|ies))\b",
    r"\bmy (son|daughter|child|kids?|wife|husband|partner|mother|father|parent|sibling|brother|sister)\b",
    r"\b(died|passed away|death|grieving|funeral)\b",
    r"\b(disability|disabled|chronic|terminal)\b",
    r"\b(trauma|abuse|assault|survivor)\b",
    r"\b(believe|think|value|principle|philosophy|worldview)\b",
    r"\b(always|never|every time|consistently|fundamental(ly)?)\b",
    r"\bi (am|was) (a|an) \w+",            # identity statements
    r"\bmy (job|career|profession|work) (is|was|involves)\b",
]

# Medium signals → score 2
_MEDIUM_PATTERNS = [
    r"\b(prefer|prefer(ence)?|favourite|favorite|like|dislike|hate|love)\b",
    r"\b(goal|plan|project|building|working on)\b",
    r"\b(noticed|realised|realized|learned|found out)\b",
    r"\b(yesterday|last week|recently|just)\b",
    r"\b(recommend|suggestion|advice)\b",
    r"\b(interesting|fascinating|excited|curious)\b",
]

# Explicit throwaway signals → score 1
_LOW_PATTERNS = [
    r"\b(lunch|breakfast|dinner|snack|ate|eating|had (a |some )?\w+ (today|just now|for lunch))\b",
    r"\b(weather|hot|cold|raining|sunny) (today|outside|right now)\b",
    r"\b(tired|sleepy|bored) (right now|today|atm)\b",
    r"\b(watching|saw) (a |an )?(movie|show|episode|video)\b",
]

# Escalation overrides — even in throwaway context, these promote to score 3
_ESCALATION_OVERRIDES = [
    r"\b(allerg(y|ic))\b",
    r"\b(intoleran(t|ce))\b",
    r"\b(can('t| not) (eat|have|drink|take))\b",
    r"\b(makes? (me|him|her|them) (sick|ill|react))\b",
    r"\b(medic(ation|ine|al))\b",
    r"\b(hospitali[sz]ed?)\b",
]


def rule_classify(text: str) -> tuple[int, float]:
    """
    Returns (score, confidence).
    score: 1=not_worth, 2=normal, 3=high-value normal
    confidence: rough 0–1 estimate from rule density
    """
    lowered = text.lower()

    # escalation check first — overrides everything
    for pat in _ESCALATION_OVERRIDES:
        if re.search(pat, lowered):
            return 3, 0.8

    high_hits   = sum(1 for p in _HIGH_PATTERNS   if re.search(p, lowered))
    medium_hits = sum(1 for p in _MEDIUM_PATTERNS if re.search(p, lowered))
    low_hits    = sum(1 for p in _LOW_PATTERNS    if re.search(p, lowered))

    if high_hits >= 1:
        confidence = min(0.6 + high_hits * 0.1, 0.85)
        return 3, confidence

    if medium_hits >= 1 and low_hits == 0:
        confidence = min(0.4 + medium_hits * 0.08, 0.65)
        return 2, confidence

    if low_hits >= 1 and high_hits == 0:
        confidence = min(0.3 + low_hits * 0.05, 0.55)
        return 1, confidence

    # ambiguous — call it normal with low confidence
    return 2, 0.3
