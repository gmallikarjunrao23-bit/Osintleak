"""Search blueprint — multi-format export."""
from __future__ import annotations
import json, base64, csv, io
from flask import Blueprint, render_template, request, jsonify, current_app, flash, redirect, url_for, make_response, abort
from flask_login import login_required, current_user
from app.extensions import db
from app.models import SearchLog
from app.services.osint import search as osint_search

search_bp = Blueprint("search", __name__)


def _get_tier_cfg():
    return current_app.config["TIER_LIMITS"].get(current_user.tier, current_app.config["TIER_LIMITS"]["free"])


def _check_limit():
    try:
        current_user.reset_daily_if_needed()
        cfg = _get_tier_cfg()
        limit = cfg.get("searches_day", 3)
        return current_user.searches_today < limit
    except Exception:
        return True


def _can_export(fmt):
    cfg = _get_tier_cfg()
    return fmt in cfg.get("export", [])


def _record_search(result):
    try:
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
    except Exception:
        db.session.rollback()


@search_bp.route("/search", methods=["GET", "POST"])
@login_required
def index():
    result = None
    query = ""
    if request.method == "POST":
        query = request.form.get("query", "").strip()
        if not query:
            flash("Please enter a search query.", "warning")
            return render_template("dashboard/search.html", result=None, query=query)
        if not _check_limit():
            flash("Daily search limit reached. Upgrade your plan.", "danger")
            return redirect(url_for("billing.index"))
        result = osint_search(query)
        _record_search(result)
        # Limit sources visible for free tier
        cfg = _get_tier_cfg()
        max_src = cfg.get("sources_visible", 2)
        if result and result.get("sources") and len(result["sources"]) > max_src:
            result["sources_hidden"] = len(result["sources"]) - max_src
            result["sources"] = result["sources"][:max_src]
        else:
            result["sources_hidden"] = 0
    return render_template("dashboard/search.html", result=result, query=query)


