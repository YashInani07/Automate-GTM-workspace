from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List
from datetime import datetime, timezone

from app.core.database import get_db
from app.core.config import settings
from app.worker.celery_app import celery_app
from app.services.sequence_engine import sequence_engine
from app.models.outreach_message import OutreachMessage
from app.models.sequence_enrollment import SequenceEnrollment
import app.crud as crud
import app.schemas as schemas
from sqlalchemy.future import select

router = APIRouter()
companies_router = APIRouter()
enrollments_router = APIRouter()
messages_router = APIRouter()


# -------------------- SEQUENCE CRUD --------------------

@router.post("", response_model=schemas.SequenceResponse, status_code=status.HTTP_201_CREATED)
async def create_sequence_endpoint(
    sequence_in: schemas.SequenceCreate, db: AsyncSession = Depends(get_db)
):
    return await crud.create_sequence(db, obj_in=sequence_in)


@router.get("", response_model=List[schemas.SequenceResponse])
async def list_sequences_endpoint(
    skip: int = 0, limit: int = 100, db: AsyncSession = Depends(get_db)
):
    return await crud.get_sequences(db, skip=skip, limit=limit)


@router.get("/{sequence_id}", response_model=schemas.SequenceResponse)
async def get_sequence_endpoint(
    sequence_id: int, db: AsyncSession = Depends(get_db)
):
    seq = await crud.get_sequence(db, sequence_id)
    if not seq:
        raise HTTPException(status_code=404, detail="Sequence not found")
    return seq


@router.put("/{sequence_id}", response_model=schemas.SequenceResponse)
async def update_sequence_endpoint(
    sequence_id: int, sequence_in: schemas.SequenceUpdate, db: AsyncSession = Depends(get_db)
):
    seq = await crud.update_sequence(db, sequence_id, obj_in=sequence_in)
    if not seq:
        raise HTTPException(status_code=404, detail="Sequence not found")
    return seq


@router.delete("/{sequence_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_sequence_endpoint(
    sequence_id: int, db: AsyncSession = Depends(get_db)
):
    success = await crud.delete_sequence(db, sequence_id)
    if not success:
        raise HTTPException(status_code=404, detail="Sequence not found")
    return None


# -------------------- COMPANY ENROLLMENTS --------------------

@companies_router.post("/{company_id}/enroll", response_model=schemas.EnrollmentResponse)
async def enroll_company_endpoint(
    company_id: int, enroll_in: schemas.EnrollmentCreate, db: AsyncSession = Depends(get_db)
):
    try:
        enrollment = await sequence_engine.enroll_company(
            db=db,
            company_id=company_id,
            sequence_id=enroll_in.sequence_id,
            contact_email=enroll_in.contact_email,
            start_immediately=enroll_in.start_immediately
        )
        return enrollment
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@companies_router.get("/{company_id}/enrollments", response_model=List[schemas.EnrollmentResponse])
async def list_company_enrollments_endpoint(
    company_id: int, db: AsyncSession = Depends(get_db)
):
    company = await crud.get_company(db, company_id)
    if not company:
        raise HTTPException(status_code=404, detail="Company not found")
    return await crud.get_enrollments_by_company(db, company_id=company_id)


# -------------------- ENROLLMENT ACTIONS --------------------

@enrollments_router.post("/{enrollment_id}/pause", response_model=schemas.EnrollmentResponse)
async def pause_enrollment_endpoint(
    enrollment_id: int, db: AsyncSession = Depends(get_db)
):
    enrollment = await crud.get_enrollment(db, enrollment_id)
    if not enrollment:
        raise HTTPException(status_code=404, detail="Enrollment not found")
    
    updated = await crud.update_enrollment_status(db, enrollment_id, "paused")
    
    # Cancel pending scheduled messages
    for msg in enrollment.messages:
        if msg.status == "scheduled":
            msg.status = "cancelled"
            db.add(msg)
            if msg.celery_task_id:
                try:
                    celery_app.control.revoke(msg.celery_task_id, terminate=True)
                except Exception as e:
                    # Ignore or log warning if Celery not fully running
                    pass
                
    await crud.create_audit_log(db, enrollment.company_id, "sequence_paused", "success", {
        "enrollment_id": enrollment.id
    })
    await db.commit()
    await db.refresh(updated)
    return updated


