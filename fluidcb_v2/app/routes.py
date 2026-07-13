# ── routes.py ─────────────────────────────────────────────────────────────────
# Flask routes only. No business logic here.

import os
from flask import Blueprint, render_template, request, jsonify, Response, stream_with_context

from app.config import CODE_MEMORY_DIR
from app.core import llm as llm_core
from app.core.teach import detect_teach_intent

bp = Blueprint("main", __name__)
os.makedirs(CODE_MEMORY_DIR, exist_ok=True)

# ── Home panel (quick launch) ─────────────────────────────────────────────────
from flask import render_template_string
from datetime import datetime as _dt

_HOME_HTML = """<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8"/>
  <meta name="viewport" content="width=device-width, initial-scale=1.0"/>
  <title>Home — PranshulOS</title>
  <link rel="stylesheet" href="/static/fonts/ibmflex.css"/>
  <style>
    *, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }
    :root {
      --bg: #0c0c0c; --surface: #141414; --surface2: #1c1c1c;
      --border: #272727; --border2: #333;
      --text: #e8e6e1; --text2: #8a8880; --text3: #4a4845;
      --amber: #e8a84c; --amber-dim: #7a5820; --amber-glow: rgba(232,168,76,0.08);
      --radius: 12px;
      --mono: 'IBM Plex Mono', monospace; --sans: 'IBM Plex Sans', sans-serif;
    }
    html, body { height: 100%; background: var(--bg); color: var(--text); font-family: var(--sans); -webkit-font-smoothing: antialiased; }
    .shell { max-width: 640px; margin: 0 auto; padding: 48px 24px 32px; }
    .greeting { font-size: 24px; font-weight: 300; letter-spacing: -0.02em; margin-bottom: 6px; }
    .greeting em { color: var(--amber); font-style: normal; }
    .sub { font-size: 13px; color: var(--text3); font-family: var(--mono); margin-bottom: 36px; letter-spacing: 0.04em; }
    .section-label { font-family: var(--mono); font-size: 10px; font-weight: 500; color: var(--text3); letter-spacing: 0.12em; text-transform: uppercase; margin-bottom: 12px; }
    .launch-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 10px; margin-bottom: 32px; }
    .launch-btn {
      padding: 16px 18px; border-radius: var(--radius);
      background: var(--surface); border: 1px solid var(--border2);
      color: var(--text); font-family: var(--sans); font-size: 14px;
      text-align: left; cursor: pointer; transition: all 0.15s;
      display: flex; align-items: center; gap: 10px;
    }
    .launch-btn:hover { background: var(--surface2); border-color: var(--amber-dim); }
    .launch-btn .icon { font-size: 18px; }
    .launch-btn .label { font-weight: 400; }
    .launch-btn .desc { font-size: 11px; color: var(--text3); margin-top: 2px; font-family: var(--mono); }
    .divider { height: 1px; background: var(--border); margin: 28px 0; }
    .input-row { display: flex; gap: 10px; }
    .input-box {
      flex: 1; padding: 12px 16px; border-radius: var(--radius);
      background: var(--surface); border: 1px solid var(--border2);
      color: var(--text); font-family: var(--sans); font-size: 14px; outline: none;
      transition: border-color 0.15s;
    }
    .input-box:focus { border-color: var(--amber-dim); }
    .input-box::placeholder { color: var(--text3); }
    .go-btn {
      padding: 12px 24px; border-radius: var(--radius);
      background: var(--amber); color: #0c0c0c; border: none;
      font-family: var(--sans); font-size: 14px; font-weight: 500;
      cursor: pointer; transition: opacity 0.15s;
    }
    .go-btn:hover { opacity: 0.85; }
    .log {
      margin-top: 16px; padding: 14px 16px; border-radius: var(--radius);
      background: var(--surface); border: 1px solid var(--border);
      font-family: var(--mono); font-size: 12px; color: var(--text2);
      min-height: 48px; line-height: 1.8;
    }
    .log .entry { animation: fadein 0.2s ease; }
    .log .entry.you { color: var(--text); }
    .log .entry.reply { color: var(--amber); }
    @keyframes fadein { from { opacity:0; transform: translateY(3px); } to { opacity:1; transform:none; } }
  </style>
</head>
<body>
<div class="shell">
  <div class="greeting">{{ greeting }}</div>
  <div class="sub">what do you want to do?</div>

  <div class="section-label">Quick Launch</div>
  <div class="launch-grid">
    <button class="launch-btn" onclick="launch('work')">
      <span class="icon">💻</span>
      <div><div class="label">Work</div><div class="desc">Spotify + VS Code</div></div>
    </button>
    <button class="launch-btn" onclick="launch('chill')">
      <span class="icon">🎬</span>
      <div><div class="label">Chill</div><div class="desc">YouTube</div></div>
    </button>
    <button class="launch-btn" onclick="launch('open_spotify')">
      <span class="icon">🎵</span>
      <div><div class="label">Spotify</div><div class="desc">Music only</div></div>
    </button>
    <button class="launch-btn" onclick="launch('open_whatsapp')">
      <span class="icon">💬</span>
      <div><div class="label">WhatsApp</div><div class="desc">Web messages</div></div>
    </button>
    <button class="launch-btn" onclick="launch('open_discord')">
      <span class="icon">🎮</span>
      <div><div class="label">Discord</div><div class="desc">Open app</div></div>
    </button>
    <button class="launch-btn" onclick="launch('open_github')">
      <span class="icon">🐙</span>
      <div><div class="label">GitHub</div><div class="desc">Open dashboard</div></div>
    </button>
    <button class="launch-btn" onclick="launch('open_linkedin')">
      <span class="icon">🔗</span>
      <div><div class="label">LinkedIn</div><div class="desc">Your profile</div></div>
    </button>
  </div>

  <div class="divider"></div>
  <div class="section-label">Or just tell me</div>
  <div class="input-row">
    <input class="input-box" id="inp" placeholder='e.g. "bored" or "start work"…' onkeydown="if(event.key==='Enter') go()"/>
    <button class="go-btn" onclick="go()">Go</button>
  </div>
  <div class="log" id="log"><span style="color:var(--text3)">→ hey! what do you need?</span></div>
</div>
<script>
async function launch(fn) {
  const result = await window.pywebview.api[fn]();
  addLog('→ ' + (result || 'done!'), 'reply');
}
async function go() {
  const inp = document.getElementById('inp');
  const text = inp.value.trim();
  if (!text) return;
  addLog('You: ' + text, 'you');
  inp.value = '';
  const result = await window.pywebview.api.check_trigger(text);
  addLog(result ? '→ ' + result : "→ Didn't catch that. Try 'start work', 'bored', 'github'…", 'reply');
}
function addLog(text, cls) {
  const log = document.getElementById('log');
  if (log.children.length === 0 || log.querySelector('span')) log.innerHTML = '';
  const el = document.createElement('div');
  el.className = 'entry ' + cls;
  el.textContent = text;
  log.appendChild(el);
  log.scrollTop = log.scrollHeight;
}
</script>
</body>
</html>"""

