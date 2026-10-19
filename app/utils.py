from __future__ import annotations
import base64, zlib, json, time
from datetime import datetime
from functools import wraps
from flask import request, current_app, abort
import hmac

def now_iso() -> str:
    return datetime.utcnow().isoformat() + "Z"

def client_ip() -> str:
    if current_app.config.get("TRUST_PROXY"):
        for h in ("X-Forwarded-For", "CF-Connecting-IP"):
            if h in request.headers:
                return request.headers[h].split(",")[0].strip()
    return request.remote_addr or ""

def compress_dom(dom: str, limit: int = 200000) -> str:
    try:
        b = dom.encode("utf-8") if isinstance(dom, str) else b""
        if len(b) > limit:
            b = b[:limit]
        return base64.b64encode(zlib.compress(b, 6)).decode("ascii")
    except Exception:
        return ""

def decompress_dom(enc: str) -> str:
    try:
        return zlib.decompress(base64.b64decode(enc)).decode("utf-8", errors="ignore")
    except Exception:
        return ""

def pretty_json(s: str) -> str:
    try:
        return json.dumps(json.loads(s or "{}"), ensure_ascii=False, indent=2)
    except Exception:
        return s or ""


# --- HTTP Basic Auth for admin endpoints ---
def _check_basic_auth(username: str, password: str) -> bool:
    """Compare username/password against config using constant-time comparison."""
    expected_user = current_app.config.get("ADMIN_USER", "admin")
    expected_pass = current_app.config["ADMIN_PASSWORD"]
    return hmac.compare_digest(username.encode(), expected_user.encode()) and hmac.compare_digest(
        password.encode(), expected_pass.encode()
    )


def require_basic_auth(f):
    """Decorator enforcing HTTP Basic Auth. Sends 401 with WWW-Authenticate header."""
    @wraps(f)
    def wrapper(*args, **kwargs):
        auth = request.authorization
        if not auth or not _check_basic_auth(auth.username or "", auth.password or ""):
            return (
                {"ok": False, "error": "unauthorized"},
                401,
                {"WWW-Authenticate": 'Basic realm="blindxss-lite admin"'},
            )
        return f(*args, **kwargs)
    return wrapper

from urllib.parse import urlparse

def require_same_origin() -> None:
    """403 unless the request's Origin/Referer matches the app's own host."""
    expected = request.host
    for hdr in ("Origin", "Referer"):
        val = request.headers.get(hdr)
        if val:
            if urlparse(val).netloc == expected:
                return
            abort(403)
    abort(403)  # no Origin and no Referer: not a browser form post

# --- SQLite-backed sliding-window rate limiter (shared across gunicorn workers) ---
def is_rate_limited(key: str) -> bool:
    """Return True if `key` exceeded RATE_LIMIT_COUNT requests in RATE_LIMIT_WINDOW seconds."""
    from .db import get_db

    limit = int(current_app.config.get("RATE_LIMIT_COUNT", 60))
    window = float(current_app.config.get("RATE_LIMIT_WINDOW", 60))
    now = time.time()
    db = get_db()

    # drop timestamps outside the window for this key
    db.execute("DELETE FROM rate_limit WHERE key=? AND ts <= ?", (key, now - window))
    count = db.execute("SELECT COUNT(*) FROM rate_limit WHERE key=?", (key,)).fetchone()[0]
    if count >= limit:
        db.commit()
        return True

    db.execute("INSERT INTO rate_limit(key, ts) VALUES(?, ?)", (key, now))
    db.commit()
    return False
