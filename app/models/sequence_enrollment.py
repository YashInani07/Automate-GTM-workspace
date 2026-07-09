from sqlalchemy import String, Integer, DateTime, ForeignKey, func
from sqlalchemy.orm import Mapped, mapped_column, relationship
from datetime import datetime
from typing import Optional, List
from app.models.base import Base


class SequenceEnrollment(Base):
    __tablename__ = "sequence_enrollments"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    company_id: Mapped[int] = mapped_column(
        ForeignKey("companies.id", ondelete="CASCADE"), nullable=False, index=True
    )
    sequence_id: Mapped[int] = mapped_column(
        ForeignKey("outreach_sequences.id", ondelete="CASCADE"), nullable=False, index=True
    )
    contact_email: Mapped[str] = mapped_column(String(255), nullable=False)
    status: Mapped[str] = mapped_column(
        String(50), nullable=False, default="active"
    )  # active, paused, completed, replied, cancelled
    current_step: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    enrolled_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    company: Mapped["Company"] = relationship("Company", back_populates="enrollments")
    sequence: Mapped["OutreachSequence"] = relationship("OutreachSequence", back_populates="enrollments")
    messages: Mapped[List["OutreachMessage"]] = relationship(
        "OutreachMessage",
        back_populates="enrollment",
        cascade="all, delete-orphan",
        order_by="OutreachMessage.step_number",
    )
    reply_events: Mapped[List["ReplyEvent"]] = relationship(
        "ReplyEvent", back_populates="enrollment", cascade="all, delete-orphan"
    )
