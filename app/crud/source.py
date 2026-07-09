from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from typing import List
from app.models.source import CompanySource
from app.schemas.source import SourceCreate

async def get_company_sources(db: AsyncSession, company_id: int) -> List[CompanySource]:
    result = await db.execute(
        select(CompanySource)
        .where(CompanySource.company_id == company_id)
        .order_by(CompanySource.created_at.asc())
    )
    return result.scalars().all()

async def create_company_source(db: AsyncSession, company_id: int, obj_in: SourceCreate) -> CompanySource:
    db_obj = CompanySource(
        company_id=company_id,
        url=obj_in.url
    )
    db.add(db_obj)
    await db.commit()
    await db.refresh(db_obj)
    return db_obj

async def delete_company_source(db: AsyncSession, source_id: int) -> bool:
    result = await db.execute(select(CompanySource).where(CompanySource.id == source_id))
    db_obj = result.scalars().first()
    if not db_obj:
        return False
    await db.delete(db_obj)
    await db.commit()
    return True
