# app/db.py
from __future__ import annotations
import sqlite3
from pathlib import Path
from flask import current_app, g, Flask

SCHEMA = """
CREATE TABLE IF NOT EXISTS events(
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    ts TEXT NOT NULL,
    ip TEXT,
    ua TEXT,
    url TEXT,
    origin TEXT,
    referrer TEXT,
    title TEXT,
    cookies TEXT,
    local_storage TEXT,
    session_storage TEXT,
    dom_snippet BLOB,
    raw_len INTEGER
);

CREATE TABLE IF NOT EXISTS settings(
    key TEXT PRIMARY KEY,
    value TEXT
);

CREATE TABLE IF NOT EXISTS rate_limit(
    key TEXT NOT NULL,
    ts REAL NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_rate_limit_key ON rate_limit(key);
"""

def get_db():
    if "db" not in g:
        db_path = Path(current_app.config.get("DB_PATH", "bxss.db"))
        g.db = sqlite3.connect(db_path)
        g.db.row_factory = sqlite3.Row
        g.db.execute("PRAGMA busy_timeout = 5000")
        g.db.execute("PRAGMA journal_mode = WAL").fetchone()
    return g.db

def init_db(app: Flask):
    db_path = Path(app.config.get("DB_PATH", "bxss.db"))
    db_path.parent.mkdir(parents=True, exist_ok=True)
    with app.app_context():
        db = get_db()
        db.executescript(SCHEMA)
        db.commit()

def get_setting(key: str) -> str:
    row = get_db().execute("SELECT value FROM settings WHERE key=?", (key,)).fetchone()
    return row["value"] if row else ""

def set_setting(key: str, value: str) -> None:
    db = get_db()
    db.execute(
        "INSERT INTO settings(key, value) VALUES(?, ?) "
        "ON CONFLICT(key) DO UPDATE SET value=excluded.value",
        (key, value),
    )
    db.commit()

def close_db(e=None):
    db = g.pop("db", None)
    if db is not None:
        db.close()

def init_app(app: Flask):
    app.teardown_appcontext(close_db)
    init_db(app)
