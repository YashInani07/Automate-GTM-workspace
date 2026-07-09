from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List
from app.core.database import get_db
import app.crud as crud
import app.schemas as schemas

router = APIRouter()

@router.get("/{company_id}/sources", response_model=List[schemas.SourceResponse])
async def list_company_sources(company_id: int, db: AsyncSession = Depends(get_db)):
    company = await crud.get_company(db, company_id)
    if not company:
        raise HTTPException(status_code=404, detail="Company not found")
    sources = await crud.get_company_sources(db, company_id)
    return sources

@router.post("/{company_id}/sources", response_model=schemas.SourceResponse, status_code=status.HTTP_201_CREATED)
async def create_company_source(
    company_id: int, source_in: schemas.SourceCreate, db: AsyncSession = Depends(get_db)
):
    company = await crud.get_company(db, company_id)
    if not company:
        raise HTTPException(status_code=404, detail="Company not found")
    
    existing = await crud.get_company_sources(db, company_id)
    for src in existing:
        if src.url == source_in.url:
            raise HTTPException(status_code=400, detail="Source URL already exists for this company")
            
    source = await crud.create_company_source(db, company_id, obj_in=source_in)
    return source

@router.delete("/sources/{source_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_company_source(source_id: int, db: AsyncSession = Depends(get_db)):
    success = await crud.delete_company_source(db, source_id)
    if not success:
        raise HTTPException(status_code=404, detail="Source not found")
    return None
