from fastapi import APIRouter
from app.api.v1.endpoints import health, companies, enrichment, analytics, sources, sequences

api_router = APIRouter()

api_router.include_router(health.router, prefix="/health", tags=["health"])
api_router.include_router(companies.router, prefix="/companies", tags=["companies"])
api_router.include_router(enrichment.router, prefix="/companies", tags=["enrichment"])
api_router.include_router(analytics.router, prefix="/analytics", tags=["analytics"])
api_router.include_router(sources.router, prefix="/companies", tags=["sources"])
api_router.include_router(sequences.router, prefix="/sequences", tags=["sequences"])
api_router.include_router(sequences.companies_router, prefix="/companies", tags=["companies"])
api_router.include_router(sequences.enrollments_router, prefix="/enrollments", tags=["enrollments"])
api_router.include_router(sequences.messages_router, prefix="/messages", tags=["messages"])

