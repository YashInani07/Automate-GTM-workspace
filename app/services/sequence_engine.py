import logging
from datetime import datetime, timezone, timedelta
from typing import Optional, List

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.orm import selectinload

from app.core.database import SessionLocal
from app.core.config import settings
from app.services.llm import llm_service
from app.services.email import gmail_service
from app.crm.registry import crm_registry
import app.crud as crud
from app.models.outreach_sequence import OutreachSequence
from app.models.sequence_step import SequenceStep
from app.models.sequence_enrollment import SequenceEnrollment
from app.models.outreach_message import OutreachMessage
from app.models.company import Company
from app.models.reply_event import ReplyEvent
from app.worker.celery_app import celery_app

logger = logging.getLogger(__name__)


class SequenceEngine:
    async def enroll_company(
        self,
        db: AsyncSession,
        company_id: int,
        sequence_id: int,
        contact_email: str,
        start_immediately: bool = True
    ) -> SequenceEnrollment:
        logger.info(f"Enrolling company {company_id} into sequence {sequence_id}")

        # 1. Verify sequence exists and is active
        sequence = await crud.get_sequence(db, sequence_id)
        if not sequence or not sequence.is_active:
            raise ValueError(f"Sequence ID {sequence_id} is not found or inactive.")

        # 2. Verify company exists and update contact_email
        company = await crud.get_company(db, company_id)
        if not company:
            raise ValueError(f"Company ID {company_id} not found.")

        company.contact_email = contact_email
        db.add(company)

        # 3. Check and cancel active enrollments
        active_enrollment = await crud.get_active_enrollment_by_company(db, company_id)
        if active_enrollment:
            logger.info(f"Cancelling active enrollment {active_enrollment.id} for company {company_id}")
            active_enrollment.status = "cancelled"
            active_enrollment.completed_at = datetime.now(timezone.utc)
            db.add(active_enrollment)
            
            # Cancel pending messages
            for msg in active_enrollment.messages:
                if msg.status == "scheduled":
                    msg.status = "cancelled"
                    db.add(msg)
                    if msg.celery_task_id:
                        try:
                            celery_app.control.revoke(msg.celery_task_id, terminate=True)
                        except Exception as e:
                            logger.warning(f"Failed to revoke task {msg.celery_task_id}: {e}")
            
            await crud.create_audit_log(db, company_id, "sequence_cancelled", "success", {
                "enrollment_id": active_enrollment.id,
                "reason": "New sequence enrolled"
            })

        # 4. Create new enrollment
        enrollment = await crud.create_enrollment(
            db, company_id=company_id, sequence_id=sequence_id, contact_email=contact_email
        )

        await crud.create_audit_log(db, company_id, "sequence_enrolled", "success", {
            "enrollment_id": enrollment.id,
            "sequence_name": sequence.name,
            "contact_email": contact_email
        })

        # 5. Fetch step 1
        step_1 = next((s for s in sequence.steps if s.step_number == 1), None)
        if not step_1:
            logger.warning(f"No Step 1 found in sequence {sequence_id}. Completing immediately.")
            enrollment.status = "completed"
            enrollment.completed_at = datetime.now(timezone.utc)
            db.add(enrollment)
            await db.commit()
            return enrollment

        # 6. Schedule step 1
        now = datetime.now(timezone.utc)
        delay = timedelta(days=step_1.delay_days) if not start_immediately else timedelta(seconds=0)
        scheduled_at = now + delay

        message = await crud.create_outreach_message(
            db=db,
            enrollment_id=enrollment.id,
            step_id=step_1.id,
            step_number=1,
            recipient_email=contact_email,
            status="scheduled",
            scheduled_at=scheduled_at
        )

        # Enqueue execution
        try:
            task = celery_app.send_task(
                "app.worker.tasks.execute_outreach_step",
                args=[message.id],
                eta=scheduled_at
            )
            message.celery_task_id = task.id
            db.add(message)
        except Exception as e:
            logger.error(f"Failed to enqueue Celery task: {e}")

        await db.commit()
        return await crud.get_enrollment(db, enrollment.id)

    async def enroll_company_from_pipeline(
        self,
        db: AsyncSession,
        company_id: int,
        sequence_id: int,
        contact_email: str,
        draft_subject: str,
        draft_body: str,
        draft_cta: str,
        draft_only: bool = True
    ) -> SequenceEnrollment:
        logger.info(f"Enrolling company {company_id} from pipeline into sequence {sequence_id}")

        sequence = await crud.get_sequence(db, sequence_id)
        if not sequence or not sequence.is_active:
            raise ValueError(f"Sequence ID {sequence_id} is inactive or not found.")

        company = await crud.get_company(db, company_id)
        if not company:
            raise ValueError(f"Company ID {company_id} not found.")

        company.contact_email = contact_email
        db.add(company)

        # Cancel previous active enrollment
        active_enrollment = await crud.get_active_enrollment_by_company(db, company_id)
        if active_enrollment:
            active_enrollment.status = "cancelled"
            active_enrollment.completed_at = datetime.now(timezone.utc)
            db.add(active_enrollment)
            for msg in active_enrollment.messages:
                if msg.status == "scheduled":
                    msg.status = "cancelled"
                    db.add(msg)
                    if msg.celery_task_id:
                        try:
                            celery_app.control.revoke(msg.celery_task_id, terminate=True)
                        except Exception as e:
                            logger.warning(f"Failed to revoke task {msg.celery_task_id}: {e}")
            await crud.create_audit_log(db, company_id, "sequence_cancelled", "success", {
                "enrollment_id": active_enrollment.id,
                "reason": "New sequence enrolled from pipeline"
            })

        # Create enrollment
        enrollment = await crud.create_enrollment(
            db, company_id=company_id, sequence_id=sequence_id, contact_email=contact_email
        )

        await crud.create_audit_log(db, company_id, "sequence_enrolled", "success", {
            "enrollment_id": enrollment.id,
            "sequence_name": sequence.name,
            "source": "pipeline"
        })

        step_1 = next((s for s in sequence.steps if s.step_number == 1), None)
        step_1_id = step_1.id if step_1 else None

        # Create outreach message using the generated draft
        now = datetime.now(timezone.utc)
        message = await crud.create_outreach_message(
            db=db,
            enrollment_id=enrollment.id,
            step_id=step_1_id,
            step_number=1,
            recipient_email=contact_email,
            status="draft",
            scheduled_at=now,
            subject=draft_subject,
            body=draft_body,
            cta=draft_cta
        )

        if not draft_only:
            # Deliver immediately
            message.status = "sending"
            db.add(message)
            await db.commit()

            try:
                mail_res = await gmail_service.send_email(
                    recipient_email=contact_email,
                    subject=message.subject,
                    body=f"{message.body}\n\n{message.cta}"
                )
                if mail_res.get("status") == "sent":
                    message.status = "sent"
                    message.sent_at = datetime.now(timezone.utc)
                    message.message_id = mail_res.get("message_id")
                    db.add(message)
                    
                    await crud.create_audit_log(db, company_id, "follow_up_sent", "success", {
                        "message_id": message.id,
                        "step_number": 1,
                        "recipient": contact_email
                    })

                    # Trigger CRM webhook event
                    crm = crm_registry.get_crm("webhook")
                    if crm and hasattr(crm, "trigger_event"):
                        company_payload = {"id": company.id, "name": company.name, "domain": company.domain}
                        await crm.trigger_event("follow_up_sent", company_payload, {
                            "step_number": 1,
                            "subject": message.subject,
                            "recipient": contact_email
                        })

                    # Schedule Step 2
                    await self.schedule_next_step(db, enrollment.id)
                else:
                    err = mail_res.get("error", "SMTP Delivery failed")
                    message.status = "failed"
                    message.error_message = err
                    db.add(message)
                    await crud.create_audit_log(db, company_id, "follow_up_failed", "failed", {
                        "message_id": message.id,
                        "error": err
                    })
            except Exception as e:
                logger.error(f"Failed pipeline initial email send: {e}")
                message.status = "failed"
                message.error_message = str(e)
                db.add(message)
                await crud.create_audit_log(db, company_id, "follow_up_failed", "failed", {
                    "message_id": message.id,
                    "error": str(e)
                })
        else:
            await crud.create_audit_log(db, company_id, "follow_up_drafted", "success", {
                "message_id": message.id,
                "step_number": 1
            })

        await db.commit()
        return await crud.get_enrollment(db, enrollment.id)

    async def schedule_next_step(self, db: AsyncSession, enrollment_id: int):
        enrollment = await crud.get_enrollment(db, enrollment_id)
        if not enrollment or enrollment.status != "active":
            return

        # Fetch sequence steps
        sequence = await crud.get_sequence(db, enrollment.sequence_id)
        if not sequence:
            return

        # Find step where step_number > current_step
        next_step = None
        for step in sorted(sequence.steps, key=lambda s: s.step_number):
            if step.step_number > enrollment.current_step:
                next_step = step
                break

        if not next_step:
            logger.info(f"No further steps in sequence {sequence.id}. Completing enrollment {enrollment_id}")
            enrollment.status = "completed"
            enrollment.completed_at = datetime.now(timezone.utc)
            db.add(enrollment)
            
            await crud.create_audit_log(db, enrollment.company_id, "sequence_completed", "success", {
                "enrollment_id": enrollment.id,
                "sequence_name": sequence.name
            })

            # Trigger CRM webhook event
            crm = crm_registry.get_crm("webhook")
            if crm and hasattr(crm, "trigger_event"):
                company_result = await db.execute(select(Company).where(Company.id == enrollment.company_id))
                company = company_result.scalars().first()
                if company:
                    company_payload = {"id": company.id, "name": company.name, "domain": company.domain}
                    await crm.trigger_event("sequence_completed", company_payload, {
                        "enrollment_id": enrollment.id,
                        "sequence_name": sequence.name
                    })

            await db.commit()
            return

        # Create next message
        scheduled_at = datetime.now(timezone.utc) + timedelta(days=next_step.delay_days)
        message = await crud.create_outreach_message(
            db=db,
            enrollment_id=enrollment.id,
            step_id=next_step.id,
            step_number=next_step.step_number,
            recipient_email=enrollment.contact_email,
            status="scheduled",
            scheduled_at=scheduled_at
        )

        enrollment.current_step = next_step.step_number
        db.add(enrollment)

        try:
            task = celery_app.send_task(
                "app.worker.tasks.execute_outreach_step",
                args=[message.id],
                eta=scheduled_at
            )
            message.celery_task_id = task.id
            db.add(message)
        except Exception as e:
            logger.error(f"Failed to schedule celery task for next step: {e}")

        await crud.create_audit_log(db, enrollment.company_id, "follow_up_scheduled", "success", {
            "message_id": message.id,
            "step_number": next_step.step_number,
            "scheduled_at": scheduled_at.isoformat()
        })

        await db.commit()

    async def execute_step(self, message_id: int, manual_send: bool = False):
        async with SessionLocal() as db:
            message = await crud.get_outreach_message(db, message_id)
            if not message or message.status not in ("scheduled", "draft", "failed"):
                logger.warning(f"Message {message_id} is not eligible for execution. Status: {message.status if message else 'None'}")
                return

            enrollment = await crud.get_enrollment(db, message.enrollment_id)
            if not enrollment or enrollment.status != "active":
                logger.warning(f"Enrollment {message.enrollment_id} is not active. Aborting execute step.")
                return

            company = await crud.get_company(db, enrollment.company_id)
            if not company:
                logger.error(f"Company ID {enrollment.company_id} not found for outreach execution.")
                return

            # Check if LLM generation is needed
            if not message.subject or not message.body:
                logger.info(f"Generating content for follow-up message {message_id}")
                
                # Fetch company enrichments
                enrichments = await crud.get_enrichments_by_company(db, company.id)
                clean_data = enrichments[0].clean_data if enrichments else {}
                
                # Fetch AI analyses
                analyses = await crud.get_ai_analyses_by_company(db, company.id)
                analysis = analyses[0] if analyses else None
                
                # Fetch prior sent messages
                prior_messages_result = await db.execute(
                    select(OutreachMessage)
                    .where(OutreachMessage.enrollment_id == enrollment.id)
                    .where(OutreachMessage.status == "sent")
                    .order_by(OutreachMessage.step_number.asc())
                )
                prior_messages = prior_messages_result.scalars().all()
                prior_messages_list = [{"subject": m.subject, "body": m.body} for m in prior_messages]

                # Fetch reply snippet if any
                reply_event_result = await db.execute(
                    select(ReplyEvent)
                    .where(ReplyEvent.enrollment_id == enrollment.id)
                    .order_by(ReplyEvent.detected_at.desc())
                )
                latest_reply = reply_event_result.scalars().first()
                reply_snippet = latest_reply.snippet if latest_reply else None

                step_prompt = message.step.prompt_template if message.step else "Write a professional follow-up email."

                try:
                    generated = await llm_service.generate_follow_up_email(
                        company_name=company.name,
                        summary=analysis.summary if analysis else "",
                        pain_points=analysis.pain_points if analysis else [],
                        buying_signals=analysis.buying_signals if analysis else [],
                        prompt_template=step_prompt,
                        prior_messages=prior_messages_list,
                        reply_snippet=reply_snippet,
                        sources_mapping=clean_data.get("sources_mapping", {})
                    )
                    message.subject = generated.get("subject", "")
                    message.body = generated.get("email", "")
                    message.cta = generated.get("cta", "")
                    db.add(message)
                    await db.commit()
                except Exception as e:
                    logger.exception(f"LLM follow-up email generation failed for message {message_id}: {e}")
                    message.status = "failed"
                    message.error_message = f"LLM generation failed: {str(e)}"
                    db.add(message)
                    await db.commit()
                    await crud.create_audit_log(db, company.id, "follow_up_failed", "failed", {
                        "message_id": message.id,
                        "error": f"LLM generation error: {str(e)}"
                    })
                    return

            # Determine whether to send
            auto_send = message.step.auto_send if message.step else True
            
            if auto_send or manual_send:
                message.status = "sending"
                db.add(message)
                await db.commit()

                try:
                    mail_res = await gmail_service.send_email(
                        recipient_email=message.recipient_email,
                        subject=message.subject,
                        body=f"{message.body}\n\n{message.cta}"
                    )
                    if mail_res.get("status") == "sent":
                        message.status = "sent"
                        message.sent_at = datetime.now(timezone.utc)
                        message.message_id = mail_res.get("message_id")
                        db.add(message)

                        await crud.create_audit_log(db, company.id, "follow_up_sent", "success", {
                            "message_id": message.id,
                            "step_number": message.step_number,
                            "recipient": message.recipient_email
                        })

                        # Trigger CRM sync
                        crm = crm_registry.get_crm("webhook")
                        if crm and hasattr(crm, "trigger_event"):
                            company_payload = {"id": company.id, "name": company.name, "domain": company.domain}
                            await crm.trigger_event("follow_up_sent", company_payload, {
                                "step_number": message.step_number,
                                "subject": message.subject,
                                "recipient": message.recipient_email
                            })

                        # Schedule Next Step
                        await self.schedule_next_step(db, enrollment.id)
                    else:
                        err = mail_res.get("error", "SMTP Delivery failed")
                        message.status = "failed"
                        message.error_message = err
                        db.add(message)
                        await crud.create_audit_log(db, company.id, "follow_up_failed", "failed", {
                            "message_id": message.id,
                            "error": err
                        })
                except Exception as e:
                    logger.error(f"Gmail SMTP delivery failed for message {message_id}: {e}")
                    message.status = "failed"
                    message.error_message = str(e)
                    db.add(message)
                    await crud.create_audit_log(db, company.id, "follow_up_failed", "failed", {
                        "message_id": message.id,
                        "error": str(e)
                    })
            else:
                message.status = "draft"
                db.add(message)
                await crud.create_audit_log(db, company.id, "follow_up_drafted", "success", {
                    "message_id": message.id,
                    "step_number": message.step_number
                })
            
            await db.commit()

    async def pause_on_reply(self, db: AsyncSession, enrollment_id: int, reply_event) -> None:
        enrollment = await crud.get_enrollment(db, enrollment_id)
        if not enrollment or enrollment.status == "replied":
            return

        logger.info(f"Pausing enrollment {enrollment_id} due to prospect reply from {reply_event.from_email}")
        
        enrollment.status = "replied"
        enrollment.completed_at = datetime.now(timezone.utc)
        db.add(enrollment)

        # Cancel pending messages
        for msg in enrollment.messages:
            if msg.status == "scheduled":
                msg.status = "cancelled"
                db.add(msg)
                if msg.celery_task_id:
                    try:
                        celery_app.control.revoke(msg.celery_task_id, terminate=True)
                    except Exception as e:
                        logger.warning(f"Failed to revoke task {msg.celery_task_id} during pause: {e}")

        await crud.create_audit_log(db, enrollment.company_id, "prospect_replied", "success", {
            "enrollment_id": enrollment.id,
            "reply_from": reply_event.from_email,
            "subject": reply_event.subject,
            "snippet": reply_event.snippet
        })
        
        await crud.create_audit_log(db, enrollment.company_id, "sequence_paused", "success", {
            "enrollment_id": enrollment.id
        })

        # Trigger CRM sync event
        crm = crm_registry.get_crm("webhook")
        if crm and hasattr(crm, "trigger_event"):
            company_result = await db.execute(select(Company).where(Company.id == enrollment.company_id))
            company = company_result.scalars().first()
            if company:
                company_payload = {"id": company.id, "name": company.name, "domain": company.domain}
                await crm.trigger_event("prospect_replied", company_payload, {
                    "reply_from": reply_event.from_email,
                    "subject": reply_event.subject,
                    "snippet": reply_event.snippet
                })

        await db.commit()

    async def sweep_overdue_messages(self) -> None:
        async with SessionLocal() as db:
            now = datetime.now(timezone.utc)
            # Find scheduled messages with scheduled_at in the past
            result = await db.execute(
                select(OutreachMessage)
                .join(SequenceEnrollment)
                .where(OutreachMessage.status == "scheduled")
                .where(OutreachMessage.scheduled_at <= now)
                .where(SequenceEnrollment.status == "active")
            )
            overdue_messages = result.scalars().all()
            
            if overdue_messages:
                logger.info(f"Sweep found {len(overdue_messages)} overdue messages.")
                for msg in overdue_messages:
                    try:
                        task = celery_app.send_task(
                            "app.worker.tasks.execute_outreach_step",
                            args=[msg.id]
                        )
                        msg.celery_task_id = task.id
                        db.add(msg)
                    except Exception as e:
                        logger.error(f"Sweep failed to dispatch task for message {msg.id}: {e}")
                await db.commit()


sequence_engine = SequenceEngine()
