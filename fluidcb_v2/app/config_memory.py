# ── config/settings.py ────────────────────────────────────────────────────────
# All tunable constants live here. Change values here, never in logic files.

# ── model ─────────────────────────────────────────────────────────────────────
OLLAMA_MODEL = "Qwen3:latest"

# ── memory tiers ──────────────────────────────────────────────────────────────
TIER_NORMAL_TTL_DAYS    = 60
TIER_NOT_WORTH_TTL_DAYS = 14

# ── classifier weights ────────────────────────────────────────────────────────
LLM_WEIGHT  = 0.7
RULE_WEIGHT = 0.3

TIER_ESSENTIAL_THRESHOLD = 2.5   # weighted score → normal  (no essential tier, maps to high-confidence normal)
TIER_NORMAL_THRESHOLD    = 1.5   # weighted score → not_worth below this

# ── confidence ────────────────────────────────────────────────────────────────
CONFIDENCE_PERMANENT_MIN  = 0.85  # confidence floor for permanent promotion
EMOTION_SKIP_THRESHOLD    = 0.3   # skip emotion extraction below this + not_worth
SUMMARY_SKIP_CHARS        = 120   # skip summarisation if raw_extract shorter than this

# ── forgetting curve ──────────────────────────────────────────────────────────
STABILITY_INIT            = 1.0   # starting S value for new memories
STABILITY_REINFORCE_DELTA = 1.5   # S increment on each reinforcement
STABILITY_PERMANENT_MIN   = 15.0  # stability floor for permanent promotion
FORGETTING_ARCHIVE_THRESHOLD = 0.2   # R below this for 30+ days → archive
FORGETTING_ARCHIVE_DAYS      = 30

# ── retrieval ─────────────────────────────────────────────────────────────────
DEPTH_TRIGGER_THRESHOLD   = 0.7   # cosine sim floor to pull raw session messages
RAW_MESSAGE_FETCH_LIMIT   = 20    # max raw messages pulled when depth triggered
SESSION_SUMMARY_LOAD_N    = 5     # how many past session summaries to always load
RECENT_MESSAGES_LIMIT     = 10    # messages loaded from current session

# ── depth scoring bands ───────────────────────────────────────────────────────
DEPTH_HIGH  = 0.7   # full recall + raw messages
DEPTH_MID   = 0.4   # summary + key details
# below DEPTH_MID → one-liner + safety trigger prompt

# ── session summarisation ─────────────────────────────────────────────────────
SESSION_SUMMARY_SENTENCES = 5
