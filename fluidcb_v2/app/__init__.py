# ── app/__init__.py ───────────────────────────────────────────────────────────
# App factory. Import and create the app; don't instantiate at module level.

from flask import Flask


def create_app() -> Flask:
    app = Flask(__name__, template_folder="../templates")

    from app.data.db import init_db, init_dashboard_tables
    init_db()
    init_dashboard_tables()

    from app.routes import bp
    app.register_blueprint(bp)

    return app
