"""Dashboard blueprint."""
from flask import Blueprint, render_template, request
from flask_login import login_required, current_user
from sqlalchemy import select
from app.extensions import db
from app.models import SearchLog

dashboard_bp = Blueprint("dashboard", __name__)


@dashboard_bp.route("/")
@login_required
def index():
    try:
        stmt = select(SearchLog).where(
            SearchLog.user_id == current_user.id
        ).order_by(SearchLog.created_at.desc()).limit(5)
        recent = db.session.execute(stmt).scalars().all()
    except Exception:
        recent = []
    return render_template("dashboard/index.html", recent=recent)


@dashboard_bp.route("/history")
@login_required
def history():
    page = request.args.get("page", 1, type=int)
    q = request.args.get("q", "").strip()
    qtype = request.args.get("type", "").strip()

    try:
        stmt = select(SearchLog).where(SearchLog.user_id == current_user.id)
        if q:
            stmt = stmt.where(SearchLog.query.ilike(f"%{q}%"))
        if qtype:
            stmt = stmt.where(SearchLog.query_type == qtype)
        stmt = stmt.order_by(SearchLog.created_at.desc())

        all_results = db.session.execute(stmt).scalars().all()
        per_page = 20
        total = len(all_results)
        start = (page - 1) * per_page
        items = all_results[start:start + per_page]

        class SimplePagination:
            def __init__(self, items, page, per_page, total):
                self.items = items
                self.page = page
                self.per_page = per_page
                self.total = total
                self.has_prev = page > 1
                self.has_next = (page * per_page) < total
                self.prev_num = page - 1
                self.next_num = page + 1
            def iter_pages(self):
                return range(1, (self.total // self.per_page) + 2)

        pagination = SimplePagination(items, page, per_page, total)
    except Exception:
        class EmptyPagination:
            items = []
            page = 1
            total = 0
            has_prev = False
            has_next = False
            prev_num = 0
            next_num = 2
            def iter_pages(self): return []
        pagination = EmptyPagination()

    return render_template("dashboard/history.html", pagination=pagination, q=q, qtype=qtype)


@dashboard_bp.route("/profile")
@login_required
def profile():
    return render_template("dashboard/profile.html")
