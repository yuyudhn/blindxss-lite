# app/events.py
from __future__ import annotations
from flask import Blueprint, render_template, request, abort, jsonify, current_app
from .db import get_db
from .utils import decompress_dom, pretty_json, require_basic_auth

bp = Blueprint("events", __name__)

def get_event_or_404(eid: int):
    """ambil 1 event by id atau 404"""
    with get_db() as db:
        row = db.execute(
            "SELECT id, ts, ip, ua, url, origin, referrer, title, cookies, "
            "local_storage, session_storage, dom_snippet, raw_len "
            "FROM events WHERE id=?",
            (eid,),
        ).fetchone()
        if not row:
            abort(404)
        return row

@bp.route("/events")
@require_basic_auth
def events():
    q = (
        "SELECT id, ts, ip, ua, url, referrer, title, cookies, raw_len "
        "FROM events ORDER BY id DESC LIMIT 500"
    )
    with get_db() as db:
        rows = db.execute(q).fetchall()
    return render_template("events.html", rows=rows)

@bp.route("/events/<int:eid>")
@require_basic_auth
def event_json(eid: int):
    row = get_event_or_404(eid)
    dom = decompress_dom(row["dom_snippet"]) if row["dom_snippet"] else ""
    data = {
        "id": row["id"],
        "ts": row["ts"],
        "ip": row["ip"],
        "ua": row["ua"] or "",
        "url": row["url"] or "",
        "origin": row["origin"] or "",
        "referrer": row["referrer"] or "",
        "title": row["title"] or "",
        "cookies": row["cookies"] or "",
        "local_storage": row["local_storage"] or "{}",
        "session_storage": row["session_storage"] or "{}",
        "raw_len": row["raw_len"] or 0,
        "dom": dom,
    }
    return jsonify(data)

@bp.route("/events/<int:eid>/view")
@require_basic_auth
def event_view(eid: int):
    row = get_event_or_404(eid)
    ev = {
        "id": row["id"],
        "ts": row["ts"],
        "ip": row["ip"],
        "ua": row["ua"] or "",
        "url": row["url"] or "",
        "origin": row["origin"] or "",
        "referrer": row["referrer"] or "",
        "title": row["title"] or "",
        "cookies": row["cookies"] or "",
        "local_storage": row["local_storage"] or "{}",
        "session_storage": row["session_storage"] or "{}",
        "raw_len": row["raw_len"] or 0,
        "dom": decompress_dom(row["dom_snippet"]) if row["dom_snippet"] else "",
    }

    events_url  = f"{request.url_root.rstrip('/')}/events"
    json_url    = f"{request.url_root.rstrip('/')}/events/{ev['id']}"
    payload_url = f"{request.url_root.rstrip('/')}/payloads"

    ev["local_storage_pretty"]   = pretty_json(ev["local_storage"])
    ev["session_storage_pretty"] = pretty_json(ev["session_storage"])

    return render_template(
        "event.html",
        ev=ev,
        events_url=events_url,
        json_url=json_url,
        payload_url=payload_url,
    )