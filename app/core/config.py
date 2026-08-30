import os
import re
from typing import Optional
from pydantic import field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

def clean_asyncpg_url(url_str: str) -> str:
    if not isinstance(url_str, str):
        return url_str
    
    if url_str.startswith("postgres://"):
        url_str = url_str.replace("postgres://", "postgresql+asyncpg://", 1)
    elif url_str.startswith("postgresql://"):
        url_str = url_str.replace("postgresql://", "postgresql+asyncpg://", 1)
    elif not url_str.startswith("postgresql+asyncpg://"):
        url_str = "postgresql+asyncpg://" + url_str.split("://", 1)[-1]
        
    # Replace sslmode= with ssl= for asyncpg
    if "sslmode=" in url_str:
        url_str = url_str.replace("sslmode=", "ssl=")

    # Strip channel_binding parameter as asyncpg does not accept channel_binding
    url_str = re.sub(r'([?&])channel_binding=[^&]*&?', r'\1', url_str)
    url_str = url_str.rstrip('?').rstrip('&')
    return url_str

def clean_psycopg2_url(url_str: str) -> str:
    if not isinstance(url_str, str):
        return url_str
    
    if url_str.startswith("postgres://"):
        url_str = url_str.replace("postgres://", "postgresql+psycopg2://", 1)
    elif url_str.startswith("postgresql://"):
        url_str = url_str.replace("postgresql://", "postgresql+psycopg2://", 1)
    elif url_str.startswith("postgresql+asyncpg://"):
        url_str = url_str.replace("postgresql+asyncpg://", "postgresql+psycopg2://", 1)
    elif not url_str.startswith("postgresql+psycopg2://"):
        url_str = "postgresql+psycopg2://" + url_str.split("://", 1)[-1]

    if "ssl=" in url_str and "sslmode=" not in url_str:
        url_str = url_str.replace("ssl=", "sslmode=")
    return url_str

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
        return clean_asyncpg_url(v)

    @model_validator(mode="after")
    def assemble_sync_db_url(self) -> "Settings":
        # Always use DATABASE_URL to derive DATABASE_URL_SYNC if DATABASE_URL_SYNC is missing or points to old database
        if not self.DATABASE_URL_SYNC or "gtm-db" in self.DATABASE_URL_SYNC or "dpg-" in self.DATABASE_URL_SYNC:
            self.DATABASE_URL_SYNC = clean_psycopg2_url(self.DATABASE_URL)
        else:
            self.DATABASE_URL_SYNC = clean_psycopg2_url(self.DATABASE_URL_SYNC)
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



