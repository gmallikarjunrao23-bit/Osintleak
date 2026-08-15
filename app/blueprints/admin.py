"""Admin blueprint."""
from __future__ import annotations
from datetime import datetime, timezone, timedelta
from functools import wraps
from flask import Blueprint, render_template, request, redirect, url_for, flash, abort
from flask_login import login_required, current_user
from sqlalchemy import select, func
from app.extensions import db
from app.models import User, Payment, SearchLog, AuditLog

admin_bp = Blueprint("admin", __name__)


def admin_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if not current_user.is_authenticated or not current_user.is_admin:
            abort(403)
        return f(*args, **kwargs)
    return decorated


@admin_bp.route("/")
@login_required
@admin_required
def index():
    try:
        total_users = db.session.execute(select(func.count(User.id))).scalar()
        premium_users = db.session.execute(select(func.count(User.id)).where(User.tier != "free")).scalar()
        pending_payments = db.session.execute(select(func.count(Payment.id)).where(Payment.status == "pending")).scalar()
        revenue = db.session.execute(select(func.coalesce(func.sum(Payment.amount), 0)).where(Payment.status == "approved")).scalar() or 0
        today_searches = db.session.execute(select(func.count(SearchLog.id))).scalar()
        stats = {"total_users": total_users, "premium_users": premium_users,
                 "pending_payments": pending_payments, "revenue": revenue, "today_searches": today_searches}
        recent_users = db.session.execute(select(User).order_by(User.created_at.desc()).limit(5)).scalars().all()
        recent_payments = db.session.execute(select(Payment).order_by(Payment.created_at.desc()).limit(5)).scalars().all()
    except Exception:
        stats = {"total_users":0,"premium_users":0,"pending_payments":0,"revenue":0,"today_searches":0}
        recent_users = []
        recent_payments = []
    return render_template("admin/index.html", stats=stats, recent_users=recent_users, recent_payments=recent_payments)


@admin_bp.route("/users")
@login_required
@admin_required
def users():
    page = request.args.get("page", 1, type=int)
    q = request.args.get("q", "").strip()
    try:
        stmt = select(User)
        if q:
            stmt = stmt.where(User.email.ilike(f"%{q}%") | User.full_name.ilike(f"%{q}%"))
        stmt = stmt.order_by(User.created_at.desc())
        all_users = db.session.execute(stmt).scalars().all()
        per_page = 25
        total = len(all_users)
        start = (page - 1) * per_page
        items = all_users[start:start + per_page]

        class P:
            def __init__(s):
                s.items = items; s.page = page; s.total = total
                s.has_prev = page > 1; s.has_next = (page * per_page) < total
                s.prev_num = page - 1; s.next_num = page + 1
            def iter_pages(s): return range(1, (total // per_page) + 2)
        pagination = P()
    except Exception:
        class EP:
            items=[]; page=1; total=0; has_prev=False; has_next=False; prev_num=0; next_num=2
            def iter_pages(s): return []
        pagination = EP()
    return render_template("admin/users.html", pagination=pagination, q=q)


@admin_bp.route("/users/<int:user_id>/tier", methods=["POST"])
@login_required
@admin_required
def set_tier(user_id):
    user = db.session.get(User, user_id)
    if not user: abort(404)
    tier = request.form.get("tier", "free")
    user.tier = tier
    if tier != "free":
        user.premium_expiry = datetime.now(timezone.utc) + timedelta(days=30)
    try:
        db.session.commit()
        flash(f"User {user.email} tier set to {tier}.", "success")
    except Exception:
        db.session.rollback()
    return redirect(url_for("admin.users"))


@admin_bp.route("/users/<int:user_id>/toggle", methods=["POST"])
@login_required
@admin_required
def toggle_user(user_id):
    user = db.session.get(User, user_id)
    if not user: abort(404)
    user.is_active = not user.is_active
    try:
        db.session.commit()
        flash(f"User {'activated' if user.is_active else 'suspended'}.", "success")
    except Exception:
        db.session.rollback()
    return redirect(url_for("admin.users"))


@admin_bp.route("/payments")
@login_required
@admin_required
def payments():
    page = request.args.get("page", 1, type=int)
    status = request.args.get("status", "").strip()
    try:
        stmt = select(Payment)
        if status: stmt = stmt.where(Payment.status == status)
        stmt = stmt.order_by(Payment.created_at.desc())
        all_p = db.session.execute(stmt).scalars().all()
        per_page = 25
        total = len(all_p)
        start = (page - 1) * per_page
        items = all_p[start:start + per_page]

        class P:
            def __init__(s):
                s.items = items; s.page = page; s.total = total
                s.has_prev = page > 1; s.has_next = (page * per_page) < total
                s.prev_num = page - 1; s.next_num = page + 1
            def iter_pages(s): return range(1, (total // per_page) + 2)
        pagination = P()
    except Exception:
        class EP:
            items=[]; page=1; total=0; has_prev=False; has_next=False; prev_num=0; next_num=2
            def iter_pages(s): return []
        pagination = EP()
    return render_template("admin/payments.html", pagination=pagination, status=status)


@admin_bp.route("/payments/<int:payment_id>/approve", methods=["POST"])
@login_required
@admin_required
def approve_payment(payment_id):
    payment = db.session.get(Payment, payment_id)
    if not payment or payment.status != "pending": abort(404)
    payment.status = "approved"
    payment.admin_notes = request.form.get("notes", "")
    payment.admin_id = current_user.id
    payment.approved_at = datetime.now(timezone.utc)
    user = db.session.get(User, payment.user_id)
    if user:
        user.tier = payment.tier
        user.premium_expiry = datetime.now(timezone.utc) + timedelta(days=30)
    try:
        db.session.commit()
        flash(f"Payment #{payment_id} approved.", "success")
    except Exception:
        db.session.rollback()
    return redirect(url_for("admin.payments"))


@admin_bp.route("/payments/<int:payment_id>/reject", methods=["POST"])
@login_required
@admin_required
def reject_payment(payment_id):
    payment = db.session.get(Payment, payment_id)
    if not payment or payment.status != "pending": abort(404)
    payment.status = "rejected"
    payment.admin_notes = request.form.get("notes", "")
    payment.admin_id = current_user.id
    try:
        db.session.commit()
        flash(f"Payment #{payment_id} rejected.", "warning")
    except Exception:
        db.session.rollback()
    return redirect(url_for("admin.payments"))


@admin_bp.route("/logs")
@login_required
@admin_required
def logs():
    page = request.args.get("page", 1, type=int)
    try:
        stmt = select(AuditLog).order_by(AuditLog.created_at.desc())
        all_logs = db.session.execute(stmt).scalars().all()
        per_page = 50
        total = len(all_logs)
        start = (page - 1) * per_page
        items = all_logs[start:start + per_page]

        class P:
            def __init__(s):
                s.items = items; s.page = page; s.total = total
                s.has_prev = page > 1; s.has_next = (page * per_page) < total
                s.prev_num = page - 1; s.next_num = page + 1
            def iter_pages(s): return range(1, (total // per_page) + 2)
        pagination = P()
    except Exception:
        class EP:
            items=[]; page=1; total=0; has_prev=False; has_next=False; prev_num=0; next_num=2
            def iter_pages(s): return []
        pagination = EP()
    return render_template("admin/logs.html", pagination=pagination)
