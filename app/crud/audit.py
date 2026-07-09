from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from typing import List
from app.models.audit import AuditHistory

async def create_audit_log(
    db: AsyncSession,
    company_id: int,
    action: str,
    status: str,
    details: dict = None
) -> AuditHistory:
    db_obj = AuditHistory(
        company_id=company_id,
        action=action,
        status=status,
        details=details
    )
    db.add(db_obj)
    await db.commit()
    await db.refresh(db_obj)
    return db_obj

async def get_audit_history_by_company(db: AsyncSession, company_id: int) -> List[AuditHistory]:
    result = await db.execute(
        select(AuditHistory)
        .where(AuditHistory.company_id == company_id)
        .order_by(AuditHistory.timestamp.asc())
    )
    return result.scalars().all()