@enrollments_router.post("/{enrollment_id}/resume", response_model=schemas.EnrollmentResponse)
async def resume_enrollment_endpoint(
    enrollment_id: int, db: AsyncSession = Depends(get_db)
):
    enrollment = await crud.get_enrollment(db, enrollment_id)
    if not enrollment:
        raise HTTPException(status_code=404, detail="Enrollment not found")
    if enrollment.status != "paused":
        raise HTTPException(status_code=400, detail="Only paused enrollments can be resumed")

    enrollment.status = "active"
    db.add(enrollment)

    # Reschedule the current step if it was paused/cancelled/drafted
    msg_result = await db.execute(
        select(OutreachMessage)
        .where(OutreachMessage.enrollment_id == enrollment_id)
        .where(OutreachMessage.step_number == enrollment.current_step)
    )
    msg = msg_result.scalars().first()

    if msg and msg.status in ("cancelled", "scheduled", "failed", "draft"):
        msg.status = "scheduled"
        msg.scheduled_at = datetime.now(timezone.utc)
        try:
            task = celery_app.send_task(
                "app.worker.tasks.execute_outreach_step",
                args=[msg.id]
            )
            msg.celery_task_id = task.id
        except Exception:
            pass
        db.add(msg)
        await crud.create_audit_log(db, enrollment.company_id, "sequence_resumed", "success", {
            "enrollment_id": enrollment.id,
            "rescheduled_message_id": msg.id
        })
    else:
        await crud.create_audit_log(db, enrollment.company_id, "sequence_resumed", "success", {
            "enrollment_id": enrollment.id
        })
        await sequence_engine.schedule_next_step(db, enrollment_id)

    await db.commit()
    await db.refresh(enrollment)
    return enrollment


@enrollments_router.post("/{enrollment_id}/cancel", response_model=schemas.EnrollmentResponse)
async def cancel_enrollment_endpoint(
    enrollment_id: int, db: AsyncSession = Depends(get_db)
):
    enrollment = await crud.get_enrollment(db, enrollment_id)
    if not enrollment:
        raise HTTPException(status_code=404, detail="Enrollment not found")
    
    updated = await crud.update_enrollment_status(db, enrollment_id, "cancelled")
    
    # Cancel pending scheduled messages
    for msg in enrollment.messages:
        if msg.status == "scheduled":
            msg.status = "cancelled"
            db.add(msg)
            if msg.celery_task_id:
                try:
                    celery_app.control.revoke(msg.celery_task_id, terminate=True)
                except Exception:
                    pass
                
    await crud.create_audit_log(db, enrollment.company_id, "sequence_cancelled", "success", {
        "enrollment_id": enrollment.id
    })
    await db.commit()
    await db.refresh(updated)
    return updated


# -------------------- MESSAGE ACTIONS --------------------

@messages_router.post("/{message_id}/send", response_model=schemas.OutreachMessageResponse)
async def send_message_endpoint(
    message_id: int, db: AsyncSession = Depends(get_db)
):
    message = await crud.get_outreach_message(db, message_id)
    if not message:
        raise HTTPException(status_code=404, detail="Message not found")
    
    # We will trigger the execution step with manual override
    await db.commit()
    
    try:
        await sequence_engine.execute_step(message_id, manual_send=True)
        # Fetch updated message from db
        async with get_db() as new_db:
            updated = await crud.get_outreach_message(new_db, message_id)
            if not updated:
                raise HTTPException(status_code=404, detail="Message not found after send")
            return updated
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
