from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from typing import List
from app.models.enrichment import CompanyEnrichment

async def create_enrichment(
    db: AsyncSession, company_id: int, connector: str, raw_data: dict, clean_data: dict
) -> CompanyEnrichment:
    db_obj = CompanyEnrichment(
        company_id=company_id,
        connector=connector,
        raw_data=raw_data,
        clean_data=clean_data
    )
    db.add(db_obj)
    await db.commit()
    await db.refresh(db_obj)
    return db_obj

async def get_enrichments_by_company(db: AsyncSession, company_id: int) -> List[CompanyEnrichment]:
    result = await db.execute(select(CompanyEnrichment).where(CompanyEnrichment.company_id == company_id))
    return result.scalars().all()
