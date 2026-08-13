"""Database models."""
from __future__ import annotations

import uuid
import string
import random
from datetime import datetime, timezone

from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash

from app.extensions import db


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _gen_user_id() -> str:
    return "U" + "".join(random.choices(string.digits, k=8))


def _gen_referral() -> str:
    return "".join(random.choices(string.ascii_uppercase + string.digits, k=8))


class User(UserMixin, db.Model):
    """Application user."""

    __tablename__ = "users"

    id: int = db.Column(db.Integer, primary_key=True)
    user_id: str = db.Column(
        db.String(12), unique=True, nullable=False, default=_gen_user_id
    )
    email: str = db.Column(db.String(255), unique=True, nullable=False, index=True)
    password_hash: str = db.Column(db.String(512), nullable=False)
    full_name: str = db.Column(db.String(255), nullable=False)
    tier: str = db.Column(db.String(20), nullable=False, default="free")
    is_active: bool = db.Column(db.Boolean, nullable=False, default=True)
    is_admin: bool = db.Column(db.Boolean, nullable=False, default=False)
    created_at: datetime = db.Column(db.DateTime(timezone=True), default=_utcnow)
    last_login: datetime = db.Column(db.DateTime(timezone=True), nullable=True)
    total_searches: int = db.Column(db.Integer, nullable=False, default=0)
    searches_today: int = db.Column(db.Integer, nullable=False, default=0)
    last_search_date: datetime = db.Column(db.Date, nullable=True)
    premium_expiry: datetime = db.Column(db.DateTime(timezone=True), nullable=True)
    referral_code: str = db.Column(
        db.String(12), unique=True, nullable=False, default=_gen_referral
    )
    referred_by: str = db.Column(db.String(12), nullable=True)
    last_ip: str = db.Column(db.String(45), nullable=True)
    last_user_agent: str = db.Column(db.String(512), nullable=True)
    avatar_seed: str = db.Column(
        db.String(36), nullable=False, default=lambda: str(uuid.uuid4())
    )

    # relationships
    search_logs = db.relationship(
        "SearchLog", back_populates="user", lazy="dynamic", cascade="all, delete-orphan"
    )
    payments = db.relationship(
        "Payment", back_populates="user", foreign_keys="Payment.user_id",
        lazy="dynamic", cascade="all, delete-orphan"
    )
    audit_logs = db.relationship(
        "AuditLog", back_populates="user", lazy="dynamic", cascade="all, delete-orphan"
    )

    def set_password(self, password: str) -> None:
        self.password_hash = generate_password_hash(password)

    def check_password(self, password: str) -> bool:
        return check_password_hash(self.password_hash, password)

    def reset_daily_if_needed(self) -> None:
        today = _utcnow().date()
        if self.last_search_date != today:
            self.searches_today = 0
            self.last_search_date = today

    @property
    def avatar_url(self) -> str:
        return f"https://api.dicebear.com/7.x/identicon/svg?seed={self.avatar_seed}"

    def __repr__(self) -> str:
        return f"<User {self.user_id} {self.email}>"


class SearchLog(db.Model):
    """Search history record."""

    __tablename__ = "search_logs"

    id: int = db.Column(db.Integer, primary_key=True)
    user_id: int = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    query: str = db.Column(db.String(512), nullable=False)
    query_type: str = db.Column(db.String(20), nullable=False, default="any")
    result_count: int = db.Column(db.Integer, nullable=False, default=0)
    response_time: float = db.Column(db.Float, nullable=True)
    api_status: str = db.Column(db.String(20), nullable=False, default="ok")
    error_message: str = db.Column(db.Text, nullable=True)
    ip_address: str = db.Column(db.String(45), nullable=True)
    user_agent: str = db.Column(db.String(512), nullable=True)
    created_at: datetime = db.Column(
        db.DateTime(timezone=True), default=_utcnow, index=True
    )

    user = db.relationship("User", back_populates="search_logs")

    def __repr__(self) -> str:
        return f"<SearchLog {self.id} {self.query_type}:{self.query[:20]}>"


class Payment(db.Model):
    """Payment record."""

    __tablename__ = "payments"

    id: int = db.Column(db.Integer, primary_key=True)
    user_id: int = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    amount: float = db.Column(db.Float, nullable=False)
    tier: str = db.Column(db.String(20), nullable=False)
    transaction_id: str = db.Column(db.String(255), unique=True, nullable=False)
    screenshot_url: str = db.Column(db.String(1024), nullable=True)
    upi_id: str = db.Column(db.String(255), nullable=True)
    status: str = db.Column(db.String(20), nullable=False, default="pending")
    admin_notes: str = db.Column(db.Text, nullable=True)
    admin_id: int = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True)
    created_at: datetime = db.Column(db.DateTime(timezone=True), default=_utcnow)
    approved_at: datetime = db.Column(db.DateTime(timezone=True), nullable=True)

    user = db.relationship("User", back_populates="payments", foreign_keys=[user_id])
    admin = db.relationship("User", foreign_keys=[admin_id])

    def __repr__(self) -> str:
        return f"<Payment {self.id} {self.status} {self.tier}>"


class AuditLog(db.Model):
    """Admin audit trail."""

    __tablename__ = "audit_logs"

    id: int = db.Column(db.Integer, primary_key=True)
    user_id: int = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True)
    action: str = db.Column(db.String(100), nullable=False)
    resource: str = db.Column(db.String(100), nullable=True)
    resource_id: str = db.Column(db.String(100), nullable=True)
    details: str = db.Column(db.Text, nullable=True)
    ip_address: str = db.Column(db.String(45), nullable=True)
    user_agent: str = db.Column(db.String(512), nullable=True)
    created_at: datetime = db.Column(db.DateTime(timezone=True), default=_utcnow)

    user = db.relationship("User", back_populates="audit_logs")

    def __repr__(self) -> str:
        return f"<AuditLog {self.id} {self.action}>"
