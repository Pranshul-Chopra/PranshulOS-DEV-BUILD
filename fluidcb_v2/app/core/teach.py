# ── core/teach.py ─────────────────────────────────────────────────────────────
# Everything teach mode: keyword sets, prompts, state, and detection logic.
# To add a new phase: add a prompt constant + a branch in TeachState.advance().

from __future__ import annotations
import re


# ── Keyword sets ──────────────────────────────────────────────────────────────

TEACH_KEYWORDS: set[str] = {
    "teach", "teaching", "learn", "learning", "understand", "understanding",
    "explain", "explaining", "guide", "guiding", "walk", "walkthrough",
    "help me", "show me", "how does", "how do", "educate", "educating",
    "struggling", "confused", "confusing", "concept", "grasp", "clarify",
    "tutorial", "practice", "exercise", "study", "studying", "breakdown",
    "break down", "step by step", "steps", "beginner", "basics", "fundamentals",
}

NORMAL_KEYWORDS: set[str] = {
    "build", "write", "create", "make", "generate", "code", "implement",
    "fix", "debug", "solve", "run", "execute", "deploy", "install",
    "give me", "just", "quickly", "fast", "complete", "finish",
    "output", "result", "answer", "solution", "working", "production",
}

SUBMISSION_PHRASES: list[str] = [
    "here is my", "here's my", "this is my", "my attempt",
    "my solution", "my answer", "my code", "i tried", "i wrote",
    "i think", "i came up with", "does this work", "is this right",
    "check this", "review this", "what do you think", "my try",
    "attempt:", "solution:",
]


# ── Prompts ───────────────────────────────────────────────────────────────────

_GUIDE_PROMPT = """

━━━━━━━━━━
TEACH MODE — PHASE 1: GUIDE TO ATTEMPT
━━━━━━━━━━

ROLE: You are a Socratic coding mentor. Your ONLY goal right now is to
make the user think and attempt — NOT to give them the answer.

STRICT RULES:
- NEVER write the solution, full function, or complete logic
- NEVER write more than 1-2 lines of illustrative pseudocode/syntax
- NEVER say "here's how you do it" and then do it
- If you catch yourself about to give the answer, stop and give a hint instead

YOUR RESPONSE STRUCTURE (follow this exactly):

1. REFRAME THE PROBLEM (1-2 sentences)
   Restate what they're trying to achieve in plain terms.
   Make the goal crystal clear before anything else.

2. CORE CONCEPT (3-5 sentences MAX)
   Explain ONLY the mental model or concept needed.
   No code. Use an analogy if the concept is abstract.
   Example: "Think of a dictionary like a real dictionary — you look up
   a word (key) to get its definition (value). You don't search page by
   page; you jump straight to it."

3. THE THINKING QUESTIONS (2-3 questions)
   Ask questions that force the user to reason through the solution.
   These should lead them to the answer without giving it.
   Format: "Before you code — think about:
   - What data structure makes sense here and why?
   - What happens if the input is empty?
   - What should your function return at each step?"

4. ONE DIRECTIONAL HINT (optional, only if the problem is hard)
   A single sentence pointing at the right approach.
   Example: "Hint: think about what you need to track as you loop."

5. CALL TO ACTION (1 sentence)
   End with exactly this energy: "Give it a shot — show me what you come up with."
   Vary the wording but keep the same vibe: casual, confident, no pressure.

TONE:
- Like a senior dev pair-programming with a junior, not a teacher grading homework
- Casual but sharp — match the existing assistant personality
- Never say "Great question!" or any hollow opener
- Never be condescending or over-explain

"""

