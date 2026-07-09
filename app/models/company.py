from sqlalchemy import String, Text, DateTime, func
from sqlalchemy.orm import Mapped, mapped_column, relationship
from datetime import datetime
from typing import Optional
from app.models.base import Base

class Company(Base):
    __tablename__ = "companies"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    domain: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    industry: Mapped[str] = mapped_column(String(255), nullable=True)
    notes: Mapped[str] = mapped_column(Text, nullable=True)
    contact_email: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    # Relationships
    enrichments = relationship("CompanyEnrichment", back_populates="company", cascade="all, delete-orphan")
    ai_analyses = relationship("AIAnalysis", back_populates="company", cascade="all, delete-orphan")
    email_drafts = relationship("EmailDraft", back_populates="company", cascade="all, delete-orphan")
    crm_syncs = relationship("CRMSync", back_populates="company", cascade="all, delete-orphan")
    audit_history = relationship("AuditHistory", back_populates="company", cascade="all, delete-orphan")
    sources = relationship("CompanySource", back_populates="company", cascade="all, delete-orphan")
    enrollments = relationship("SequenceEnrollment", back_populates="company", cascade="all, delete-orphan")
