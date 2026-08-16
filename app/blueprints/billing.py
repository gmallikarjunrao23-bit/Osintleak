"""Billing blueprint — upgraded 4-tier system."""
from __future__ import annotations
from flask import Blueprint, render_template, request, flash, redirect, url_for, current_app
from flask_login import login_required, current_user
from sqlalchemy import select
from app.extensions import db
from app.models import Payment

billing_bp = Blueprint("billing", __name__)

TIER_PRICES = {"plus": 199, "pro": 499, "max": 999}

TIER_FEATURES = {
    "free": {
        "name": "Free",
        "price": 0,
        "badge": "🆓",
        "color": "#6b7280",
        "searches": "3/day",
        "export": "None",
        "history": "1 day",
        "sources": "2 sources",
        "pivot": False,
        "priority": False,
        "api": False,
        "features": [
            "3 searches per day",
            "2 breach sources visible",
            "Basic intel summary",
            "1 day search history",
        ],
        "locked": [
            "Export (JSON, TXT, HTML, PDF)",
            "Pivot targeting",
            "Full source access",
            "Priority support",
        ]
    },
    "plus": {
        "name": "Plus",
        "price": 199,
        "badge": "⭐",
        "color": "#7c3aed",
        "searches": "50/day",
        "export": "JSON, TXT",
        "history": "7 days",
        "sources": "All sources",
        "pivot": True,
        "priority": False,
        "api": False,
        "features": [
            "50 searches per day",
            "All 500+ breach sources",
            "Full intel summary",
            "Export JSON & TXT",
            "Pivot targeting",
            "7 day search history",
            "Email support",
        ],
        "locked": [
            "HTML & PDF export",
            "Priority support",
            "API access",
        ]
    },
    "pro": {
        "name": "Pro",
        "price": 499,
        "badge": "⚡",
        "color": "#06b6d4",
        "searches": "200/day",
        "export": "JSON, TXT, HTML",
        "history": "30 days",
        "sources": "All sources",
        "pivot": True,
        "priority": True,
        "api": False,
        "features": [
            "200 searches per day",
            "All 500+ breach sources",
            "Full intel + deep analysis",
            "Export JSON, TXT & HTML",
            "Pivot targeting",
            "Shareable result links",
            "30 day search history",
            "Priority support",
            "Bulk query mode",
        ],
        "locked": [
            "PDF export",
            "API access",
        ]
    },
    "max": {
        "name": "Max",
        "price": 999,
        "badge": "👑",
        "color": "#f59e0b",
        "searches": "Unlimited",
        "export": "JSON, TXT, HTML, PDF",
        "history": "Unlimited",
        "sources": "All sources",
        "pivot": True,
        "priority": True,
        "api": True,
        "features": [
            "Unlimited searches",
            "All 500+ breach sources",
            "Full intel + deep analysis",
            "Export JSON, TXT, HTML & PDF",
            "Pivot targeting",
            "Shareable result links",
            "Unlimited search history",
            "Priority 24/7 support",
            "Bulk query mode",
            "API access",
            "Custom data filters",
            "Early access to new features",
        ],
        "locked": []
    },
}


@billing_bp.route("/billing")
@login_required
def index():
    try:
        stmt = select(Payment).where(Payment.user_id == current_user.id).order_by(Payment.created_at.desc())
        history = db.session.execute(stmt).scalars().all()
    except Exception:
        history = []
    return render_template("dashboard/billing.html",
                           history=history,
                           tier_prices=TIER_PRICES,
                           tier_features=TIER_FEATURES,
                           upi_id=current_app.config["UPI_ID"],
                           bank_name=current_app.config["BANK_NAME"])


@billing_bp.route("/billing/submit", methods=["POST"])
@login_required
def submit():
    tier = request.form.get("tier", "").strip()
    txn_id = request.form.get("transaction_id", "").strip()
    upi_from = request.form.get("upi_id", "").strip()
    screenshot = request.form.get("screenshot_url", "").strip()

    if tier not in TIER_PRICES:
        flash("Invalid plan selected.", "danger")
        return redirect(url_for("billing.index"))
    if not txn_id:
        flash("Transaction ID is required.", "danger")
        return redirect(url_for("billing.index"))
    try:
        existing = db.session.execute(select(Payment).where(Payment.transaction_id == txn_id)).scalar_one_or_none()
        if existing:
            flash("Transaction ID already submitted.", "danger")
            return redirect(url_for("billing.index"))
        payment = Payment(
            user_id=current_user.id,
            amount=TIER_PRICES[tier],
            tier=tier,
            transaction_id=txn_id,
            upi_id=upi_from,
            screenshot_url=screenshot or None,
            status="pending"
        )
        db.session.add(payment)
        db.session.commit()
        flash("Payment submitted! Admin will verify and upgrade your account within 24 hours.", "success")
    except Exception as e:
        db.session.rollback()
        flash(f"Submission failed. Try again.", "danger")
    return redirect(url_for("billing.index"))


@billing_bp.route("/terms")
def terms():
    return render_template("dashboard/terms.html")
