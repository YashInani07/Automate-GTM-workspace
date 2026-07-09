from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from typing import List
from app.models.crm_sync import CRMSync

async def create_crm_sync(
    db: AsyncSession,
    company_id: int,
    provider: str,
    status: str,
    response_payload: dict = None,
    error_message: str = None
) -> CRMSync:
    db_obj = CRMSync(
        company_id=company_id,
        provider=provider,
        status=status,
        response_payload=response_payload,
        error_message=error_message
    )
    db.add(db_obj)
    await db.commit()
    await db.refresh(db_obj)
    return db_obj

async def get_crm_syncs_by_company(db: AsyncSession, company_id: int) -> List[CRMSync]:
    result = await db.execute(select(CRMSync).where(CRMSync.company_id == company_id))
    return result.scalars().all()
