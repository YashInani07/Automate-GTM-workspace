from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List
from app.core.database import get_db
import app.crud as crud
import app.schemas as schemas

router = APIRouter()

@router.get("", response_model=List[schemas.CompanyResponse])
async def list_companies(
    skip: int = 0, limit: int = 100, db: AsyncSession = Depends(get_db)
):
    companies = await crud.get_companies(db, skip=skip, limit=limit)
    return companies

@router.post("", response_model=schemas.CompanyResponse, status_code=status.HTTP_201_CREATED)
async def create_company(
    company_in: schemas.CompanyCreate, db: AsyncSession = Depends(get_db)
):
    db_company = await crud.get_company_by_domain(db, domain=company_in.domain)
    if db_company:
        raise HTTPException(
            status_code=400,
            detail=f"Company with domain '{company_in.domain}' already exists."
        )
    company = await crud.create_company(db, obj_in=company_in)
    return company

@router.get("/{company_id}", response_model=schemas.CompanyResponse)
async def get_company(company_id: int, db: AsyncSession = Depends(get_db)):
    company = await crud.get_company(db, company_id)
    if not company:
        raise HTTPException(status_code=404, detail="Company not found")
    return company

@router.put("/{company_id}", response_model=schemas.CompanyResponse)
async def update_company(
    company_id: int, company_in: schemas.CompanyUpdate, db: AsyncSession = Depends(get_db)
):
    company = await crud.update_company(db, company_id, obj_in=company_in)
    if not company:
        raise HTTPException(status_code=404, detail="Company not found")
    return company

@router.delete("/{company_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_company(company_id: int, db: AsyncSession = Depends(get_db)):
    success = await crud.delete_company(db, company_id)
    if not success:
        raise HTTPException(status_code=404, detail="Company not found")
    return None

@router.get("/{company_id}/audit")
async def get_company_audit(company_id: int, db: AsyncSession = Depends(get_db)):
    # Check if company exists
    company = await crud.get_company(db, company_id)
    if not company:
        raise HTTPException(status_code=404, detail="Company not found")
    history = await crud.get_audit_history_by_company(db, company_id)
    return history

@router.get("/{company_id}/results")
async def get_company_results(company_id: int, db: AsyncSession = Depends(get_db)):
    company = await crud.get_company(db, company_id)
    if not company:
        raise HTTPException(status_code=404, detail="Company not found")
    
    analyses = await crud.get_ai_analyses_by_company(db, company_id)
    emails = await crud.get_email_drafts_by_company(db, company_id)
    
    latest_analysis = analyses[0] if analyses else None
    latest_email = emails[0] if emails else None
    
    return {
        "analysis": latest_analysis,
        "email": latest_email
    }
