"""Admin blueprint."""
from __future__ import annotations

from datetime import datetime, timezone, timedelta
from functools import wraps

from flask import (
    Blueprint, render_template, request, redirect,
    url_for, flash, abort, jsonify, current_app,
)
from flask_login import login_required, current_user
from sqlalchemy import func

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


def _audit(action: str, resource: str = "", resource_id: str = "", details: str = ""):
    log = AuditLog(
        user_id=current_user.id,
        action=action,
        resource=resource,
        resource_id=str(resource_id),
        details=details,
        ip_address=request.remote_addr,
        user_agent=request.user_agent.string[:512],
    )
    db.session.add(log)


@admin_bp.route("/")
@login_required
@admin_required
def index():
    today = datetime.now(timezone.utc).date()
    stats = {
        "total_users":    User.query.count(),
        "premium_users":  User.query.filter(User.tier != "free").count(),
        "pending_payments": Payment.query.filter_by(status="pending").count(),
        "today_searches": SearchLog.query.filter(
            func.date(SearchLog.created_at) == today
        ).count(),
        "revenue": db.session.query(
            func.coalesce(func.sum(Payment.amount), 0)
        ).filter_by(status="approved").scalar() or 0,
    }
    recent_users = User.query.order_by(User.created_at.desc()).limit(5).all()
    recent_payments = Payment.query.order_by(Payment.created_at.desc()).limit(5).all()
    return render_template(
        "admin/index.html", stats=stats,
        recent_users=recent_users, recent_payments=recent_payments,
    )


@admin_bp.route("/users")
@login_required
@admin_required
def users():
    page = request.args.get("page", 1, type=int)
    q = request.args.get("q", "").strip()
    query = User.query
    if q:
        query = query.filter(
            User.email.ilike(f"%{q}%") | User.full_name.ilike(f"%{q}%")
        )
    pagination = query.order_by(User.created_at.desc()).paginate(
        page=page, per_page=25, error_out=False
    )
    return render_template("admin/users.html", pagination=pagination, q=q)


@admin_bp.route("/users/<int:user_id>/tier", methods=["POST"])
@login_required
@admin_required
def set_tier(user_id: int):
    user = db.session.get(User, user_id)
    if not user:
        abort(404)
    tier = request.form.get("tier", "free")
    if tier not in ("free", "premium", "pro", "enterprise"):
        abort(400)
    old = user.tier
    user.tier = tier
    if tier != "free":
        user.premium_expiry = datetime.now(timezone.utc) + timedelta(days=30)
    _audit("set_tier", "user", user_id, f"{old} → {tier}")
    db.session.commit()
    flash(f"User {user.email} tier set to {tier}.", "success")
    return redirect(url_for("admin.users"))


@admin_bp.route("/users/<int:user_id>/toggle", methods=["POST"])
@login_required
@admin_required
def toggle_user(user_id: int):
    user = db.session.get(User, user_id)
    if not user:
        abort(404)
    user.is_active = not user.is_active
    _audit("toggle_active", "user", user_id, f"active={user.is_active}")
    db.session.commit()
    flash(
        f"User {user.email} {'activated' if user.is_active else 'suspended'}.",
        "success",
    )
    return redirect(url_for("admin.users"))


@admin_bp.route("/payments")
@login_required
@admin_required
def payments():
    page = request.args.get("page", 1, type=int)
    status = request.args.get("status", "").strip()
    query = Payment.query
    if status:
        query = query.filter_by(status=status)
    pagination = query.order_by(Payment.created_at.desc()).paginate(
        page=page, per_page=25, error_out=False
    )
    return render_template(
        "admin/payments.html", pagination=pagination, status=status
    )


@admin_bp.route("/payments/<int:payment_id>/approve", methods=["POST"])
@login_required
@admin_required
def approve_payment(payment_id: int):
    payment = db.session.get(Payment, payment_id)
    if not payment or payment.status != "pending":
        abort(404)

    notes = request.form.get("notes", "").strip()
    payment.status = "approved"
    payment.admin_notes = notes
    payment.admin_id = current_user.id
    payment.approved_at = datetime.now(timezone.utc)

    user = db.session.get(User, payment.user_id)
    if user:
        user.tier = payment.tier
        user.premium_expiry = datetime.now(timezone.utc) + timedelta(days=30)

    _audit("approve_payment", "payment", payment_id, f"tier={payment.tier}")
    db.session.commit()
    flash(f"Payment #{payment_id} approved. User upgraded to {payment.tier}.", "success")
    return redirect(url_for("admin.payments"))


@admin_bp.route("/payments/<int:payment_id>/reject", methods=["POST"])
@login_required
@admin_required
def reject_payment(payment_id: int):
    payment = db.session.get(Payment, payment_id)
    if not payment or payment.status != "pending":
        abort(404)

    notes = request.form.get("notes", "").strip()
    payment.status = "rejected"
    payment.admin_notes = notes
    payment.admin_id = current_user.id

    _audit("reject_payment", "payment", payment_id)
    db.session.commit()
    flash(f"Payment #{payment_id} rejected.", "warning")
    return redirect(url_for("admin.payments"))


@admin_bp.route("/logs")
@login_required
@admin_required
def logs():
    page = request.args.get("page", 1, type=int)
    pagination = (
        AuditLog.query
        .order_by(AuditLog.created_at.desc())
        .paginate(page=page, per_page=50, error_out=False)
    )
    return render_template("admin/logs.html", pagination=pagination)
