# ── core/tool_router.py ───────────────────────────────────────────────────────
# Contextual intent router for tool calling.
#
# Detects one of four intents from a user message:
#   "search"   → user wants AI to search the web
#   "fetch"    → user wants AI to read a specific URL
#   "share"    → user is sharing info they already found (no tool needed)
#   "none"     → regular conversational message — just chat
#
# Key design principle: most messages are normal conversation. We should
# only trigger tools when the user is clearly requesting them. Ambiguous
# messages default to "none" (let the LLM answer naturally).

from __future__ import annotations
import re

# ── Thresholds ────────────────────────────────────────────────────────────────

ACT_THRESHOLD  = 0.45   # raised — must be clearly requesting a tool
WORD_SCORE     = 0.15
PHRASE_SCORE   = 0.30

# Signals that the message is personal/conversational — never ask_user on these
# Pre-compile for performance
_CONVERSATIONAL_SIGNALS = [
    re.compile(r"\bi (was|am|feel|felt|think|thought|saw|noticed|met|know|went|had|been)\b"),
    re.compile(r"\bmy (friend|girl|guy|crush|partner|mom|dad|sister|brother|family|gym|life|day)\b"),
    re.compile(r"\bthere (is|are|was|were) (this|a|some)\b"),
    re.compile(r"\bpart of\b"),
    re.compile(r"\bkinda|kinda\b"),
    re.compile(r"\blike i\b"),
    re.compile(r"\bjust (sharing|venting|saying|telling you)\b"),
]

# Search and fetch detection removed to simplify assistant and reduce latency

# User is sharing what they already found — no tool needed
SHARE_PHRASES: set[str] = {
    "i searched", "i found", "i looked up", "i tried", "i got",
    "i read", "i checked", "i googled", "here's what i got",
    "here is what i found", "according to", "it says that",
    "i got this error", "this is what i got", "i already searched",
    "i just searched",
}

# Embedded factual question detection removed with search/fetch feature removal

# ── Scorer ────────────────────────────────────────────────────────────────────

def _is_conversational(text: str) -> bool:
    """Returns True if the message is clearly personal/emotional context, not a request."""
    lowered = text.lower()
    # Long messages are almost always context-sharing
    if len(text) > 100:
        for pat in _CONVERSATIONAL_SIGNALS:
            if pat.search(lowered):
                return True
    return False


def _score_phrases(text: str, phrases: set[str]) -> float:
    lowered = text.lower()
    score = 0.0
    for phrase in phrases:
        if phrase in lowered:
            score += PHRASE_SCORE if " " in phrase else WORD_SCORE
    return score


def _is_explicit_question(text: str) -> bool:
    """Returns True only if the message is a standalone question, not embedded in conversation."""
    cleaned = text.strip()
    # If the message is long (>100 chars), it's probably conversational context, not a pure question
    if len(cleaned) > 120:
        return False
    # Explicit question detection disabled — questions are handled by the LLM
    return False


# ── Public API ─────────────────────────────────────────────────────────────────

class ToolIntent:
    """Result of routing — what to do and with what."""

    def __init__(
        self,
        intent: str,                  # "search" | "fetch" | "share" | "none"
        query:  str | None = None,
        url:    str | None = None,
    ) -> None:
        self.intent = intent
        self.query  = query
        self.url    = url

    def __repr__(self) -> str:
        return f"ToolIntent({self.intent!r}, query={self.query!r}, url={self.url!r})"


def route(text: str) -> ToolIntent:
    """
    Analyse the user message and return a ToolIntent.

    Priority order:
      1. URL present → fetch (unless user is sharing it as context)
      2. Share signals dominate → share
      3. Explicit search phrases → search
      4. Standalone question patterns → search
      5. Everything else → none (let LLM answer naturally)
    """
    # Simplified routing: only detect explicit 'share' patterns; all other
    # messages are normal conversational messages handled by the LLM.
    share_score = _score_phrases(text, SHARE_PHRASES)
    if share_score >= ACT_THRESHOLD:
        return ToolIntent("share")
    return ToolIntent("none")


def _extract_query(text: str) -> str:
    """
    Extract a clean search query from the user's message.
    """
    strip_phrases = [
        "can you search for", "can you look up", "can you find",
        "search for", "look up", "find", "search", "google",
        "what is", "what are", "who is", "who are",
        "tell me about", "any info on", "information on",
        "check online for", "look online for", "search that up",
        "look that up",
    ]
    # Query extraction removed with search feature removal
    return text.strip()


def _extract_embedded_query(text: str) -> str:
    """
    For messages like "i was watching X, what is Y about it" ->
    extract the question + subject as search query, replacing vague
    pronouns (it/that/this) with the actual subject.
    """
    import re as _re
    # Extract subject: words between trigger verb and question word
    subject = ""
    sub_m = _re.search(
        r"(?:watching|reading|playing|saw|tried|using|listened to)\s+([\w\s]+?)\s+(?:what|who|how|when|where)",
        text, _re.IGNORECASE
    )
    # Embedded query extraction removed with search feature removal
    return text.strip()
