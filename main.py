"""
PranshulOS — entry point.
Starts FluidCB Flask server in a background thread, then launches pywebview.
"""
import threading
import time
import sys
import os

FLUIDCB_PATH = os.path.join(os.path.dirname(__file__), "fluidcb_v2")
if FLUIDCB_PATH not in sys.path:
    sys.path.insert(0, FLUIDCB_PATH)

from server import start_flask
from shell import launch

if __name__ == "__main__":
    flask_thread = threading.Thread(target=start_flask, daemon=True)
    flask_thread.start()

    # Wait for Flask to actually bind before opening the window.
    # Polling beats a blind sleep — typical bind is ~100ms, not 1500ms.
    import urllib.request, urllib.error
    for _ in range(60):          # up to 3 seconds (60 × 50ms)
        try:
            urllib.request.urlopen("http://127.0.0.1:5000/home")
            break
        except urllib.error.URLError:
            time.sleep(0.05)

    # Start task notification scheduler (11 PM reminders)
    from app.notifier import start as start_notifier
    start_notifier()

    launch()
