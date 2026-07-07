import os
from dotenv import load_dotenv

load_dotenv()


class Config:
    SECRET_KEY = os.environ.get("FLASK_SECRET_KEY", "dev-key-insecure")
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SITE_PASSWORD = os.environ.get("SITE_PASSWORD", "")
    ADMIN_PASSWORD = os.environ.get("ADMIN_PASSWORD", "")
    GUESTBOOK_ENABLED = os.environ.get("GUESTBOOK_ENABLED", "false").lower() == "true"
    # Cookie de session : 30 jours
    PERMANENT_SESSION_LIFETIME = 60 * 60 * 24 * 30


class DevelopmentConfig(Config):
    DEBUG = True
    SQLALCHEMY_DATABASE_URI = os.environ.get(
        "DATABASE_URL", "sqlite:///mariage_dev.db"
    )


class ProductionConfig(Config):
    DEBUG = False
    db_url = os.environ.get("DATABASE_URL", "")
    # Railway fournit parfois postgres:// — SQLAlchemy exige postgresql://
    if db_url.startswith("postgres://"):
        db_url = db_url.replace("postgres://", "postgresql://", 1)
    SQLALCHEMY_DATABASE_URI = db_url


config_by_name = {
    "development": DevelopmentConfig,
    "production": ProductionConfig,
}
