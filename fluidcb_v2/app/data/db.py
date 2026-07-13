# ── data/db.py ────────────────────────────────────────────────────────────────
# Raw database access only. No business logic here.
# All tunable values come from config/settings.py.

import sqlite3
import json
import threading
from queue import Queue
from datetime import datetime, timedelta
from pathlib import Path
from config.settings import (
    TIER_NORMAL_TTL_DAYS,
    TIER_NOT_WORTH_TTL_DAYS,
    STABILITY_INIT,
    FORGETTING_ARCHIVE_THRESHOLD,
    FORGETTING_ARCHIVE_DAYS,
)

DB_PATH = Path(__file__).parent / "fluidcb.db"

# ── Connection Pool ────────────────────────────────────────────────────────────
# Reuse database connections to reduce overhead
class _ConnectionPool:
    def __init__(self, size: int = 3):
        self._pool: Queue = Queue(maxsize=size)
        self._lock = threading.Lock()
        self._size = size
        # Pre-create connections
        for _ in range(size):
            self._pool.put(self._create_connection())
    
    def _create_connection(self) -> sqlite3.Connection:
        con = sqlite3.connect(str(DB_PATH), check_same_thread=False, timeout=5.0)
        con.row_factory = sqlite3.Row
        con.execute("PRAGMA journal_mode=WAL")
        con.execute("PRAGMA foreign_keys=ON")
        return con
    
    def get(self) -> sqlite3.Connection:
        """Get a connection from the pool (blocks if none available)."""
        return self._pool.get(timeout=5.0)
    
    def put(self, conn: sqlite3.Connection) -> None:
        """Return a connection to the pool."""
        try:
            self._pool.put(conn, block=False)
        except:
            # If pool is full, close the connection
            try:
                conn.close()
            except:
                pass

# Global connection pool
_pool = _ConnectionPool(size=3)


# ── connection ─────────────────────────────────────────────────────────────────

class _ConnectionContext:
    """Context manager for connection pooling."""
    def __init__(self, pool: _ConnectionPool):
        self.pool = pool
        self.conn = None
    
    def __enter__(self):
        self.conn = self.pool.get()
        return self.conn
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.conn:
            if exc_type:
                # Error occurred — rollback changes
                try:
                    self.conn.rollback()
                except:
                    pass
            else:
                # Success — commit changes
                try:
                    self.conn.commit()
                except:
                    pass
            self.pool.put(self.conn)

def _conn() -> _ConnectionContext:
    """Get a pooled database connection."""
    return _ConnectionContext(_pool)


# ── schema ─────────────────────────────────────────────────────────────────────

def init_db() -> None:
    with _conn() as con:
        con.executescript("""
            CREATE TABLE IF NOT EXISTS sessions (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                started_at  DATETIME DEFAULT CURRENT_TIMESTAMP,
                ended_at    DATETIME,
                summary     TEXT
            );

            CREATE TABLE IF NOT EXISTS messages (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id  INTEGER NOT NULL REFERENCES sessions(id),
                role        TEXT    NOT NULL,
                content     TEXT    NOT NULL,
                timestamp   DATETIME DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS memory (
                id            INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id    INTEGER NOT NULL REFERENCES sessions(id),
                tier          TEXT    NOT NULL CHECK(tier IN ('normal','not_worth')),
                confidence    REAL    NOT NULL DEFAULT 0.5,
                permanent     INTEGER NOT NULL DEFAULT 0,
                raw_extract   TEXT    NOT NULL,
                summary       TEXT,
                emotion       TEXT,
                stability     REAL    NOT NULL DEFAULT 1.0,
                last_accessed DATETIME DEFAULT CURRENT_TIMESTAMP,
                created_at    DATETIME DEFAULT CURRENT_TIMESTAMP,
                expires_at    DATETIME,
                superseded_by INTEGER REFERENCES memory(id),
                archived      INTEGER NOT NULL DEFAULT 0
            );

            CREATE INDEX IF NOT EXISTS idx_messages_session
                ON messages(session_id);
            CREATE INDEX IF NOT EXISTS idx_memory_session
                ON memory(session_id);
            CREATE INDEX IF NOT EXISTS idx_memory_permanent
                ON memory(permanent);
            CREATE INDEX IF NOT EXISTS idx_memory_archived
                ON memory(archived);
        """)


