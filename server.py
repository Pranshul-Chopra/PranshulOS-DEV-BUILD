"""
server.py — boots the FluidCB Flask app on localhost:5000.
Called in a background thread by main.py.
"""
import sys
import os

FLUIDCB_PATH = os.path.join(os.path.dirname(__file__), "fluidcb_v2")
if FLUIDCB_PATH not in sys.path:
    sys.path.insert(0, FLUIDCB_PATH)

FLASK_PORT = 5000

def start_flask():
    from app import create_app
    flask_app = create_app()
    flask_app.run(
        host="127.0.0.1",
        port=FLASK_PORT,
        debug=False,
        use_reloader=False,   # MUST be False inside a thread
    )
