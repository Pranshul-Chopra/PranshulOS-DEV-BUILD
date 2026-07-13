# ── notifier.py ───────────────────────────────────────────────────────────────
# Watches pending tasks and fires Windows toast notifications at 11 PM.
# Runs entirely in a daemon thread — never blocks the main app.
#
# Schedule:
#   23:00 — main reminder: lists all incomplete tasks for today
#   23:30 — final nudge if tasks still undone (softer tone)
#
# Uses `plyer` for native Windows notifications (same API as outlook toasts).

import threading
import time
import sys
import os
from datetime import datetime, date

# ── Notification sender ────────────────────────────────────────────────────────

def _notify(title: str, message: str, timeout: int = 8) -> None:
    """Fire a Windows native toast notification via plyer."""
    try:
        from plyer import notification
        notification.notify(
            title=title,
            message=message,
            app_name="FLUIDCB",
            timeout=timeout,
        )
    except ImportError:
        print(f"[notifier] plyer not installed — install with: pip install plyer")
        print(f"[notifier] would have shown: {title} — {message}")
    except Exception as e:
        print(f"[notifier] notification error: {e}")


# ── Task fetcher ───────────────────────────────────────────────────────────────

def _get_pending_tasks() -> list[str]:
    """Returns text of all incomplete tasks for today."""
    try:
        # Import here to avoid circular imports at module load time
        sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
        from app.data.db import get_tasks
        today = date.today().isoformat()
        tasks = get_tasks()
        pending = [
            t["text"] for t in tasks
            if not t.get("done") and t.get("date", today) <= today
        ]
        return pending
    except Exception as e:
        print(f"[notifier] error fetching tasks: {e}")
        return []


# ── Notification logic ─────────────────────────────────────────────────────────

def _build_message(tasks: list[str]) -> str:
    """Formats pending tasks into a compact notification message."""
    if not tasks:
        return ""
    if len(tasks) == 1:
        return f"Still open: {tasks[0]}"
    if len(tasks) <= 3:
        lines = "\n".join(f"• {t}" for t in tasks)
        return lines
    # More than 3 — show first 3 and a count
    lines = "\n".join(f"• {t}" for t in tasks[:3])
    return f"{lines}\n…and {len(tasks) - 3} more"


def _fire_main_reminder() -> None:
    pending = _get_pending_tasks()
    if not pending:
        return  # all done — no notification needed
    count = len(pending)
    title = f"🔔 {count} task{'s' if count > 1 else ''} still pending"
    message = _build_message(pending)
    _notify(title, message, timeout=10)
    print(f"[notifier] 11 PM reminder fired — {count} pending task(s)")


def _fire_final_nudge() -> None:
    pending = _get_pending_tasks()
    if not pending:
        return
    count = len(pending)
    title = f"⏰ Last call — {count} task{'s' if count > 1 else ''} unfinished"
    message = _build_message(pending)
    _notify(title, message, timeout=10)
    print(f"[notifier] 11:30 PM nudge fired — {count} pending task(s)")


# ── Scheduler loop ─────────────────────────────────────────────────────────────

def _scheduler_loop() -> None:
    """
    Sleeps until the next scheduled time, fires notification, then loops.
    Checks every 30 seconds to avoid missing the window on slow systems.
    """
    fired_today: dict[str, bool] = {}  # {"2025-06-24_2300": True, ...}

    print("[notifier] scheduler started — watching for 23:00 and 23:30 daily")

    while True:
        try:
            now   = datetime.now()
            today = now.date().isoformat()
            hhmm  = now.hour * 100 + now.minute  # e.g. 2305

            key_main  = f"{today}_2300"
            key_nudge = f"{today}_2330"

            # Main reminder window: 23:00 – 23:04
            if 2300 <= hhmm <= 2304 and not fired_today.get(key_main):
                fired_today[key_main] = True
                _fire_main_reminder()

            # Final nudge window: 23:30 – 23:34
            if 2330 <= hhmm <= 2334 and not fired_today.get(key_nudge):
                fired_today[key_nudge] = True
                _fire_final_nudge()

            # Clean up yesterday's keys to avoid unbounded growth
            for key in list(fired_today.keys()):
                if not key.startswith(today):
                    del fired_today[key]

        except Exception as e:
            print(f"[notifier] scheduler error: {e}")

        time.sleep(30)  # check every 30 seconds


# ── Public API ─────────────────────────────────────────────────────────────────

def start() -> None:
    """Starts the notification scheduler in a background daemon thread."""
    t = threading.Thread(target=_scheduler_loop, daemon=True, name="task-notifier")
    t.start()


def test_notification() -> None:
    """Fires a test notification immediately — useful for verifying plyer works."""
    _notify(
        "FLUIDCB — Test Notification",
        "Notifications are working! You'll get task reminders at 11 PM.",
        timeout=6,
    )
