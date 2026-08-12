"""OSINT 100X — Application Factory."""
from __future__ import annotations

import os
import logging
from flask import Flask

from app.config import config_map
from app.extensions import db, login_manager, cache, limiter, csrf


def create_app(env: str | None = None) -> Flask:
    """Create and configure the Flask application."""
    if env is None:
        env = os.environ.get("FLASK_ENV", "production")

    app = Flask(__name__, template_folder="templates", static_folder="static")
    app.config.from_object(config_map.get(env, config_map["default"]))

    # Railway PostgreSQL fix — postgres:// → postgresql://
    db_url = app.config.get("SQLALCHEMY_DATABASE_URI", "")
    if db_url.startswith("postgres://"):
        app.config["SQLALCHEMY_DATABASE_URI"] = db_url.replace("postgres://", "postgresql://", 1)

    _init_extensions(app)
    _register_blueprints(app)
    _register_error_handlers(app)
    _register_shell_context(app)
    _configure_logging(app)

    return app


def _init_extensions(app: Flask) -> None:
    db.init_app(app)
    login_manager.init_app(app)
    cache.init_app(app)
    limiter.init_app(app)
    csrf.init_app(app)

    login_manager.login_view = "auth.login"
    login_manager.login_message = "Please log in to access this page."
    login_manager.login_message_category = "warning"

    from app.models import User

    @login_manager.user_loader
    def load_user(user_id: str) -> User | None:
        return db.session.get(User, int(user_id))

    with app.app_context():
        db.create_all()
        _ensure_admin(app)


def _ensure_admin(app: Flask) -> None:
    """Create default admin if none exists."""
    from app.models import User
    if not User.query.filter_by(is_admin=True).first():
        admin = User(
            email="admin@osint100x.local",
            full_name="Administrator",
            tier="enterprise",
            is_admin=True,
        )
        admin.set_password("Admin@100X!")
        db.session.add(admin)
        db.session.commit()
        app.logger.info("Default admin created: admin@osint100x.local / Admin@100X!")


def _register_blueprints(app: Flask) -> None:
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


def _register_error_handlers(app: Flask) -> None:
    from flask import render_template

    @app.errorhandler(404)
    def not_found(e):
        return render_template("errors/404.html"), 404

    @app.errorhandler(500)
    def server_error(e):
        return render_template("errors/500.html"), 500

    @app.errorhandler(429)
    def rate_limited(e):
        return render_template("errors/429.html"), 429


def _register_shell_context(app: Flask) -> None:
    from app.models import User, SearchLog, Payment, AuditLog

    @app.shell_context_processor
    def make_shell_context():
        return {
            "db": db,
            "User": User,
            "SearchLog": SearchLog,
            "Payment": Payment,
            "AuditLog": AuditLog,
        }


def _configure_logging(app: Flask) -> None:
    if not app.debug:
        logging.basicConfig(
            level=logging.INFO,
            format="%(asctime)s %(levelname)s %(name)s: %(message)s",
        )
