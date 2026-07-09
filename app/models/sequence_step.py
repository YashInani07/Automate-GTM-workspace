from sqlalchemy import String, Text, Integer, Boolean, DateTime, ForeignKey, func
from sqlalchemy.orm import Mapped, mapped_column, relationship
from datetime import datetime
from typing import Optional, List
from app.models.base import Base


class SequenceStep(Base):
    __tablename__ = "sequence_steps"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    sequence_id: Mapped[int] = mapped_column(
        ForeignKey("outreach_sequences.id", ondelete="CASCADE"), nullable=False, index=True
    )
    step_number: Mapped[int] = mapped_column(Integer, nullable=False)
    delay_days: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    channel: Mapped[str] = mapped_column(String(50), nullable=False, default="email")
    prompt_template: Mapped[str] = mapped_column(Text, nullable=False)
    auto_send: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    sequence: Mapped["OutreachSequence"] = relationship("OutreachSequence", back_populates="steps")
    messages: Mapped[List["OutreachMessage"]] = relationship(
        "OutreachMessage", back_populates="step"
    )
