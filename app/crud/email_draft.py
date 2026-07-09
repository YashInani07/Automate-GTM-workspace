from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from datetime import datetime
from typing import List, Optional
from app.models.email_draft import EmailDraft

async def create_email_draft(
    db: AsyncSession,
    company_id: int,
    subject: str,
    body: str,
    cta: str,
    outreach_objective: str,
    status: str = "draft",
    error_message: str = None
) -> EmailDraft:
    db_obj = EmailDraft(
        company_id=company_id,
        subject=subject,
        body=body,
        cta=cta,
        outreach_objective=outreach_objective,
        status=status,
        error_message=error_message
    )
    db.add(db_obj)
    await db.commit()
    await db.refresh(db_obj)
    return db_obj

async def update_email_draft_status(
    db: AsyncSession,
    draft_id: int,
    status: str,
    error_message: str = None,
    sent_at: datetime = None
) -> Optional[EmailDraft]:
    result = await db.execute(select(EmailDraft).where(EmailDraft.id == draft_id))
    db_obj = result.scalars().first()
    if not db_obj:
        return None
    db_obj.status = status
    db_obj.error_message = error_message
    db_obj.sent_at = sent_at
    db.add(db_obj)
    await db.commit()
    await db.refresh(db_obj)
    return db_obj

async def get_email_drafts_by_company(db: AsyncSession, company_id: int) -> List[EmailDraft]:
    result = await db.execute(
        select(EmailDraft)
        .where(EmailDraft.company_id == company_id)
        .order_by(EmailDraft.created_at.desc())
    )
    return result.scalars().all()
