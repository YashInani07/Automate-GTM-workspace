from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from typing import List
from app.models.ai_analysis import AIAnalysis

async def create_ai_analysis(
    db: AsyncSession,
    company_id: int,
    summary: str,
    pain_points: List[str],
    buying_signals: List[str],
    outreach_context: str
) -> AIAnalysis:
    db_obj = AIAnalysis(
        company_id=company_id,
        summary=summary,
        pain_points=pain_points,
        buying_signals=buying_signals,
        outreach_context=outreach_context
    )
    db.add(db_obj)
    await db.commit()
    await db.refresh(db_obj)
    return db_obj

async def get_ai_analyses_by_company(db: AsyncSession, company_id: int) -> List[AIAnalysis]:
    result = await db.execute(
        select(AIAnalysis)
        .where(AIAnalysis.company_id == company_id)
        .order_by(AIAnalysis.created_at.desc())
    )
    return result.scalars().all()
