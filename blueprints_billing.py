"""Billing blueprint — UPI payment flow."""
from __future__ import annotations

from flask import (
    Blueprint, render_template, request, flash,
    redirect, url_for, current_app,
)
from flask_login import login_required, current_user

from app.extensions import db
from app.models import Payment

billing_bp = Blueprint("billing", __name__)

TIER_PRICES = {
    "premium":    99,
    "pro":        299,
    "enterprise": 999,
}


@billing_bp.route("/billing")
@login_required
def index():
    history = (
        Payment.query
        .filter_by(user_id=current_user.id)
        .order_by(Payment.created_at.desc())
        .all()
    )
    return render_template(
        "dashboard/billing.html",
        history=history,
        tier_prices=TIER_PRICES,
        upi_id=current_app.config["UPI_ID"],
        bank_name=current_app.config["BANK_NAME"],
    )


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

    if Payment.query.filter_by(transaction_id=txn_id).first():
        flash("Transaction ID already submitted.", "danger")
        return redirect(url_for("billing.index"))

    payment = Payment(
        user_id=current_user.id,
        amount=TIER_PRICES[tier],
        tier=tier,
        transaction_id=txn_id,
        upi_id=upi_from,
        screenshot_url=screenshot or None,
        status="pending",
    )
    db.session.add(payment)
    db.session.commit()

    flash(
        "Payment submitted! Admin will approve within 24 hours. "
        "You'll get access once approved.",
        "success",
    )
    return redirect(url_for("billing.index"))
