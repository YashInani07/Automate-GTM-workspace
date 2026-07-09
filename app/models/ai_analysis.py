from sqlalchemy import Text, DateTime, ForeignKey, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship
from datetime import datetime
from app.models.base import Base

class AIAnalysis(Base):
    __tablename__ = "ai_analyses"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    company_id: Mapped[int] = mapped_column(ForeignKey("companies.id", ondelete="CASCADE"), nullable=False, index=True)
    summary: Mapped[str] = mapped_column(Text, nullable=False)
    pain_points: Mapped[list] = mapped_column(JSONB, nullable=False)  # JSON list of strings
    buying_signals: Mapped[list] = mapped_column(JSONB, nullable=False)  # JSON list of strings
    outreach_context: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    company = relationship("Company", back_populates="ai_analyses")
