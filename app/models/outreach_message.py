from sqlalchemy import String, Text, Integer, DateTime, ForeignKey, func
from sqlalchemy.orm import Mapped, mapped_column, relationship
from datetime import datetime
from typing import Optional
from app.models.base import Base


class OutreachMessage(Base):
    __tablename__ = "outreach_messages"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    enrollment_id: Mapped[int] = mapped_column(
        ForeignKey("sequence_enrollments.id", ondelete="CASCADE"), nullable=False, index=True
    )
    step_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("sequence_steps.id", ondelete="SET NULL"), nullable=True
    )
    step_number: Mapped[int] = mapped_column(Integer, nullable=False)
    subject: Mapped[str] = mapped_column(String(255), nullable=False, default="")
    body: Mapped[str] = mapped_column(Text, nullable=False, default="")
    cta: Mapped[str] = mapped_column(String(255), nullable=False, default="")
    recipient_email: Mapped[str] = mapped_column(String(255), nullable=False)
    status: Mapped[str] = mapped_column(
        String(50), nullable=False, default="scheduled"
    )  # scheduled, draft, sending, sent, failed, cancelled
    scheduled_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    sent_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    message_id: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    celery_task_id: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    enrollment: Mapped["SequenceEnrollment"] = relationship(
        "SequenceEnrollment", back_populates="messages"
    )
    step: Mapped[Optional["SequenceStep"]] = relationship("SequenceStep", back_populates="messages")
