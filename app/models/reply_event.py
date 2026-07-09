from sqlalchemy import String, Text, DateTime, ForeignKey, func
from sqlalchemy.orm import Mapped, mapped_column, relationship
from datetime import datetime
from typing import Optional
from app.models.base import Base


class ReplyEvent(Base):
    __tablename__ = "reply_events"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    enrollment_id: Mapped[int] = mapped_column(
        ForeignKey("sequence_enrollments.id", ondelete="CASCADE"), nullable=False, index=True
    )
    from_email: Mapped[str] = mapped_column(String(255), nullable=False)
    subject: Mapped[str] = mapped_column(String(500), nullable=False, default="")
    snippet: Mapped[str] = mapped_column(Text, nullable=False, default="")
    in_reply_to: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    raw_headers: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    detected_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    enrollment: Mapped["SequenceEnrollment"] = relationship(
        "SequenceEnrollment", back_populates="reply_events"
    )
