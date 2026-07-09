from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db
from app.connectors.registry import registry as connector_registry
from app.services.pipeline import run_enrichment_pipeline
import app.crud as crud
import app.schemas as schemas

router = APIRouter()

@router.post("/{company_id}/enrich", status_code=status.HTTP_202_ACCEPTED)
async def trigger_enrichment(
    company_id: int,
    background_tasks: BackgroundTasks,
    request: schemas.EmailSendRequest,
    connector: str = Query("jina", description="The connector to use: 'jina' or 'website'"),
    db: AsyncSession = Depends(get_db)
):
    company = await crud.get_company(db, company_id)
    if not company:
        raise HTTPException(status_code=404, detail="Company not found")

    if connector not in connector_registry.list_connectors():
        raise HTTPException(
            status_code=400,
            detail=f"Connector '{connector}' is not registered. Choose from: {connector_registry.list_connectors()}"
        )

    background_tasks.add_task(
        run_enrichment_pipeline,
        company_id=company_id,
        connector_name=connector,
        outreach_objective=request.outreach_objective,
        draft_only=request.draft_only,
        additional_urls=request.additional_urls,
        sequence_id=request.sequence_id,
        contact_email=request.contact_email
    )

    return {
        "message": "Enrichment and outreach pipeline triggered successfully.",
        "company_id": company_id,
        "connector": connector,
        "status": "processing"
    }
