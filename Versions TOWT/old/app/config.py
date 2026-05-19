import os
from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    # Application
    APP_NAME: str = "my_newtowt"
    APP_VERSION: str = "3.0.0"
    APP_ENV: str = "production"
    DEBUG: bool = False

    # Database — no default, must come from env (.env or docker-compose)
    DATABASE_URL: str

    # Security — no default, must come from env
    SECRET_KEY: str
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 480  # 8 heures

    # API tokens (inbound)
    # Tracking CSV upload requires this token via the X-API-Token header.
    TRACKING_API_TOKEN: str = ""

    # External URL (for portal links shared with clients)
    SITE_URL: str = "https://my.newtowt.eu"

    # Pipedrive CRM integration
    PIPEDRIVE_API_TOKEN: str = ""

    # NEWTOWT Fleet
    FLEET: dict = {
        1: {"name": "Anemos", "code": 1},
        2: {"name": "Artemis", "code": 2},
        3: {"name": "Atlantis", "code": 3},
        4: {"name": "Atlas", "code": 4},
    }

    # Shortcut ports
    SHORTCUT_PORTS: list = ["FRFEC", "BRSSO"]

    class Config:
        env_file = ".env"
        extra = "allow"


@lru_cache()
def get_settings() -> Settings:
    settings = Settings()
    weak_secrets = {
        "towt_secret_key_change_in_production_2025",
        "change_me",
        "changeme",
        "secret",
    }
    if settings.SECRET_KEY in weak_secrets or len(settings.SECRET_KEY) < 32:
        raise RuntimeError(
            "SECRET_KEY must be set to a strong value (>=32 chars) via environment. "
            "Refusing to start with default/weak key."
        )
    if "towt_secure_2025" in settings.DATABASE_URL:
        raise RuntimeError(
            "DATABASE_URL uses the default weak password. "
            "Set POSTGRES_PASSWORD/DATABASE_URL via environment before starting."
        )
    return settings
