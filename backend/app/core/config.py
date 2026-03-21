from pydantic_settings import BaseSettings
from typing import List


class Settings(BaseSettings):
    DATABASE_URL: str = "postgresql+asyncpg://pcmonitor:password@localhost:5433/pcmonitor"
    SECRET_KEY: str = "change-me-in-production"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 15
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    SMTP_HOST: str = ""
    SMTP_PORT: int = 587
    SMTP_USER: str = ""
    SMTP_PASSWORD: str = ""
    SMTP_FROM: str = "alerts@numbers10.co.za"
    ALERT_EMAIL: str = ""  # Recipient address for alert notifications

    TELEGRAM_TOKEN: str = ""
    TELEGRAM_CHAT_ID: str = ""

    CORS_ORIGINS: str = "https://localhost:8443"
    DASHBOARD_URL: str = "https://localhost:8443"
    RETENTION_DAYS: int = 90
    ALERT_CHECK_INTERVAL: int = 30

    @property
    def cors_origins_list(self) -> List[str]:
        return [o.strip() for o in self.CORS_ORIGINS.split(",") if o.strip()]

    model_config = {"env_file": ".env", "extra": "ignore"}


settings = Settings()