@search_bp.route("/search/export/<fmt>", methods=["POST"])
@login_required
def export(fmt: str):
    if not _can_export(fmt):
        flash(f"Export as {fmt.upper()} requires a higher plan. Upgrade now.", "danger")
        return redirect(url_for("billing.index"))

    raw = request.form.get("result_json", "")
    try:
        result = json.loads(raw)
    except Exception:
        abort(400)

    if fmt == "json":
        resp = make_response(json.dumps(result, indent=2, ensure_ascii=False))
        resp.headers["Content-Type"] = "application/json"
        resp.headers["Content-Disposition"] = f"attachment; filename=osint_{result.get('number','query')}.json"
        return resp

    if fmt == "txt":
        lines = [f"OSINT 100X — Results for {result.get('query','')}\n"]
        lines.append(f"Sources: {result.get('total_sources',0)} | Records: {result.get('total_records',0)}\n")
        lines.append("="*60)
        intel = result.get("intel", {})
        for key, vals in intel.items():
            if vals:
                lines.append(f"\n[{key.upper()}]")
                for v in vals:
                    lines.append(f"  {v}")
        lines.append("\n" + "="*60 + "\nSOURCES\n" + "="*60)
        for src in result.get("sources", []):
            lines.append(f"\n{src['badge']} {src['title']}")
            for rec in src.get("records", []):
                lines.append(f"  Name: {rec.get('full_name','')} | Email: {rec.get('email','')} | Phone: {', '.join(rec.get('phones',[]))}")
        resp = make_response("\n".join(lines))
        resp.headers["Content-Type"] = "text/plain"
        resp.headers["Content-Disposition"] = f"attachment; filename=osint_{result.get('number','query')}.txt"
        return resp

    if fmt == "html":
        html = f"""<!DOCTYPE html>
<html><head><meta charset='utf-8'><title>OSINT 100X — {result.get('query','')}</title>
<style>
body{{background:#0d0d0d;color:#e0e0e0;font-family:monospace;padding:2rem;max-width:900px;margin:0 auto}}
h1{{color:#00e5ff;border-bottom:2px solid #00e5ff;padding-bottom:.5rem}}
h2{{color:#ce93d8;margin-top:2rem}}
h3{{color:#66bb6a;margin-top:1.5rem}}
table{{width:100%;border-collapse:collapse;margin-bottom:1rem}}
td{{padding:.4rem .8rem;border:1px solid #333;word-break:break-all;font-size:.85rem}}
.k{{color:#ffd54f;width:140px;font-weight:bold}}
tr:hover{{background:#1a1a2e}}
.badge{{display:inline-block;background:#1a237e;padding:.2rem .6rem;border-radius:4px;font-size:.75rem;margin-bottom:.5rem}}
</style></head><body>
<h1>🔍 OSINT 100X — {result.get('query','')}</h1>
<p style='color:#888'>Sources: {result.get('total_sources',0)} | Records: {result.get('total_records',0)} | Time: {result.get('response_time',0):.3f}s</p>
<h2>Intelligence Summary</h2>"""
        intel = result.get("intel", {})
        for key, vals in intel.items():
            if vals:
                html += f"<h3>{key.capitalize()}</h3><table>"
                for v in vals:
                    html += f"<tr><td>{v}</td></tr>"
                html += "</table>"
        html += "<h2>Source Records</h2>"
        for src in result.get("sources", []):
            html += f"<div class='badge'>{src['badge']} {src['title']}</div>"
            for rec in src.get("records", []):
                html += "<table>"
                for k, v in rec.items():
                    if v and k not in ("phones","addresses"):
                        html += f"<tr><td class='k'>{k}</td><td>{v}</td></tr>"
                if rec.get("phones"):
                    html += f"<tr><td class='k'>phones</td><td>{', '.join(rec['phones'])}</td></tr>"
                if rec.get("addresses"):
                    html += f"<tr><td class='k'>addresses</td><td>{', '.join(rec['addresses'])}</td></tr>"
                html += "</table>"
        html += f"<p style='color:#444;font-size:.75rem;margin-top:2rem'>Generated by OSINT 100X | {current_app.config['DEVELOPER']}</p></body></html>"
        resp = make_response(html)
        resp.headers["Content-Type"] = "text/html"
        resp.headers["Content-Disposition"] = f"attachment; filename=osint_{result.get('number','query')}.html"
        return resp

    if fmt == "pdf":
        try:
            from reportlab.pdfgen import canvas as pdf_canvas
            from reportlab.lib.pagesizes import A4
            from reportlab.lib import colors
            buf = io.BytesIO()
            c = pdf_canvas.Canvas(buf, pagesize=A4)
            w, h = A4
            c.setFont("Helvetica-Bold", 16)
            c.setFillColor(colors.HexColor("#7c3aed"))
            c.drawString(50, h-50, f"OSINT 100X — {result.get('query','')}")
            c.setFont("Helvetica", 10)
            c.setFillColor(colors.grey)
            c.drawString(50, h-70, f"Sources: {result.get('total_sources',0)} | Records: {result.get('total_records',0)}")
            y = h - 100
            intel = result.get("intel", {})
            for key, vals in intel.items():
                if vals and y > 80:
                    c.setFont("Helvetica-Bold", 11)
                    c.setFillColor(colors.HexColor("#06b6d4"))
                    c.drawString(50, y, key.upper())
                    y -= 15
                    c.setFont("Helvetica", 9)
                    c.setFillColor(colors.white)
                    for v in vals[:10]:
                        if y < 80:
                            c.showPage()
                            y = h - 50
                        c.drawString(70, y, str(v)[:80])
                        y -= 13
                    y -= 5
            c.save()
            buf.seek(0)
            resp = make_response(buf.read())
            resp.headers["Content-Type"] = "application/pdf"
            resp.headers["Content-Disposition"] = f"attachment; filename=osint_{result.get('number','query')}.pdf"
            return resp
        except ImportError:
            # reportlab not installed — fallback to txt
            flash("PDF export unavailable. Falling back to TXT.", "warning")
            return redirect(url_for("search.index"))

    abort(400)


@search_bp.route("/search/share", methods=["POST"])
@login_required
def share():
    if not _can_export("json"):
        return jsonify({"error": "Upgrade required"}), 403
    raw = request.form.get("result_json", "")
    try:
        json.loads(raw)
        encoded = base64.urlsafe_b64encode(raw.encode()).decode()
        link = url_for("search.view_shared", token=encoded, _external=True)
        return jsonify({"link": link})
    except Exception:
        return jsonify({"error": "Invalid data"}), 400


@search_bp.route("/s/<token>")
def view_shared(token):
    try:
        raw = base64.urlsafe_b64decode(token.encode()).decode()
        result = json.loads(raw)
    except Exception:
        abort(404)
    return render_template("dashboard/search_shared.html", result=result)
