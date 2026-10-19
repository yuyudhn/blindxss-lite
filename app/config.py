# app/config.py
from __future__ import annotations
import os
from pathlib import Path

def _load_dotenv(path: Path) -> None:
    """Load key=value pairs from a .env file into os.environ if not already set."""
    if not path.exists():
        return
    for line in path.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        os.environ.setdefault(key, value)

class Config:
    BASE_DIR = Path(__file__).resolve().parent
    DEFAULT_DB = (BASE_DIR / ".." / "bxss.db").resolve()
    # Load .env from project root if present (for non-Docker runs)
    _load_dotenv(BASE_DIR / ".." / ".env")
    # Basic Auth credentials for admin dashboard.
    ADMIN_USER = os.environ.get("ADMIN_USER", "admin")
    ADMIN_PASSWORD = os.environ.get("ADMIN_PASSWORD") or ""
    DB_PATH = str(Path(os.environ.get("DB_PATH", str(DEFAULT_DB))).resolve())
    MAX_BODY = int(os.environ.get("MAX_BODY", "524288"))
    RATE_LIMIT_COUNT = int(os.environ.get("RATE_LIMIT_COUNT", "60"))
    RATE_LIMIT_WINDOW = int(os.environ.get("RATE_LIMIT_WINDOW", "60"))
    PUBLIC_URL = os.environ.get("PUBLIC_URL", "")
    TRUST_PROXY = os.environ.get("TRUST_PROXY", "").lower() in ("1", "true", "yes")
