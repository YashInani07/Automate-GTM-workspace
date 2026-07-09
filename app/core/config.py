import os
from typing import Optional
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    PROJECT_NAME: str = "GTM Automated Workflow"
    DATABASE_URL: str
    DATABASE_URL_SYNC: str
    JINA_API_KEY: str
    GEMINI_API_KEY: str
    ZAPIER_WEBHOOK_URL: Optional[str] = ""
    CRM_WEBHOOK_URL: Optional[str] = ""
    GMAIL_USER: Optional[str] = ""
    GMAIL_APP_PASSWORD: Optional[str] = ""
    LOG_LEVEL: str = "INFO"
    CELERY_BROKER_URL: str = "redis://redis:6379/0"
    CELERY_RESULT_BACKEND: str = "redis://redis:6379/0"
    IMAP_HOST: str = "imap.gmail.com"
    IMAP_PORT: int = 993
    IMAP_USER: Optional[str] = ""
    IMAP_PASSWORD: Optional[str] = ""
    REPLY_POLL_INTERVAL_MINUTES: int = 5

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )

settings = Settings()
