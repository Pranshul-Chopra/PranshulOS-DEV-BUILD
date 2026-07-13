# ── core/llm.py ───────────────────────────────────────────────────────────────
# Conversation history, system prompt assembly, Ollama streaming.

import re
import json
import threading
import requests
from typing import Generator
from app.config import OLLAMA_URL, MODEL
from app.core.modes import get_base_identity
from app.core.teach import TeachState

from app.data.db import (
    init_db, create_session, save_message as db_save_message,
    get_all_active_memories,
)
from app.memory.pipeline import process_message
from app.retrieval.retrieval import (
    build_memory_context, build_recall_response_hint, is_recall_query,
)
from app.memory.similarity import clear_vector_cache
from app.retrieval.summariser import close_session

# ── Tuning ─────────────────────────────────────────────────────────────────────
MAX_HISTORY = 10

# ── State ──────────────────────────────────────────────────────────────────────
_history:    list[dict] = []
teach        = TeachState()

# Always start a fresh session on boot
init_db()
_session_id: int = create_session()

# ── Memory Cache (request-scoped) ──────────────────────────────────────────────
_memory_cache: dict = {}
_cache_valid: bool = False

def _get_cached_memories() -> list[dict]:
    global _memory_cache, _cache_valid
    if not _cache_valid:
        _memory_cache = get_all_active_memories()
        _cache_valid = True
    return _memory_cache

def _invalidate_memory_cache() -> None:
    global _cache_valid
    _cache_valid = False
    clear_vector_cache()


# ── Public API ─────────────────────────────────────────────────────────────────

def invalidate_memory_cache() -> None:
    pass  # no-op — pipeline handles its own state

def clear_history() -> None:
    global _session_id
    close_session(_session_id)
    _history.clear()
    _session_id = create_session()

def get_personality_status() -> dict[str, float]:
    return {}

def get_session_id() -> int:
    return _session_id


# ── System prompt ──────────────────────────────────────────────────────────────

def _build_system_prompt(query: str, tool_result: str = "") -> str:
    tool_block = ""
    if tool_result:
        tool_block = (
            "\n━━━━━━━━━━\nTOOL RESULTS\n━━━━━━━━━━\n"
            + tool_result
            + "\n\nUse the above to inform your response naturally. "
            "Do not say 'I searched' or 'according to my search'.\n"
        )

    memory_block = build_memory_context(query, _get_cached_memories())

    recall_hint = ""
    if is_recall_query(query):
        active = _get_cached_memories()
        hint = build_recall_response_hint(query, active)
        if hint:
            recall_hint = hint

    sections = [
        get_base_identity(),
        tool_block,
        memory_block,
        recall_hint,
        teach.prompt_appendix(),
    ]
    return "\n".join(s for s in sections if s)


# ── Code extraction ────────────────────────────────────────────────────────────

def extract_code(text: str) -> str | None:
    blocks = re.findall(r"```(?:\w+)?\n?(.*?)```", text, re.DOTALL)
    if blocks:
        return "\n\n".join(b.strip() for b in blocks)
    return None


# ── Background memory pipeline ─────────────────────────────────────────────────

def _run_memory_pipeline(session_id: int, user_input: str) -> None:
    try:
        process_message(session_id, user_input)
    except Exception as e:
        print(f"[memory pipeline error: {e}]")


# ── Streaming Ollama call ──────────────────────────────────────────────────────

def stream_chat(
    user_input: str,
    tool_result: str = "",
) -> Generator[str, None, None]:
    db_save_message(_session_id, "user", user_input)
    _history.append({"role": "user", "content": user_input})

    messages = [
        {"role": "system", "content": _build_system_prompt(user_input, tool_result)}
    ] + _history[-MAX_HISTORY:]

    full_reply: list[str] = []

    try:
        with requests.post(
            OLLAMA_URL,
            json={"model": MODEL, "messages": messages, "stream": True, "think": False},
            stream=True,
            timeout=120,
        ) as resp:
            resp.raise_for_status()

            for raw_line in resp.iter_lines():
                if not raw_line:
                    continue
                try:
                    chunk = json.loads(raw_line)
                except json.JSONDecodeError:
                    continue

                token = chunk.get("message", {}).get("content", "")
                if token:
                    full_reply.append(token)
                    safe = token.replace("\n", "\\n")
                    yield f"data: {safe}\n\n"

                if chunk.get("done", False):
                    break

    except requests.exceptions.ConnectionError:
        msg = "Can't reach Ollama — is it running? (`ollama serve`)"
        yield f"data: [ERROR] {msg}\n\n"
        _history.pop()
        return

    except requests.exceptions.Timeout:
        msg = "Ollama timed out. The model might be loading; try again."
        yield f"data: [ERROR] {msg}\n\n"
        _history.pop()
        return

    except Exception as exc:
        yield f"data: [ERROR] {exc}\n\n"
        _history.pop()
        return

    reply = "".join(full_reply)
    _history.append({"role": "assistant", "content": reply})
    db_save_message(_session_id, "assistant", reply)

    def _pipeline_with_cache_clear():
        try:
            _run_memory_pipeline(_session_id, user_input)
        finally:
            _invalidate_memory_cache()

    threading.Thread(target=_pipeline_with_cache_clear, daemon=True).start()

    yield "data: [DONE]\n\n"
