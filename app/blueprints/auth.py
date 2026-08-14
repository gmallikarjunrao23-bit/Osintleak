"""Authentication blueprint."""
from __future__ import annotations

from datetime import datetime, timezone
from flask import (
    Blueprint, render_template, redirect, url_for,
    flash, request, session, current_app,
)
from flask_login import login_user, logout_user, login_required, current_user

from app.extensions import db
from app.models import User, AuditLog

auth_bp = Blueprint("auth", __name__)


def _log_audit(action: str, user: User | None = None, details: str = "") -> None:
    try:
        log = AuditLog(
            user_id=user.id if user else None,
            action=action,
            ip_address=request.remote_addr,
            user_agent=request.user_agent.string[:512],
            details=details,
        )
        db.session.add(log)
    except Exception:
        pass


@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    if current_user.is_authenticated:
        return redirect(url_for("dashboard.index"))

    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        remember = bool(request.form.get("remember"))

        user = User.query.filter_by(email=email).first()

        if not user or not user.check_password(password):
            flash("Invalid email or password.", "danger")
            return render_template("auth/login.html")

        if not user.is_active:
            flash("Your account has been suspended.", "danger")
            return render_template("auth/login.html")

        try:
            user.last_login = datetime.now(timezone.utc)
            user.last_ip = request.remote_addr
            user.last_user_agent = request.user_agent.string[:512]
            _log_audit("login", user)
            db.session.commit()
        except Exception:
            db.session.rollback()

        login_user(user, remember=remember)
        session.permanent = True

        nxt = request.args.get("next")
        return redirect(nxt or url_for("dashboard.index"))

    return render_template("auth/login.html")


@auth_bp.route("/register", methods=["GET", "POST"])
def register():
    if current_user.is_authenticated:
        return redirect(url_for("dashboard.index"))

    if request.method == "POST":
        full_name = request.form.get("full_name", "").strip()
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        referral = request.form.get("referral", "").strip().upper()

        if not full_name or not email or not password:
            flash("All fields are required.", "danger")
            return render_template("auth/register.html")

        if len(password) < 6:
            flash("Password must be at least 6 characters.", "danger")
            return render_template("auth/register.html")

        if User.query.filter_by(email=email).first():
            flash("Email already registered.", "danger")
            return render_template("auth/register.html")

        referred_by = None
        if referral:
            try:
                ref_user = User.query.filter_by(referral_code=referral).first()
                if ref_user:
                    referred_by = ref_user.referral_code
            except Exception:
                pass

        try:
            user = User(
                full_name=full_name,
                email=email,
                referred_by=referred_by,
            )
            user.set_password(password)
            db.session.add(user)
            db.session.commit()
            _log_audit("register", user)
            db.session.commit()
        except Exception as e:
            db.session.rollback()
            flash("Registration failed. Try again.", "danger")
            return render_template("auth/register.html")

        login_user(user, remember=True)
        session.permanent = True
        flash(f"Welcome to {current_app.config['SITE_NAME']}, {full_name}!", "success")
        return redirect(url_for("dashboard.index"))

    return render_template("auth/register.html")


@auth_bp.route("/logout")
@login_required
def logout():
    try:
        _log_audit("logout", current_user)
        db.session.commit()
    except Exception:
        pass
    logout_user()
    flash("Logged out successfully.", "info")
    return redirect(url_for("auth.login"))