@bp.route("/home")
def home():
    h = _dt.now().hour
    if h < 12:   greeting = "Good morning, Pranshul ☀️"
    elif h < 17: greeting = "Good afternoon, Pranshul 🌤"
    else:        greeting = "Good evening, Pranshul 🌙"
    return render_template_string(_HOME_HTML, greeting=greeting)

# Search/confirmation flow removed — search and fetch features disabled.

# ── Memory trigger detection ───────────────────────────────────────────────────

_CODE_TRIGGERS = {
    "save this code", "save this program", "save the code",
    "store this code", "store this program",
    "save this script", "store this script",
}

_TEXT_TRIGGERS = {
    "remember this", "memorize this", "remember it",
    "save it", "store it", "memorize it",
    "this works", "final version", "this is stable", "stable version",
}

def _memory_type(text: str) -> str | None:
    lowered = text.lower()
    if any(t in lowered for t in _CODE_TRIGGERS):
        return "code"
    if any(t in lowered for t in _TEXT_TRIGGERS):
        return "text"
    return None


# ── Routes ─────────────────────────────────────────────────────────────────────

@bp.route("/")
def index():
    return render_template("index.html")


@bp.route("/chat", methods=["POST"])
def chat():
    data       = request.get_json(silent=True) or {}
    user_input = data.get("message", "").strip()

    if not user_input:
        return jsonify({"error": "Empty message"}), 400

    # 1. Teach mode
    teach       = llm_core.teach
    mode_status = teach.advance(user_input)

    if mode_status is None and detect_teach_intent(user_input):
        teach.activate(user_input)
        mode_status = "🎓 Teach Mode activated"

    # 2. /search detection — execution happens inside generate() so SSE opens immediately
    from app.searcher import is_search_command, extract_query, search as run_search
    _is_search    = is_search_command(user_input)
    _search_query = extract_query(user_input) if _is_search else None

    # 3. Memory type (legacy code-save)
    mem_type = _memory_type(user_input)

    # 4. Stream
    accumulated: list[str] = []

    def generate():
        tool_result = ""

        if _is_search:
            # Status fires immediately — user sees feedback before search starts
            yield f"data: [STATUS] 🔍 Searching: {_search_query}\n\n"
            try:
                tool_result = run_search(_search_query)
            except Exception as e:
                tool_result = f"Search failed: {e}"

        for chunk in llm_core.stream_chat(user_input, tool_result=tool_result):
            if chunk == "data: [DONE]\n\n":
                full_reply = "".join(accumulated)
                _handle_code_memory(user_input, full_reply, mem_type)

                if mode_status:
                    yield f"data: [STATUS] {mode_status}\n\n"
                yield chunk
                return

            if not chunk.startswith("data: ["):
                token = chunk[6:].rstrip("\n").replace("\\n", "\n")
                accumulated.append(token)

            yield chunk

    return Response(
        stream_with_context(generate()),
        mimetype="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


def _handle_code_memory(user_input: str, reply: str, mem_type: str | None) -> None:
    """Legacy code-save feature — saves extracted code blocks to disk."""
    if mem_type == "code":
        code = llm_core.extract_code(reply)
        if code:
            existing = len(os.listdir(CODE_MEMORY_DIR))
            filename = os.path.join(CODE_MEMORY_DIR, f"saved_{existing}.py")
            with open(filename, "w", encoding="utf-8") as f:
                f.write(code)



# Personality endpoint removed
# /greet route removed — no cold-start greeting


@bp.route("/history/clear", methods=["POST"])
def clear_history():
    llm_core.clear_history()
    return jsonify({"ok": True})


# ── Dashboard routes ───────────────────────────────────────────────────────────

from datetime import date as _date

@bp.route("/dashboard")
def dashboard():
    return render_template("dashboard.html")

@bp.route("/api/dashboard/state", methods=["GET"])
def dashboard_state():
    from app.data.db import get_tasks, get_goals, rollover_tasks
    today = _date.today().isoformat()
    rollover_tasks(today)
    return jsonify({"tasks": get_tasks(), "goals": get_goals()})

@bp.route("/api/dashboard/tasks", methods=["POST"])
def create_task():
    from app.data.db import add_task
    data = request.get_json(silent=True) or {}
    text = (data.get("text") or "").strip()
    date = (data.get("date") or _date.today().isoformat()).strip()
    if not text:
        return jsonify({"error": "text required"}), 400
    return jsonify(add_task(text, date)), 201

@bp.route("/api/dashboard/tasks/<int:task_id>", methods=["PATCH"])
def patch_task(task_id):
    from app.data.db import update_task
    data = request.get_json(silent=True) or {}
    result = update_task(task_id, **data)
    if not result:
        return jsonify({"error": "not found"}), 404
    return jsonify(result)

@bp.route("/api/dashboard/tasks/<int:task_id>", methods=["DELETE"])
def remove_task(task_id):
    from app.data.db import delete_task
    if delete_task(task_id):
        return jsonify({"ok": True})
    return jsonify({"error": "not found"}), 404

@bp.route("/api/dashboard/goals", methods=["POST"])
def create_goal():
    from app.data.db import add_goal
    data = request.get_json(silent=True) or {}
    text = (data.get("text") or "").strip()
    if not text:
        return jsonify({"error": "text required"}), 400
    return jsonify(add_goal(text)), 201

@bp.route("/api/dashboard/goals/<int:goal_id>", methods=["DELETE"])
def remove_goal(goal_id):
    from app.data.db import delete_goal
    if delete_goal(goal_id):
        return jsonify({"ok": True})
    return jsonify({"error": "not found"}), 404


@bp.route("/session", methods=["GET"])
def get_session():
    """Returns the current session ID."""
    from app.data.db import get_recent_messages
    session_id = llm_core.get_session_id()
    return jsonify({"session_id": session_id})


@bp.route("/session/end", methods=["POST", "GET"])
def end_session():
    """Ends the current session (summarise + archive) when the app/page closes."""
    llm_core.clear_history()
    return jsonify({"ok": True})


@bp.route("/messages", methods=["GET"])
def get_messages():
    """Returns all messages from the current session."""
    from app.data.db import get_recent_messages
    session_id = llm_core.get_session_id()
    # Get all messages (use a high limit)
    messages = get_recent_messages(session_id, limit=200)
    return jsonify({"messages": messages})


# ── Screen Assist ──────────────────────────────────────────────────────────────

@bp.route("/screen-assist")
def screen_assist():
    return render_template("screen_assist.html")


@bp.route("/api/screen/analyze", methods=["POST"])
def screen_analyze():
    """
    Accepts: { image_b64: <str>, question: <str>, history: [...], image_summary: <str> }

    First turn  — image_b64 is set, image_summary is empty.
                  Vision model analyses the screen. A [SUMMARY] event is emitted
                  after streaming so the frontend stores it for the session.

    Follow-up   — image_b64 is empty, image_summary carries the stored description.
                  It is injected into the system prompt so the model retains full
                  screen context without the raw image being resent every turn.

    Session end — frontend clears image_summary on clearSession() so it is never
                  reused across separate screenshots.
    """
    import json as _json
    from app.config import OLLAMA_URL, VISION_MODEL

    data          = request.get_json(silent=True) or {}
    image_b64     = data.get("image_b64", "")
    question      = (data.get("question") or "Explain what's on screen.").strip()
    history       = data.get("history", [])
    image_summary = (data.get("image_summary") or "").strip()

    is_first_turn = bool(image_b64)

    if not is_first_turn and not image_summary:
        return jsonify({"error": "No image or image summary provided"}), 400

    # /search detection — executed inside generate() so SSE opens immediately
    from app.searcher import is_search_command, extract_query, search as run_search
    _is_search    = is_search_command(question)
    _search_query = extract_query(question) if _is_search else None

    # Build system prompt — inject summary on follow-up turns instead of the image
    summary_block = ""
    if image_summary and not is_first_turn:
        summary_block = (
            f"\n\nSCREEN CONTEXT (from the start of this session):\n{image_summary}\n\n"
            "The user is asking a follow-up about that same screen. "
            "Use the context above as your reference — no new image is being sent."
        )

    system_msg = {
        "role": "system",
        "content": (
            "You are a sharp, knowledgeable teacher helping a student understand what's on their screen. "
            "Your job is NOT to repeat or summarise the text — the student can read that themselves. "
            "Your job is to EXPLAIN it: what it actually means, why it matters, how it connects to the bigger picture.\n\n"
            "When explaining content from a screen:\n"
            "- Lead with the core idea in plain language, as if explaining to someone who's never seen this before\n"
            "- Give real-world context or analogies that make the concept click\n"
            "- Point out what's non-obvious or commonly misunderstood\n"
            "- Use a concrete example if it helps — something the student can picture\n"
            "- If there are multiple concepts, explain how they relate to each other\n"
            "- End with the 'so what' — why does this matter, or when would you actually use/see this\n\n"
            "What to avoid:\n"
            "- Do NOT copy or paraphrase sentences from the screen\n"
            "- Do NOT just list the bullet points back with slightly different words\n"
            "- Do NOT over-structure with headers for short explanations — just talk\n\n"
            "Tone: like a smart friend who happens to know this subject well. Direct, clear, occasionally a real example or analogy. "
            "Not formal, not robotic."
            + summary_block
        ),
    }

    prior = [{"role": m["role"], "content": m["content"]} for m in history]

    def generate():
        nonlocal question

        # Search runs here — SSE connection is already open before DDG fires
        if _is_search:
            yield f"data: [STATUS] \U0001f50d Searching: {_search_query}\n\n"
            try:
                search_context = run_search(_search_query)
            except Exception as e:
                search_context = f"Search failed: {e}"
            question = (
                f"The user searched for: '{_search_query}'. "
                f"Here are the web results:\n\n{search_context}\n\n"
                f"Using both the screenshot and these search results, give a thorough explanation. "
                f"Connect what's on screen to what the search found."
            )

        # First turn sends the raw image; follow-ups are text-only
        if is_first_turn:
            current_msg = {"role": "user", "content": question, "images": [image_b64]}
        else:
            current_msg = {"role": "user", "content": question}

        messages = [system_msg] + prior + [current_msg]
        full_reply: list[str] = []

        try:
            import requests as _req
            with _req.post(
                OLLAMA_URL,
                json={"model": VISION_MODEL, "messages": messages, "stream": True},
                stream=True,
                timeout=120,
            ) as resp:
                resp.raise_for_status()
                for raw_line in resp.iter_lines():
                    if not raw_line:
                        continue
                    try:
                        chunk = _json.loads(raw_line)
                    except _json.JSONDecodeError:
                        continue
                    token = chunk.get("message", {}).get("content", "")
                    if token:
                        full_reply.append(token)
                        safe = token.replace("\n", "\\n")
                        yield f"data: {safe}\n\n"
                    if chunk.get("done", False):
                        break
        except Exception as exc:
            yield f"data: [ERROR] {exc}\n\n"
            yield "data: [DONE]\n\n"
            return

        # After first turn, emit the full reply as [SUMMARY] so the frontend
        # can store it and inject it on every subsequent turn without the image.
        if is_first_turn:
            summary_text = "".join(full_reply).replace("\n", "\\n")
            yield f"data: [SUMMARY] {summary_text}\n\n"

        yield "data: [DONE]\n\n"

    return Response(
        stream_with_context(generate()),
        mimetype="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


# ── Docs (Notepad) ─────────────────────────────────────────────────────────────

@bp.route("/docs")
def docs_page():
    return render_template("docs.html")


@bp.route("/api/docs", methods=["GET"])
def api_get_docs():
    from app.data.db import get_all_docs
    return jsonify(get_all_docs())


@bp.route("/api/docs", methods=["POST"])
def api_create_doc():
    from app.data.db import create_doc
    data  = request.get_json(silent=True) or {}
    title = data.get("title", "Untitled").strip() or "Untitled"
    return jsonify(create_doc(title)), 201


@bp.route("/api/docs/<int:doc_id>", methods=["GET"])
def api_get_doc(doc_id):
    from app.data.db import get_doc
    doc = get_doc(doc_id)
    if not doc:
        return jsonify({"error": "Not found"}), 404
    return jsonify(doc)


@bp.route("/api/docs/<int:doc_id>", methods=["PATCH"])
def api_update_doc(doc_id):
    from app.data.db import update_doc
    data    = request.get_json(silent=True) or {}
    title   = data.get("title")
    content = data.get("content")
    doc = update_doc(doc_id, title=title, content=content)
    if not doc:
        return jsonify({"error": "Not found"}), 404
    return jsonify(doc)


@bp.route("/api/docs/<int:doc_id>", methods=["DELETE"])
def api_delete_doc(doc_id):
    from app.data.db import delete_doc
    if delete_doc(doc_id):
        return jsonify({"ok": True})
    return jsonify({"error": "Not found"}), 404
