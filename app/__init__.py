from __future__ import annotations

import os
import logging
import sys
from datetime import datetime
from flask import Flask, jsonify, request, abort
from .config import Config
from . import db
from .collectors import bp as collectors_bp
from .events import bp as events_bp
from .payloads import bp as payloads_bp


def create_app() -> Flask:
    app = Flask(__name__, static_folder="static", template_folder="templates")
    app.config.from_object(Config)
    app.config["MAX_CONTENT_LENGTH"] = app.config["MAX_BODY"]
    db.init_app(app)
    logging.basicConfig(
        level=getattr(logging, os.getenv("LOG_LEVEL", "INFO").upper(), logging.INFO),
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
        stream=sys.stdout,
    )
    if not app.config.get("ADMIN_PASSWORD"):
        raise RuntimeError("ADMIN_PASSWORD environment variable is required")

    @app.after_request
    def add_cors(resp):
        origin = request.headers.get("Origin")
        req_hdrs = request.headers.get("Access-Control-Request-Headers", "")
        resp.headers["Access-Control-Allow-Origin"] = origin or "*"
        resp.headers["Access-Control-Allow-Methods"] = "GET,POST,OPTIONS"
        resp.headers["Access-Control-Allow-Headers"] = req_hdrs or "content-type"
        resp.headers["Vary"] = "Origin, Access-Control-Request-Headers"
        return resp

    @app.route("/", methods=["GET"])
    def index():
        abort(404)

    @app.route("/_healthz", methods=["GET"])
    def health():
        try:
            conn = db.get_db()
            conn.execute("SELECT 1").fetchone()
            db_ok = True
        except Exception:
            db_ok = False
        return jsonify(ok=True, db_ok=db_ok, now=datetime.utcnow().isoformat() + "Z")

    app.register_blueprint(collectors_bp)
    app.register_blueprint(events_bp)
    app.register_blueprint(payloads_bp)

    @app.errorhandler(401)
    def _unauth(e):
        return (
            "<h1>401 Unauthorized</h1>",
            401,
            {
                "Content-Type": "text/html; charset=utf-8",
                "WWW-Authenticate": 'Basic realm="blindxss-lite admin"',
            },
        )

    return app