from __future__ import annotations
import base64, zlib, json, time
from collections import defaultdict, deque
from datetime import datetime
from functools import wraps
from flask import request, current_app, abort
import hmac

def now_iso() -> str:
    return datetime.utcnow().isoformat() + "Z"

def client_ip() -> str:
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
    expected_pass = current_app.config.get("ADMIN_PASSWORD", "changeme")
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

# --- simple in-memory sliding-window rate limiter ---
_rate_buckets = defaultdict(deque)

def is_rate_limited(key: str) -> bool:
    """Return True if `key` exceeded RATE_LIMIT_COUNT requests in RATE_LIMIT_WINDOW seconds."""
    limit = int(current_app.config.get("RATE_LIMIT_COUNT", 60))
    window = float(current_app.config.get("RATE_LIMIT_WINDOW", 60))
    now = time.time()
    bucket = _rate_buckets[key]

    # prune expired timestamps
    while bucket and now - bucket[0] > window:
        bucket.popleft()

    if len(bucket) >= limit:
        return True

    bucket.append(now)
    return False
