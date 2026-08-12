"""Internal API blueprint."""
from flask import Blueprint, jsonify, current_app

api_bp = Blueprint("api_internal", __name__)


@api_bp.route("/health")
def health():
    return jsonify({
        "status": "healthy",
        "version": current_app.config.get("VERSION", "100X ULTIMATE"),
        "site": current_app.config.get("SITE_NAME", "OSINT 100X"),
    })
