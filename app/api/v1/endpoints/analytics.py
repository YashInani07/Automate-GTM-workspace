from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db
import app.crud as crud
import app.schemas as schemas

router = APIRouter()

@router.get("", response_model=schemas.AnalyticsResponse)
async def get_analytics(db: AsyncSession = Depends(get_db)):
    analytics = await crud.get_analytics(db)
    return analytics
