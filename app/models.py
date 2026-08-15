"""Database models."""
from __future__ import annotations
import uuid
import string
import random
from datetime import datetime, timezone
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from app.extensions import db


def _utcnow():
    return datetime.now(timezone.utc)


class User(UserMixin, db.Model):
    __tablename__ = "users"
    __table_args__ = {"extend_existing": True}

    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(255), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(512), nullable=False)
    full_name = db.Column(db.String(255), nullable=False)
    tier = db.Column(db.String(20), nullable=False, default="free")
    is_active = db.Column(db.Boolean, nullable=False, default=True)
    is_admin = db.Column(db.Boolean, nullable=False, default=False)
    created_at = db.Column(db.DateTime, default=_utcnow)
    last_login = db.Column(db.DateTime, nullable=True)
    total_searches = db.Column(db.Integer, nullable=False, default=0)
    searches_today = db.Column(db.Integer, nullable=False, default=0)
    last_search_date = db.Column(db.Date, nullable=True)
    premium_expiry = db.Column(db.DateTime, nullable=True)
    last_ip = db.Column(db.String(45), nullable=True)

    search_logs = db.relationship("SearchLog", back_populates="user", lazy="dynamic", cascade="all, delete-orphan")
    payments = db.relationship("Payment", back_populates="user", foreign_keys="Payment.user_id", lazy="dynamic", cascade="all, delete-orphan")
    audit_logs = db.relationship("AuditLog", back_populates="user", lazy="dynamic", cascade="all, delete-orphan")

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
        return f"https://api.dicebear.com/7.x/identicon/svg?seed={self.email}"


class SearchLog(db.Model):
    __tablename__ = "search_logs"
    __table_args__ = {"extend_existing": True}

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    query = db.Column(db.String(512), nullable=False)
    query_type = db.Column(db.String(20), nullable=False, default="any")
    result_count = db.Column(db.Integer, nullable=False, default=0)
    response_time = db.Column(db.Float, nullable=True)
    api_status = db.Column(db.String(20), nullable=False, default="ok")
    error_message = db.Column(db.Text, nullable=True)
    ip_address = db.Column(db.String(45), nullable=True)
    user_agent = db.Column(db.String(512), nullable=True)
    created_at = db.Column(db.DateTime, default=_utcnow, index=True)

    user = db.relationship("User", back_populates="search_logs")


class Payment(db.Model):
    __tablename__ = "payments"
    __table_args__ = {"extend_existing": True}

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    amount = db.Column(db.Float, nullable=False)
    tier = db.Column(db.String(20), nullable=False)
    transaction_id = db.Column(db.String(255), unique=True, nullable=False)
    screenshot_url = db.Column(db.String(1024), nullable=True)
    upi_id = db.Column(db.String(255), nullable=True)
    status = db.Column(db.String(20), nullable=False, default="pending")
    admin_notes = db.Column(db.Text, nullable=True)
    admin_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True)
    created_at = db.Column(db.DateTime, default=_utcnow)
    approved_at = db.Column(db.DateTime, nullable=True)

    user = db.relationship("User", back_populates="payments", foreign_keys=[user_id])
    admin = db.relationship("User", foreign_keys=[admin_id])


class AuditLog(db.Model):
    __tablename__ = "audit_logs"
    __table_args__ = {"extend_existing": True}

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True)
    action = db.Column(db.String(100), nullable=False)
    resource = db.Column(db.String(100), nullable=True)
    resource_id = db.Column(db.String(100), nullable=True)
    details = db.Column(db.Text, nullable=True)
    ip_address = db.Column(db.String(45), nullable=True)
    created_at = db.Column(db.DateTime, default=_utcnow)

    user = db.relationship("User", back_populates="audit_logs")
