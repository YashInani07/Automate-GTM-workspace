import os
from typing import Optional
from pydantic import field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    PROJECT_NAME: str = "GTM Automated Workflow"
    DATABASE_URL: str
    DATABASE_URL_SYNC: Optional[str] = None
    JINA_API_KEY: str
    GEMINI_API_KEY: str
    ZAPIER_WEBHOOK_URL: Optional[str] = ""
    CRM_WEBHOOK_URL: Optional[str] = ""
    GMAIL_USER: Optional[str] = ""
    GMAIL_APP_PASSWORD: Optional[str] = ""
    LOG_LEVEL: str = "INFO"
    CELERY_BROKER_URL: str = "redis://redis:6379/0"
    CELERY_RESULT_BACKEND: str = "redis://redis:6379/0"

    @field_validator("DATABASE_URL", mode="before")
    @classmethod
    def assemble_db_url(cls, v: str) -> str:
        if isinstance(v, str):
            if v.startswith("postgres://"):
                v = v.replace("postgres://", "postgresql+asyncpg://", 1)
            elif v.startswith("postgresql://"):
                v = v.replace("postgresql://", "postgresql+asyncpg://", 1)
            
            # asyncpg requires 'ssl=' keyword argument instead of 'sslmode='
            if "sslmode=" in v:
                v = v.replace("sslmode=", "ssl=")
        return v

    @model_validator(mode="after")
    def assemble_sync_db_url(self) -> "Settings":
        if not self.DATABASE_URL_SYNC and self.DATABASE_URL:
            url = self.DATABASE_URL
            if url.startswith("postgresql+asyncpg://"):
                url = url.replace("postgresql+asyncpg://", "postgresql+psycopg2://", 1)
            elif url.startswith("postgres://"):
                url = url.replace("postgres://", "postgresql+psycopg2://", 1)
            elif url.startswith("postgresql://"):
                url = url.replace("postgresql://", "postgresql+psycopg2://", 1)
            
            if "ssl=" in url and "sslmode=" not in url:
                url = url.replace("ssl=", "sslmode=")
            self.DATABASE_URL_SYNC = url
        elif self.DATABASE_URL_SYNC:
            v = self.DATABASE_URL_SYNC
            if v.startswith("postgres://"):
                v = v.replace("postgres://", "postgresql+psycopg2://", 1)
            elif v.startswith("postgresql://"):
                v = v.replace("postgresql://", "postgresql+psycopg2://", 1)
            if "ssl=" in v and "sslmode=" not in v:
                v = v.replace("ssl=", "sslmode=")
            self.DATABASE_URL_SYNC = v
        return self

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


