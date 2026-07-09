from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.orm import selectinload
from typing import List, Optional
from datetime import datetime, timezone

from app.models.outreach_sequence import OutreachSequence
from app.models.sequence_step import SequenceStep
from app.models.sequence_enrollment import SequenceEnrollment
from app.models.outreach_message import OutreachMessage
from app.models.reply_event import ReplyEvent
from app.schemas.sequence import SequenceCreate, SequenceUpdate


async def get_sequence(db: AsyncSession, sequence_id: int) -> Optional[OutreachSequence]:
    result = await db.execute(
        select(OutreachSequence)
        .where(OutreachSequence.id == sequence_id)
        .options(selectinload(OutreachSequence.steps))
    )
    return result.scalars().first()


async def get_sequences(db: AsyncSession, skip: int = 0, limit: int = 100) -> List[OutreachSequence]:
    result = await db.execute(
        select(OutreachSequence)
        .options(selectinload(OutreachSequence.steps))
        .offset(skip)
        .limit(limit)
    )
    return result.scalars().all()


async def create_sequence(db: AsyncSession, obj_in: SequenceCreate) -> OutreachSequence:
    db_obj = OutreachSequence(
        name=obj_in.name,
        description=obj_in.description,
        default_objective=obj_in.default_objective,
        is_active=obj_in.is_active
    )
    db.add(db_obj)
    await db.commit()
    await db.refresh(db_obj)

    for step_in in obj_in.steps:
        db_step = SequenceStep(
            sequence_id=db_obj.id,
            step_number=step_in.step_number,
            delay_days=step_in.delay_days,
            channel=step_in.channel,
            prompt_template=step_in.prompt_template,
            auto_send=step_in.auto_send
        )
        db.add(db_step)
    await db.commit()
    await db.refresh(db_obj)
    return db_obj


async def update_sequence(db: AsyncSession, sequence_id: int, obj_in: SequenceUpdate) -> Optional[OutreachSequence]:
    db_obj = await get_sequence(db, sequence_id)
    if not db_obj:
        return None
    
    update_data = obj_in.model_dump(exclude_unset=True)
    steps_data = update_data.pop("steps", None)
    
    for field, value in update_data.items():
        setattr(db_obj, field, value)
    db.add(db_obj)
    
    if steps_data is not None:
        # Load and delete existing steps
        existing_steps_result = await db.execute(
            select(SequenceStep).where(SequenceStep.sequence_id == sequence_id)
        )
        existing_steps = existing_steps_result.scalars().all()
        for step in existing_steps:
            await db.delete(step)
        
        # Add new steps
        for step_in in steps_data:
            db_step = SequenceStep(
                sequence_id=db_obj.id,
                step_number=step_in.step_number if hasattr(step_in, "step_number") else step_in["step_number"],
                delay_days=step_in.delay_days if hasattr(step_in, "delay_days") else step_in["delay_days"],
                channel=step_in.channel if hasattr(step_in, "channel") else step_in["channel"],
                prompt_template=step_in.prompt_template if hasattr(step_in, "prompt_template") else step_in["prompt_template"],
                auto_send=step_in.auto_send if hasattr(step_in, "auto_send") else step_in["auto_send"]
            )
            db.add(db_step)
            
    await db.commit()
    await db.refresh(db_obj)
    return db_obj


async def delete_sequence(db: AsyncSession, sequence_id: int) -> bool:
    db_obj = await get_sequence(db, sequence_id)
    if not db_obj:
        return False
    await db.delete(db_obj)
    await db.commit()
    return True


async def get_enrollment(db: AsyncSession, enrollment_id: int) -> Optional[SequenceEnrollment]:
    result = await db.execute(
        select(SequenceEnrollment)
        .where(SequenceEnrollment.id == enrollment_id)
        .options(
            selectinload(SequenceEnrollment.messages),
            selectinload(SequenceEnrollment.reply_events)
        )
    )
    return result.scalars().first()


async def get_enrollments_by_company(db: AsyncSession, company_id: int) -> List[SequenceEnrollment]:
    result = await db.execute(
        select(SequenceEnrollment)
        .where(SequenceEnrollment.company_id == company_id)
        .options(
            selectinload(SequenceEnrollment.messages),
            selectinload(SequenceEnrollment.reply_events)
        )
        .order_by(SequenceEnrollment.enrolled_at.desc())
    )
    return result.scalars().all()


async def get_active_enrollment_by_company(db: AsyncSession, company_id: int) -> Optional[SequenceEnrollment]:
    result = await db.execute(
        select(SequenceEnrollment)
        .where(SequenceEnrollment.company_id == company_id)
        .where(SequenceEnrollment.status == "active")
        .options(
            selectinload(SequenceEnrollment.messages),
            selectinload(SequenceEnrollment.reply_events)
        )
    )
    return result.scalars().first()


async def create_enrollment(db: AsyncSession, company_id: int, sequence_id: int, contact_email: str) -> SequenceEnrollment:
    db_obj = SequenceEnrollment(
        company_id=company_id,
        sequence_id=sequence_id,
        contact_email=contact_email,
        status="active",
        current_step=1
    )
    db.add(db_obj)
    await db.commit()
    return await get_enrollment(db, db_obj.id)


async def update_enrollment_status(db: AsyncSession, enrollment_id: int, status: str) -> Optional[SequenceEnrollment]:
    db_obj = await get_enrollment(db, enrollment_id)
    if not db_obj:
        return None
    db_obj.status = status
    if status in ("completed", "cancelled", "replied"):
        db_obj.completed_at = datetime.now(timezone.utc)
    db.add(db_obj)
    await db.commit()
    return await get_enrollment(db, enrollment_id)


async def get_outreach_message(db: AsyncSession, message_id: int) -> Optional[OutreachMessage]:
    result = await db.execute(
        select(OutreachMessage)
        .where(OutreachMessage.id == message_id)
        .options(selectinload(OutreachMessage.step))
    )
    return result.scalars().first()


async def create_outreach_message(
    db: AsyncSession,
    enrollment_id: int,
    step_id: Optional[int],
    step_number: int,
    recipient_email: str,
    status: str,
    scheduled_at: Optional[datetime],
    subject: str = "",
    body: str = "",
    cta: str = ""
) -> OutreachMessage:
    db_obj = OutreachMessage(
        enrollment_id=enrollment_id,
        step_id=step_id,
        step_number=step_number,
        recipient_email=recipient_email,
        status=status,
        scheduled_at=scheduled_at,
        subject=subject,
        body=body,
        cta=cta
    )
    db.add(db_obj)
    await db.commit()
    await db.refresh(db_obj)
    return db_obj


async def update_outreach_message(db: AsyncSession, message_id: int, **kwargs) -> Optional[OutreachMessage]:
    db_obj = await get_outreach_message(db, message_id)
    if not db_obj:
        return None
    for field, value in kwargs.items():
        setattr(db_obj, field, value)
    db.add(db_obj)
    await db.commit()
    await db.refresh(db_obj)
    return db_obj


async def create_reply_event(
    db: AsyncSession,
    enrollment_id: int,
    from_email: str,
    subject: str,
    snippet: str,
    in_reply_to: Optional[str] = None,
    raw_headers: Optional[str] = None
) -> ReplyEvent:
    db_obj = ReplyEvent(
        enrollment_id=enrollment_id,
        from_email=from_email,
        subject=subject,
        snippet=snippet,
        in_reply_to=in_reply_to,
        raw_headers=raw_headers
    )
    db.add(db_obj)
    await db.commit()
    await db.refresh(db_obj)
    return db_obj
