"""Application configuration."""
import os
from datetime import timedelta


class Config:
    SECRET_KEY: str = os.environ.get("SECRET_KEY", "changeme-set-in-railway")
    SQLALCHEMY_DATABASE_URI: str = os.environ.get("DATABASE_URL", "sqlite:///osint100x.db")
    SQLALCHEMY_TRACK_MODIFICATIONS: bool = False
    SQLALCHEMY_ENGINE_OPTIONS: dict = {
        "pool_pre_ping": True,
        "pool_recycle": 300,
    }
    PERMANENT_SESSION_LIFETIME: timedelta = timedelta(days=30)
    SESSION_COOKIE_SECURE: bool = False
    SESSION_COOKIE_HTTPONLY: bool = True
    SESSION_COOKIE_SAMESITE: str = "Lax"

    API_URL: str = os.environ.get("API_URL", "https://sahil-33rd.onrender.com/api/leakpro")
    API_KEY: str = os.environ.get("API_KEY", "SAHILS")
    API_TIMEOUT: int = 25

    CACHE_TYPE: str = os.environ.get("CACHE_TYPE", "SimpleCache")
    CACHE_DEFAULT_TIMEOUT: int = 3600
    CACHE_REDIS_URL: str = os.environ.get("REDIS_URL", "")

    RATELIMIT_DEFAULT: str = os.environ.get("RATELIMIT_DEFAULT", "10 per minute")
    RATELIMIT_STORAGE_URL: str = os.environ.get("REDIS_URL", "memory://")
    RATELIMIT_HEADERS_ENABLED: bool = True

    SITE_NAME: str = os.environ.get("SITE_NAME", "OSINT 100X")
    DEVELOPER: str = os.environ.get("DEVELOPER", "@DEVILHASHJ")
    VERSION: str = os.environ.get("VERSION", "100X ULTIMATE")
    UPI_ID: str = os.environ.get("UPI_ID", "9866583926@axl")
    BANK_NAME: str = os.environ.get("BANK_NAME", "Union Bank Of India")
    BOT_TOKEN: str = os.environ.get("BOT_TOKEN", "")

    TIER_LIMITS: dict = {
        "free":       {"searches_day": 3,     "export": False, "price": 0},
        "premium":    {"searches_day": 100,   "export": True,  "price": 99},
        "pro":        {"searches_day": 99999, "export": True,  "price": 299},
        "enterprise": {"searches_day": 99999, "export": True,  "price": 999},
    }
    TIER_BADGES: dict = {
        "free":       ("🆓", "#6b7280"),
        "premium":    ("👑", "#7c3aed"),
        "pro":        ("⚡", "#06b6d4"),
        "enterprise": ("🏢", "#10b981"),
    }


class DevelopmentConfig(Config):
    DEBUG: bool = True
    SQLALCHEMY_DATABASE_URI: str = os.environ.get("DATABASE_URL", "sqlite:///osint100x_dev.db")
    CACHE_TYPE: str = "SimpleCache"
    RATELIMIT_STORAGE_URL: str = "memory://"


class ProductionConfig(Config):
    DEBUG: bool = False


config_map = {
    "development": DevelopmentConfig,
    "production":  ProductionConfig,
    "default":     DevelopmentConfig,
}