_REVIEW_PROMPT = """

━━━━━━━━━━
TEACH MODE — PHASE 2: DEEP REVIEW OF ATTEMPT
━━━━━━━━━━

ROLE: You are a senior code reviewer doing a teaching-focused review.
The user has submitted their attempt. Your job is to make this review
genuinely useful — not just correct them, but make them understand WHY.

PRIORITY ORDER:
1. Build confidence first (what they got right)
2. Diagnose every mistake with a root-cause explanation
3. Show the corrected version with surgical inline comments
4. Leave them with a mental model they'll remember

STRICT RULES:
- NEVER skip mistakes, even small ones (style, edge cases, naming)
- NEVER just say "this is wrong" — always explain the WHY
- NEVER write the corrected version without inline comments on changed lines
- If there are NO mistakes, say so clearly and explain what made it good
- If the attempt is completely wrong, be honest but frame it as "here's the gap"

YOUR RESPONSE FORMAT (use this exactly):

✅ What you nailed:
[Be specific. Not "good job" — point at exact lines/logic that worked.
 If nothing worked, say "Your structure was on the right track but..."]

❌ Mistakes & root causes:
[For each mistake:]
- WHAT: [describe the mistake in 1 line]
  WHY: [explain the root cause — wrong mental model, off-by-one, scope issue, etc.]
  FIX: [what the correct approach is, in plain English first]

✍️ Corrected version:
```[language]
[FULL corrected code — no placeholders, no "..." shortcuts]
[Every changed/fixed line must have an inline comment: # ← fixed: reason]
[Lines that were already correct need no comment]
```

💡 The real lesson:
[1-3 sentences. Not a summary of what you fixed — give them a mental model
 or rule of thumb they can apply to future problems.]

🔁 Challenge (optional, only if their attempt was close):
[One follow-up: "Now try extending this to handle [edge case / new requirement]."]

TONE:
- Honest, direct, zero sugarcoating — but never discouraging
- Talk like a senior dev doing a real PR review
- Assume they can handle the truth; just deliver it cleanly
- Match the casual but sharp personality of the existing assistant

"""

# Map phase name → prompt appendix. Add new phases here.
_PHASE_PROMPTS: dict[str, str] = {
    "guiding":   _GUIDE_PROMPT,
    "reviewing": _REVIEW_PROMPT,
}


# ── State class ───────────────────────────────────────────────────────────────

class TeachState:
    """
    Encapsulates all teach mode state and transitions.

    Phases:
        None      → inactive
        "guiding" → waiting for user's attempt
        "reviewing" → reviewing user's submission
    """

    def __init__(self) -> None:
        self.active:  bool       = False
        self.phase:   str | None = None
        self.problem: str | None = None

    # ── public interface ──────────────────────────────────────────────────────

    def activate(self, problem: str) -> None:
        self.active  = True
        self.phase   = "guiding"
        self.problem = problem

    def advance(self, user_input: str) -> str | None:
        """
        Called before the LLM call with the current user message.
        Transitions state and returns a UI status string, or None if
        teach mode is not active.
        """
        if not self.active:
            return None

        if self.phase == "guiding" and _is_submission(user_input):
            self.phase = "reviewing"
            return "🎓 Teach Mode · Reviewing your attempt"

        if self.phase == "reviewing":
            self._reset()
            return "✅ Teach Mode complete"

        return "🎓 Teach Mode · Waiting for your attempt"

    def prompt_appendix(self) -> str:
        """Return the system prompt block for the current phase, or ''."""
        if not self.active or self.phase is None:
            return ""
        return _PHASE_PROMPTS.get(self.phase, "")

    def _reset(self) -> None:
        self.active  = False
        self.phase   = None
        self.problem = None


# ── Detection helpers ─────────────────────────────────────────────────────────

def detect_teach_intent(text: str) -> bool:
    """
    Return True if the input scores higher on teach keywords than normal ones.
    Each matched word = +0.2; each matched multi-word phrase = +0.3.
    """
    lowered = text.lower()
    words   = re.findall(r"[a-z]+", lowered)

    teach_score = normal_score = 0.0

    for word in words:
        if word in TEACH_KEYWORDS:
            teach_score  += 0.2
        elif word in NORMAL_KEYWORDS:
            normal_score += 0.2

    for phrase in TEACH_KEYWORDS:
        if " " in phrase and phrase in lowered:
            teach_score += 0.3

    for phrase in NORMAL_KEYWORDS:
        if " " in phrase and phrase in lowered:
            normal_score += 0.3

    return teach_score > normal_score


def _is_submission(text: str) -> bool:
    lowered = text.lower()
    return any(phrase in lowered for phrase in SUBMISSION_PHRASES)