# ── sessions ───────────────────────────────────────────────────────────────────

def create_session() -> int:
    with _conn() as con:
        cur = con.execute("INSERT INTO sessions DEFAULT VALUES")
        return cur.lastrowid

def get_or_resume_session() -> int:
    """Returns the most recent session if it's still active (no ended_at), else creates a new one."""
    with _conn() as con:
        row = con.execute(
            "SELECT id FROM sessions WHERE ended_at IS NULL ORDER BY id DESC LIMIT 1"
        ).fetchone()
    if row:
        return row[0]
    return create_session()

def end_session(session_id: int, summary: str) -> None:
    with _conn() as con:
        con.execute(
            "UPDATE sessions SET ended_at = CURRENT_TIMESTAMP, summary = ? WHERE id = ?",
            (summary, session_id)
        )

def get_recent_session_summaries(n: int) -> list[dict]:
    with _conn() as con:
        rows = con.execute(
            """SELECT id, started_at, summary FROM sessions
               WHERE summary IS NOT NULL
               ORDER BY id DESC LIMIT ?""",
            (n,)
        ).fetchall()
    return [dict(r) for r in reversed(rows)]


# ── messages ───────────────────────────────────────────────────────────────────

def save_message(session_id: int, role: str, content: str) -> None:
    with _conn() as con:
        con.execute(
            "INSERT INTO messages (session_id, role, content) VALUES (?, ?, ?)",
            (session_id, role, content)
        )

def get_recent_messages(session_id: int, limit: int = 10) -> list[dict]:
    with _conn() as con:
        rows = con.execute(
            """SELECT role, content FROM messages
               WHERE session_id = ?
               ORDER BY id DESC LIMIT ?""",
            (session_id, limit)
        ).fetchall()
    return [dict(r) for r in reversed(rows)]

def get_raw_session_messages(session_id: int, limit: int = 20) -> list[dict]:
    """Full raw messages from a specific past session — used for depth retrieval."""
    with _conn() as con:
        rows = con.execute(
            """SELECT role, content, timestamp FROM messages
               WHERE session_id = ?
               ORDER BY id DESC LIMIT ?""",
            (session_id, limit)
        ).fetchall()
    return [dict(r) for r in reversed(rows)]


# ── memory CRUD ────────────────────────────────────────────────────────────────

