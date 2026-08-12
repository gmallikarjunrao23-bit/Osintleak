"""Dashboard blueprint."""
from flask import Blueprint, render_template, request
from flask_login import login_required, current_user

from app.models import SearchLog

dashboard_bp = Blueprint("dashboard", __name__)


@dashboard_bp.route("/")
@login_required
def index():
    recent = (
        SearchLog.query
        .filter_by(user_id=current_user.id)
        .order_by(SearchLog.created_at.desc())
        .limit(5)
        .all()
    )
    return render_template("dashboard/index.html", recent=recent)


@dashboard_bp.route("/history")
@login_required
def history():
    page = request.args.get("page", 1, type=int)
    q = request.args.get("q", "").strip()
    qtype = request.args.get("type", "").strip()

    query = SearchLog.query.filter_by(user_id=current_user.id)

    if q:
        query = query.filter(SearchLog.query.ilike(f"%{q}%"))
    if qtype:
        query = query.filter_by(query_type=qtype)

    pagination = (
        query.order_by(SearchLog.created_at.desc())
        .paginate(page=page, per_page=20, error_out=False)
    )
    return render_template("dashboard/history.html", pagination=pagination, q=q, qtype=qtype)


@dashboard_bp.route("/profile")
@login_required
def profile():
    return render_template("dashboard/profile.html")
