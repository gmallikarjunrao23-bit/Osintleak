"""Search blueprint — core engine."""
from __future__ import annotations

import json
import base64
import csv
import io
from datetime import datetime, timezone

from flask import (
    Blueprint, render_template, request, jsonify,
    current_app, flash, redirect, url_for,
    make_response, abort,
)
from flask_login import login_required, current_user

from app.extensions import db, cache, limiter
from app.models import SearchLog
from app.services.osint import search as osint_search, detect_query_type

search_bp = Blueprint("search", __name__)


def _check_limit() -> bool:
    """Check and decrement daily search limit. Returns True if allowed."""
    current_user.reset_daily_if_needed()
    cfg = current_app.config["TIER_LIMITS"]
    limit = cfg.get(current_user.tier, {}).get("searches_day", 3)
    return current_user.searches_today < limit


def _record_search(result: dict) -> None:
    current_user.searches_today += 1
    current_user.total_searches += 1

    log = SearchLog(
        user_id=current_user.id,
        query=result["query"],
        query_type=result["query_type"],
        result_count=result["total_records"],
        response_time=result["response_time"],
        api_status="ok" if result["ok"] else "error",
        error_message=result.get("error"),
        ip_address=request.remote_addr,
        user_agent=request.user_agent.string[:512],
    )
    db.session.add(log)
    db.session.commit()


@search_bp.route("/search", methods=["GET", "POST"])
@login_required
@limiter.limit("10 per minute")
def index():
    result = None
    query = ""

    if request.method == "POST":
        query = request.form.get("query", "").strip()
        if not query:
            flash("Please enter a search query.", "warning")
            return render_template("dashboard/search.html", result=None, query=query)

        if not _check_limit():
            flash(
                f"Daily search limit reached for your {current_user.tier} plan. "
                "Upgrade to search more.",
                "danger",
            )
            return redirect(url_for("billing.index"))

        cache_key = f"search:{current_user.id}:{query.lower()}"
        result = cache.get(cache_key)

        if result is None:
            result = osint_search(query)
            if result["ok"]:
                cache.set(cache_key, result, timeout=3600)

        _record_search(result)

    return render_template("dashboard/search.html", result=result, query=query)


@search_bp.route("/search/export/<fmt>", methods=["POST"])
@login_required
def export(fmt: str):
    cfg = current_app.config["TIER_LIMITS"]
    if not cfg.get(current_user.tier, {}).get("export", False):
        abort(403)

    raw = request.form.get("result_json", "")
    try:
        result = json.loads(raw)
    except json.JSONDecodeError:
        abort(400)

    if fmt == "json":
        resp = make_response(json.dumps(result, indent=2, ensure_ascii=False))
        resp.headers["Content-Type"] = "application/json"
        resp.headers["Content-Disposition"] = (
            f"attachment; filename=osint_{result.get('number','query')}.json"
        )
        return resp

    if fmt == "csv":
        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow([
            "source", "full_name", "email", "phone", "ip",
            "country", "region", "address", "hash",
        ])
        for src in result.get("sources", []):
            for rec in src.get("records", []):
                writer.writerow([
                    src["title"],
                    rec.get("full_name", ""),
                    rec.get("email", ""),
                    ", ".join(rec.get("phones", [])),
                    rec.get("ip", ""),
                    rec.get("country", ""),
                    rec.get("region", ""),
                    ", ".join(rec.get("addresses", [])),
                    rec.get("hash", ""),
                ])
        resp = make_response(output.getvalue())
        resp.headers["Content-Type"] = "text/csv"
        resp.headers["Content-Disposition"] = (
            f"attachment; filename=osint_{result.get('number','query')}.csv"
        )
        return resp

    abort(400)


@search_bp.route("/search/share", methods=["POST"])
@login_required
def share():
    cfg = current_app.config["TIER_LIMITS"]
    if not cfg.get(current_user.tier, {}).get("export", False):
        return jsonify({"error": "Upgrade required"}), 403

    raw = request.form.get("result_json", "")
    try:
        json.loads(raw)
    except json.JSONDecodeError:
        return jsonify({"error": "Invalid data"}), 400

    encoded = base64.urlsafe_b64encode(raw.encode()).decode()
    link = url_for("search.view_shared", token=encoded, _external=True)
    return jsonify({"link": link})


@search_bp.route("/s/<token>")
def view_shared(token: str):
    try:
        raw = base64.urlsafe_b64decode(token.encode()).decode()
        result = json.loads(raw)
    except Exception:
        abort(404)
    return render_template("dashboard/search_shared.html", result=result)