def insert_memory(
    session_id:  int,
    tier:        str,
    confidence:  float,
    raw_extract: str,
    summary:     str | None,
    emotion:     dict | None,
    stability:   float = STABILITY_INIT,
) -> int:
    now = datetime.utcnow()
    if tier == "normal":
        expires_at = now + timedelta(days=TIER_NORMAL_TTL_DAYS)
    else:
        expires_at = now + timedelta(days=TIER_NOT_WORTH_TTL_DAYS)

    with _conn() as con:
        cur = con.execute(
            """INSERT INTO memory
               (session_id, tier, confidence, raw_extract, summary,
                emotion, stability, expires_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                session_id, tier, confidence, raw_extract, summary,
                json.dumps(emotion) if emotion else None,
                stability,
                expires_at.isoformat(),
            )
        )
        return cur.lastrowid

def get_all_active_memories() -> list[dict]:
    """All non-archived memories for similarity scanning."""
    with _conn() as con:
        rows = con.execute(
            "SELECT * FROM memory WHERE archived = 0"
        ).fetchall()
    return [_parse_memory(dict(r)) for r in rows]

def get_permanent_memories() -> list[dict]:
    with _conn() as con:
        rows = con.execute(
            "SELECT * FROM memory WHERE permanent = 1 AND archived = 0"
        ).fetchall()
    return [_parse_memory(dict(r)) for r in rows]

def reinforce_memory(memory_id: int, new_stability: float) -> None:
    with _conn() as con:
        con.execute(
            """UPDATE memory
               SET stability = ?, last_accessed = CURRENT_TIMESTAMP
               WHERE id = ?""",
            (new_stability, memory_id)
        )

def promote_memory(memory_id: int, new_tier: str, new_confidence: float) -> None:
    now = datetime.utcnow()
    if new_tier == "normal":
        expires_at = now + timedelta(days=TIER_NORMAL_TTL_DAYS)
    else:
        expires_at = now + timedelta(days=TIER_NOT_WORTH_TTL_DAYS)
    with _conn() as con:
        con.execute(
            """UPDATE memory
               SET tier = ?, confidence = ?, expires_at = ?
               WHERE id = ?""",
            (new_tier, new_confidence, expires_at.isoformat(), memory_id)
        )

def mark_permanent(memory_id: int) -> None:
    with _conn() as con:
        con.execute(
            "UPDATE memory SET permanent = 1, expires_at = NULL WHERE id = ?",
            (memory_id,)
        )

def supersede_memory(old_id: int, new_id: int) -> None:
    with _conn() as con:
        con.execute(
            "UPDATE memory SET superseded_by = ? WHERE id = ?",
            (new_id, old_id)
        )

def get_contradiction_chain(memory_id: int) -> list[dict]:
    """Walk the superseded_by chain from oldest to newest."""
    with _conn() as con:
        # Fetch the target memory
        current = con.execute(
            "SELECT * FROM memory WHERE id = ?", (memory_id,)
        ).fetchone()
        if not current:
            return []
        chain = [_parse_memory(dict(current))]

        # Find the immediate predecessor using a targeted query — not a full table scan
        predecessor = con.execute(
            "SELECT * FROM memory WHERE superseded_by = ? AND archived = 0 LIMIT 1",
            (memory_id,)
        ).fetchone()
        if predecessor:
            chain.insert(0, _parse_memory(dict(predecessor)))

    return chain

def archive_stale_memories() -> int:
    """
    Archive memories where retrievability R < threshold for 30+ days.
    R = e^(-t/S), t in days since last_accessed.
    Returns count of archived rows.
    """
    import math
    now = datetime.utcnow()
    with _conn() as con:
        rows = con.execute(
            "SELECT id, stability, last_accessed FROM memory WHERE permanent = 0 AND archived = 0"
        ).fetchall()
        archive_ids = []
        for row in rows:
            last = datetime.fromisoformat(row["last_accessed"])
            t = (now - last).days
            s = row["stability"]
            R = math.exp(-t / max(s, 0.1))
            if R < FORGETTING_ARCHIVE_THRESHOLD and t >= FORGETTING_ARCHIVE_DAYS:
                archive_ids.append(row["id"])
        if archive_ids:
            con.execute(
                f"UPDATE memory SET archived = 1 WHERE id IN ({','.join('?'*len(archive_ids))})",
                archive_ids
            )
    return len(archive_ids)

def touch_memory(memory_id: int) -> None:
    """Update last_accessed when a memory is retrieved."""
    with _conn() as con:
        con.execute(
            "UPDATE memory SET last_accessed = CURRENT_TIMESTAMP WHERE id = ?",
            (memory_id,)
        )


# ── helpers ────────────────────────────────────────────────────────────────────

def _parse_memory(row: dict) -> dict:
    if row.get("emotion") and isinstance(row["emotion"], str):
        try:
            row["emotion"] = json.loads(row["emotion"])
        except (json.JSONDecodeError, TypeError):
            row["emotion"] = None
    return row


# ── dashboard ──────────────────────────────────────────────────────────────────

def init_dashboard_tables() -> None:
    with _conn() as con:
        con.executescript("""
            CREATE TABLE IF NOT EXISTS dashboard_tasks (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                text        TEXT    NOT NULL,
                date        TEXT    NOT NULL,
                done        INTEGER NOT NULL DEFAULT 0,
                done_date   TEXT,
                stacked     INTEGER NOT NULL DEFAULT 0,
                created_at  DATETIME DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS dashboard_goals (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                text        TEXT    NOT NULL,
                created_at  DATETIME DEFAULT CURRENT_TIMESTAMP
            );

            CREATE INDEX IF NOT EXISTS idx_tasks_date
                ON dashboard_tasks(date);

            CREATE TABLE IF NOT EXISTS docs (
                id         INTEGER PRIMARY KEY AUTOINCREMENT,
                title      TEXT    NOT NULL DEFAULT 'Untitled',
                content    TEXT    NOT NULL DEFAULT '',
                created_at TEXT    NOT NULL DEFAULT (datetime('now')),
                updated_at TEXT    NOT NULL DEFAULT (datetime('now'))
            );
        """)


def get_tasks() -> list[dict]:
    with _conn() as con:
        rows = con.execute(
            "SELECT * FROM dashboard_tasks ORDER BY created_at ASC"
        ).fetchall()
    return [dict(r) for r in rows]


def add_task(text: str, date: str) -> dict:
    with _conn() as con:
        cur = con.execute(
            "INSERT INTO dashboard_tasks (text, date) VALUES (?, ?)",
            (text, date)
        )
        row = con.execute(
            "SELECT * FROM dashboard_tasks WHERE id = ?", (cur.lastrowid,)
        ).fetchone()
    return dict(row)


def update_task(task_id: int, **fields) -> dict | None:
    allowed = {"done", "done_date", "stacked", "text"}
    updates = {k: v for k, v in fields.items() if k in allowed}
    if not updates:
        return None
    set_clause = ", ".join(f"{k} = ?" for k in updates)
    values = list(updates.values()) + [task_id]
    with _conn() as con:
        con.execute(
            f"UPDATE dashboard_tasks SET {set_clause} WHERE id = ?", values
        )
        row = con.execute(
            "SELECT * FROM dashboard_tasks WHERE id = ?", (task_id,)
        ).fetchone()
    return dict(row) if row else None


def delete_task(task_id: int) -> bool:
    with _conn() as con:
        cur = con.execute(
            "DELETE FROM dashboard_tasks WHERE id = ?", (task_id,)
        )
    return cur.rowcount > 0


def rollover_tasks(today: str) -> None:
    """Remove done tasks from previous days; mark old pending tasks as stacked."""
    with _conn() as con:
        con.execute(
            "DELETE FROM dashboard_tasks WHERE done = 1 AND done_date != ?",
            (today,)
        )
        con.execute(
            """UPDATE dashboard_tasks
               SET stacked = 1
               WHERE done = 0 AND stacked = 0 AND date < ?""",
            (today,)
        )


def get_goals() -> list[dict]:
    with _conn() as con:
        rows = con.execute(
            "SELECT * FROM dashboard_goals ORDER BY created_at ASC"
        ).fetchall()
    return [dict(r) for r in rows]


def add_goal(text: str) -> dict:
    with _conn() as con:
        cur = con.execute(
            "INSERT INTO dashboard_goals (text) VALUES (?)", (text,)
        )
        row = con.execute(
            "SELECT * FROM dashboard_goals WHERE id = ?", (cur.lastrowid,)
        ).fetchone()
    return dict(row)


def delete_goal(goal_id: int) -> bool:
    with _conn() as con:
        cur = con.execute(
            "DELETE FROM dashboard_goals WHERE id = ?", (goal_id,)
        )
    return cur.rowcount > 0


# ── Docs (Notepad) ─────────────────────────────────────────────────────────────

def get_all_docs() -> list[dict]:
    with _conn() as con:
        rows = con.execute(
            "SELECT id, title, created_at, updated_at FROM docs ORDER BY updated_at DESC"
        ).fetchall()
    return [dict(r) for r in rows]


def get_doc(doc_id: int) -> dict | None:
    with _conn() as con:
        row = con.execute(
            "SELECT * FROM docs WHERE id = ?", (doc_id,)
        ).fetchone()
    return dict(row) if row else None


def create_doc(title: str = "Untitled") -> dict:
    with _conn() as con:
        cur = con.execute(
            "INSERT INTO docs (title, content) VALUES (?, '')", (title,)
        )
        row = con.execute(
            "SELECT * FROM docs WHERE id = ?", (cur.lastrowid,)
        ).fetchone()
    return dict(row)


def update_doc(doc_id: int, title: str | None = None, content: str | None = None) -> dict | None:
    fields, vals = [], []
    if title is not None:
        fields.append("title = ?"); vals.append(title)
    if content is not None:
        fields.append("content = ?"); vals.append(content)
    if not fields:
        return get_doc(doc_id)
    fields.append("updated_at = datetime('now')")
    vals.append(doc_id)
    with _conn() as con:
        con.execute(
            f"UPDATE docs SET {', '.join(fields)} WHERE id = ?", vals
        )
        row = con.execute("SELECT * FROM docs WHERE id = ?", (doc_id,)).fetchone()
    return dict(row) if row else None


def delete_doc(doc_id: int) -> bool:
    with _conn() as con:
        cur = con.execute("DELETE FROM docs WHERE id = ?", (doc_id,))
    return cur.rowcount > 0
