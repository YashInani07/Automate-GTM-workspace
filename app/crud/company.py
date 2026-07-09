from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from typing import List, Optional
from app.models.company import Company
from app.schemas.company import CompanyCreate, CompanyUpdate

async def get_company(db: AsyncSession, company_id: int) -> Optional[Company]:
    result = await db.execute(select(Company).where(Company.id == company_id))
    return result.scalars().first()

async def get_company_by_domain(db: AsyncSession, domain: str) -> Optional[Company]:
    result = await db.execute(select(Company).where(Company.domain == domain))
    return result.scalars().first()

async def get_companies(db: AsyncSession, skip: int = 0, limit: int = 100) -> List[Company]:
    result = await db.execute(select(Company).offset(skip).limit(limit))
    return result.scalars().all()

async def create_company(db: AsyncSession, obj_in: CompanyCreate) -> Company:
    db_obj = Company(
        name=obj_in.name,
        domain=obj_in.domain
    )
    db.add(db_obj)
    await db.commit()
    await db.refresh(db_obj)
    return db_obj

async def update_company(db: AsyncSession, company_id: int, obj_in: CompanyUpdate) -> Optional[Company]:
    db_obj = await get_company(db, company_id)
    if not db_obj:
        return None
    update_data = obj_in.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(db_obj, field, value)
    db.add(db_obj)
    await db.commit()
    await db.refresh(db_obj)
    return db_obj

async def delete_company(db: AsyncSession, company_id: int) -> bool:
    db_obj = await get_company(db, company_id)
    if not db_obj:
        return False
    await db.delete(db_obj)
    await db.commit()
    return True
