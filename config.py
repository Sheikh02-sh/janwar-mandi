import os
from dotenv import load_dotenv

load_dotenv()
BASE_DIR = os.path.abspath(os.path.dirname(__file__))

# Render apne aap RENDER=true set karta hai.
IS_PRODUCTION = bool(os.getenv("RENDER"))

_secret = os.getenv("SECRET_KEY")
if not _secret:
    if IS_PRODUCTION:
        # Default key ke saath login sessions forge ho sakte hain, is liye production mein rok dein.
        raise RuntimeError("SECRET_KEY environment variable Render par set karein.")
    _secret = "dev-secret-change-me"

# Render PostgreSQL "postgres://..." deta hai, SQLAlchemy ko "postgresql://..." chahiye.
_db_url = os.getenv("DATABASE_URL", "sqlite:///livestock.db")
if _db_url.startswith("postgres://"):
    _db_url = _db_url.replace("postgres://", "postgresql://", 1)


class Config:
    SECRET_KEY = _secret
    SQLALCHEMY_DATABASE_URI = _db_url
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_ENGINE_OPTIONS = {"pool_pre_ping": True}

    # Uploads: default app/static/uploads. Render Disk lagayein to UPLOAD_FOLDER env var mein mount path dein.
    UPLOAD_FOLDER = os.getenv(
        "UPLOAD_FOLDER", os.path.join(BASE_DIR, "app", "static", "uploads")
    )
    MAX_CONTENT_LENGTH = 20 * 1024 * 1024  # 20 MB per request

    # Cookies: production (HTTPS) mein secure.
    SESSION_COOKIE_SECURE = IS_PRODUCTION
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = "Lax"
    REMEMBER_COOKIE_SECURE = IS_PRODUCTION
    REMEMBER_COOKIE_HTTPONLY = True

    PUBLIC_BASE_URL = os.getenv("PUBLIC_BASE_URL", "")
    FB_PAGE_ID = os.getenv("FB_PAGE_ID")
    FB_PAGE_ACCESS_TOKEN = os.getenv("FB_PAGE_ACCESS_TOKEN")
    FB_GRAPH_VERSION = os.getenv("FB_GRAPH_VERSION", "v21.0")