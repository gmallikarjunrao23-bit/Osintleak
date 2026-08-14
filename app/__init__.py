"""OSINT 100X — Application Factory."""
from __future__ import annotations
import os
import logging
from flask import Flask
from app.extensions import db, login_manager


def create_app(env: str | None = None) -> Flask:
    app = Flask(__name__, template_folder="templates", static_folder="static")

    app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY", "changeme123")
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
    app.config["PERMANENT_SESSION_LIFETIME"] = 2592000
    app.config["SESSION_COOKIE_SECURE"] = False
    app.config["SESSION_COOKIE_HTTPONLY"] = True
    app.config["SESSION_COOKIE_SAMESITE"] = "Lax"

    # DB URL
    db_url = os.environ.get("DATABASE_URL", "sqlite:///osint100x.db")
    if db_url.startswith("postgres://"):
        db_url = db_url.replace("postgres://", "postgresql://", 1)
    app.config["SQLALCHEMY_DATABASE_URI"] = db_url

    # Site
    app.config["SITE_NAME"] = os.environ.get("SITE_NAME", "OSINT 100X")
    app.config["DEVELOPER"] = os.environ.get("DEVELOPER", "@DEVILHASHJ")
    app.config["VERSION"] = os.environ.get("VERSION", "100X ULTIMATE")
    app.config["UPI_ID"] = os.environ.get("UPI_ID", "9866583926@axl")
    app.config["BANK_NAME"] = os.environ.get("BANK_NAME", "Union Bank Of India")
    app.config["BOT_TOKEN"] = os.environ.get("BOT_TOKEN", "")
    app.config["API_URL"] = os.environ.get("API_URL", "https://sahil-33rd.onrender.com/api/leakpro")
    app.config["API_KEY"] = os.environ.get("API_KEY", "SAHILS")
    app.config["API_TIMEOUT"] = 25

    app.config["TIER_LIMITS"] = {
        "free":       {"searches_day": 3,     "export": False, "price": 0},
        "premium":    {"searches_day": 100,   "export": True,  "price": 99},
        "pro":        {"searches_day": 99999, "export": True,  "price": 299},
        "enterprise": {"searches_day": 99999, "export": True,  "price": 999},
    }
    app.config["TIER_BADGES"] = {
        "free":       ("🆓", "#6b7280"),
        "premium":    ("👑", "#7c3aed"),
        "pro":        ("⚡", "#06b6d4"),
        "enterprise": ("🏢", "#10b981"),
    }

    db.init_app(app)
    login_manager.init_app(app)
    login_manager.login_view = "auth.login"
    login_manager.login_message = "Please log in."
    login_manager.login_message_category = "warning"

    from app.models import User

    @login_manager.user_loader
    def load_user(user_id):
        return db.session.get(User, int(user_id))

    with app.app_context():
        db.create_all()
        _ensure_admin(app)

    _register_blueprints(app)
    _register_error_handlers(app)
    return app


def _ensure_admin(app):
    from app.models import User
    try:
        if not User.query.filter_by(is_admin=True).first():
            admin = User(email="admin@osint100x.local", full_name="Administrator", tier="enterprise", is_admin=True)
            admin.set_password("Admin@100X!")
            db.session.add(admin)
            db.session.commit()
    except Exception as e:
        db.session.rollback()
        app.logger.error(f"Admin creation failed: {e}")


def _register_blueprints(app):
    from app.blueprints.auth import auth_bp
    from app.blueprints.dashboard import dashboard_bp
    from app.blueprints.search import search_bp
    from app.blueprints.billing import billing_bp
    from app.blueprints.admin import admin_bp
    from app.blueprints.api import api_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(dashboard_bp)
    app.register_blueprint(search_bp)
    app.register_blueprint(billing_bp)
    app.register_blueprint(admin_bp, url_prefix="/admin")
    app.register_blueprint(api_bp, url_prefix="/api")


def _register_error_handlers(app):
    from flask import render_template

    @app.errorhandler(404)
    def not_found(e):
        return render_template("errors/404.html"), 404

    @app.errorhandler(500)
    def server_error(e):
        return render_template("errors/500.html"), 500
