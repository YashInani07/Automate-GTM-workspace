from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import func, select
from app.models.company import Company
from app.models.email_draft import EmailDraft
from app.models.audit import AuditHistory
from app.schemas.analytics import AnalyticsResponse

async def get_analytics(db: AsyncSession) -> AnalyticsResponse:
    # 1. Companies Processed
    result_companies = await db.execute(select(func.count(Company.id)))
    companies_processed = result_companies.scalar() or 0

    # 2. Successful Enrichments
    result_success_enrich = await db.execute(
        select(func.count(AuditHistory.id)).where(
            AuditHistory.action == "enriched",
            AuditHistory.status == "success"
        )
    )
    successful_enrichments = result_success_enrich.scalar() or 0

    # 3. Failed Enrichments
    result_fail_enrich = await db.execute(
        select(func.count(AuditHistory.id)).where(
            AuditHistory.action == "enriched",
            AuditHistory.status == "failed"
        )
    )
    failed_enrichments = result_fail_enrich.scalar() or 0

    # 4. Emails Generated
    result_emails = await db.execute(select(func.count(EmailDraft.id)))
    emails_generated = result_emails.scalar() or 0

    # 5. Emails Sent
    result_sent = await db.execute(select(func.count(EmailDraft.id)).where(EmailDraft.status == "sent"))
    emails_sent = result_sent.scalar() or 0

    # 6. Average processing time (extract epoch for PostgreSQL compatible datetime math)
    subq = (
        select(
            AuditHistory.company_id,
            func.min(AuditHistory.timestamp).label("start_time"),
            func.max(AuditHistory.timestamp).label("end_time")
        )
        .group_by(AuditHistory.company_id)
        .subquery()
    )
    time_diff_q = select(
        func.avg(
            func.extract("epoch", subq.c.end_time) - func.extract("epoch", subq.c.start_time)
        )
    )
    result_time = await db.execute(time_diff_q)
    avg_processing_time = result_time.scalar() or 0.0

    return AnalyticsResponse(
        companies_processed=companies_processed,
        successful_enrichments=successful_enrichments,
        failed_enrichments=failed_enrichments,
        emails_generated=emails_generated,
        emails_sent=emails_sent,
        average_processing_time_seconds=float(avg_processing_time)
    )
