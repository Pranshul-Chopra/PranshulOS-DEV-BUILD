# All tunable constants live here.

# model
# Model used by the memory pipeline — deliberately separate from the main chat model
# so classify/summarise calls don't compete with Qwen3 on GPU during streaming.
# gemma3:4b is already on-device for Screen Assist and is fast enough for JSON classification.
OLLAMA_MODEL = "gemma3:4b"

# memory tiers — longer TTL so nothing gets forgotten quickly
TIER_NORMAL_TTL_DAYS    = 365   # was 60 — keep normal memories for a year
TIER_NOT_WORTH_TTL_DAYS = 30    # was 14

# classifier weights
LLM_WEIGHT  = 0.7
RULE_WEIGHT = 0.3
TIER_ESSENTIAL_THRESHOLD = 2.5
TIER_NORMAL_THRESHOLD    = 1.5

# confidence — lowered so more things get promoted to permanent
CONFIDENCE_PERMANENT_MIN  = 0.55   # was 0.85 — much easier to go permanent
EMOTION_SKIP_THRESHOLD    = 0.3
SUMMARY_SKIP_CHARS        = 120

# forgetting curve — lowered stability requirement so memories stick
STABILITY_INIT            = 1.0
STABILITY_REINFORCE_DELTA = 1.5
STABILITY_PERMANENT_MIN   = 3.0    # was 15.0 — much lower bar to go permanent

FORGETTING_ARCHIVE_THRESHOLD = 0.05   # was 0.2 — archive only truly dead memories
FORGETTING_ARCHIVE_DAYS      = 180    # was 30 — wait 6 months before archiving

# retrieval — load more past sessions, lower depth trigger
DEPTH_TRIGGER_THRESHOLD   = 0.35   # consistent with retrieval.py usage
RAW_MESSAGE_FETCH_LIMIT   = 30     # was 20
SESSION_SUMMARY_LOAD_N    = 15     # was 5 — load more past sessions

# depth scoring bands
DEPTH_HIGH  = 0.7
DEPTH_MID   = 0.4

# session summarisation
SESSION_SUMMARY_SENTENCES = 7      # was 5 — more detail in summaries
