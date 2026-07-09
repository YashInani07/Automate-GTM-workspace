from sqlalchemy import String, Text, Boolean, DateTime, ForeignKey, func
from sqlalchemy.orm import Mapped, mapped_column, relationship
from datetime import datetime
from typing import Optional, List
from app.models.base import Base


class OutreachSequence(Base):
    __tablename__ = "outreach_sequences"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    default_objective: Mapped[str] = mapped_column(
        String(500),
        nullable=False,
        default="Introduce our solutions and request a brief demo",
    )
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    steps: Mapped[List["SequenceStep"]] = relationship(
        "SequenceStep",
        back_populates="sequence",
        cascade="all, delete-orphan",
        order_by="SequenceStep.step_number",
    )
    enrollments: Mapped[List["SequenceEnrollment"]] = relationship(
        "SequenceEnrollment", back_populates="sequence", cascade="all, delete-orphan"
    )
