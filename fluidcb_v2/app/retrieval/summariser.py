# ── retrieval/summariser.py ───────────────────────────────────────────────────
# Generates a 3–5 sentence session summary when a session ends.
# Also runs the forgetting curve archive pass.

import requests
from config.settings import OLLAMA_MODEL, SESSION_SUMMARY_SENTENCES
from app.data.db import get_raw_session_messages, end_session, archive_stale_memories


def close_session(session_id: int) -> None:
    """
    Called when a chat session ends.
    Summarises the session, saves it, then runs the archive pass.
    """
    messages = get_raw_session_messages(session_id, limit=50)  # Reduced from 200 for better performance
    if not messages:
        return

    summary = _summarise_session(messages)
    end_session(session_id, summary)

    archived = archive_stale_memories()
    if archived:
        print(f"[memory] archived {archived} stale memories.")


def _summarise_session(messages: list[dict]) -> str:
    # Use list comprehension + join for better performance (vs loop concatenation)
    transcript_lines = [
        f"{m['role'].upper()}: {m['content']}" for m in messages
    ]
    transcript = "\n".join(transcript_lines)
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
                            f"Summarise this conversation in {SESSION_SUMMARY_SENTENCES} sentences or fewer. "
                            "Focus on: what topics were covered, what the user revealed about themselves, "
                            "any decisions made, any problems solved. "
                            "Be specific and factual. Third person for the user. "
                            "No preamble — output the summary directly."
                        ),
                    },
                    {"role": "user", "content": transcript},
                ],
                "stream": False,
            },
            timeout=60,
        )
        return resp.json()["message"]["content"].strip()
    except Exception as e:
        return f"[session summary unavailable: {e}]"
