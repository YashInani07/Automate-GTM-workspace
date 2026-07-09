from sqlalchemy import String, DateTime, ForeignKey, func, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship
from datetime import datetime
from typing import Optional
from app.models.base import Base

class AuditHistory(Base):
    __tablename__ = "audit_history"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    company_id: Mapped[int] = mapped_column(ForeignKey("companies.id", ondelete="CASCADE"), nullable=False, index=True)
    action: Mapped[str] = mapped_column(String(100), nullable=False)  # e.g. "created", "enriched", "ai_analyzed", "email_drafted", "email_sent", "crm_synced"
    status: Mapped[str] = mapped_column(String(50), nullable=False)  # success, failed
    details: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)
    timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    company = relationship("Company", back_populates="audit_history")
