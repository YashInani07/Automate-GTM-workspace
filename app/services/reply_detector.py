import logging
import imaplib
import email
from email.header import decode_header
from email.utils import parseaddr
from datetime import datetime, timedelta, timezone
from typing import Optional, Tuple

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.core.config import settings
from app.core.database import SessionLocal
import app.crud as crud
from app.models.sequence_enrollment import SequenceEnrollment
from app.models.outreach_message import OutreachMessage
from app.models.reply_event import ReplyEvent
from app.services.sequence_engine import sequence_engine

logger = logging.getLogger(__name__)


class ReplyDetector:
    def _decode_header(self, raw_header: Optional[str]) -> str:
        if not raw_header:
            return ""
        decoded_parts = decode_header(raw_header)
        header_text = ""
        for bytes_or_str, encoding in decoded_parts:
            if isinstance(bytes_or_str, bytes):
                try:
                    header_text += bytes_or_str.decode(encoding or "utf-8", errors="ignore")
                except Exception:
                    header_text += bytes_or_str.decode("utf-8", errors="ignore")
            else:
                header_text += bytes_or_str
        return header_text.strip()

    def _parse_reply_headers(self, msg) -> Tuple[str, str, str, str, str, str]:
        msg_id = self._decode_header(msg.get("Message-ID"))
        in_reply_to = self._decode_header(msg.get("In-Reply-To"))
        references = self._decode_header(msg.get("References"))
        from_hdr = self._decode_header(msg.get("From"))
        subject = self._decode_header(msg.get("Subject"))
        
        # Extract clean email address from From header
        _, from_email = parseaddr(from_hdr)
        
        # Get snippet
        snippet = ""
        if msg.is_multipart():
            for part in msg.walk():
                content_type = part.get_content_type()
                if content_type == "text/plain":
                    try:
                        body = part.get_payload(decode=True).decode("utf-8", errors="ignore")
                        snippet = body[:300].strip()
                        break
                    except Exception:
                        pass
        else:
            try:
                body = msg.get_payload(decode=True).decode("utf-8", errors="ignore")
                snippet = body[:300].strip()
            except Exception:
                pass
                
        return msg_id, in_reply_to, references, from_email, subject, snippet

    async def poll_inbox(self) -> None:
        if not settings.IMAP_USER or not settings.IMAP_PASSWORD:
            logger.info("IMAP credentials are not configured. Reply detection skipped.")
            return

        logger.info("Starting IMAP inbox poll for reply detection...")
        
        imap = None
        try:
            imap = imaplib.IMAP4_SSL(settings.IMAP_HOST, settings.IMAP_PORT)
            imap.login(settings.IMAP_USER, settings.IMAP_PASSWORD)
            imap.select("INBOX")

            # Search messages from the last 7 days
            since_date = (datetime.now() - timedelta(days=7)).strftime("%d-%b-%Y")
            status, search_data = imap.search(None, f"(SINCE {since_date})")
            
            if status != "OK":
                logger.error("Failed to search messages in IMAP INBOX")
                return

            msg_ids = search_data[0].split()
            logger.info(f"IMAP poll found {len(msg_ids)} recent messages in INBOX")

            if not msg_ids:
                return

            # Process each message
            async with SessionLocal() as db:
                for mail_id in msg_ids:
                    # Fetch headers and structure
                    res, data = imap.fetch(mail_id, "(RFC822)")
                    if res != "OK":
                        continue
                    
                    raw_email = data[0][1]
                    msg = email.message_from_bytes(raw_email)
                    
                    msg_id, in_reply_to, references, from_email, subject, snippet = self._parse_reply_headers(msg)
                    
                    # Search match candidates
                    matched_enrollment_id = None
                    matched_msg_id_ref = None

                    # 1. Match by In-Reply-To
                    if in_reply_to:
                        msg_result = await db.execute(
                            select(OutreachMessage)
                            .where(OutreachMessage.message_id == in_reply_to)
                        )
                        sent_msg = msg_result.scalars().first()
                        if sent_msg:
                            matched_enrollment_id = sent_msg.enrollment_id
                            matched_msg_id_ref = in_reply_to
                            
                    # 2. Match by References
                    if not matched_enrollment_id and references:
                        # References contains whitespace separated message IDs
                        ref_ids = [ref.strip() for ref in references.split() if ref.strip()]
                        for r_id in ref_ids:
                            msg_result = await db.execute(
                                select(OutreachMessage)
                                .where(OutreachMessage.message_id == r_id)
                            )
                            sent_msg = msg_result.scalars().first()
                            if sent_msg:
                                matched_enrollment_id = sent_msg.enrollment_id
                                matched_msg_id_ref = r_id
                                break

                    # 3. Fallback match by Sender Email + subject reply structure
                    if not matched_enrollment_id and from_email:
                        # Clean subject reply prefixes
                        clean_subj = subject.lower()
                        for prefix in ("re:", "fwd:", "fw:"):
                            if clean_subj.startswith(prefix):
                                clean_subj = clean_subj[len(prefix):].strip()

                        # Find active enrollments matching sender email
                        enroll_result = await db.execute(
                            select(SequenceEnrollment)
                            .where(SequenceEnrollment.contact_email == from_email)
                            .where(SequenceEnrollment.status == "active")
                            .options(selectinload(SequenceEnrollment.messages))
                        )
                        active_enrollments = enroll_result.scalars().all()
                        
                        for enroll in active_enrollments:
                            for msg_sent in enroll.messages:
                                if msg_sent.status == "sent":
                                    sent_subj_clean = msg_sent.subject.lower()
                                    if sent_subj_clean.startswith("re:"):
                                        sent_subj_clean = sent_subj_clean[3:].strip()
                                    
                                    # Match clean subjects
                                    if clean_subj == sent_subj_clean:
                                        matched_enrollment_id = enroll.id
                                        matched_msg_id_ref = msg_sent.message_id
                                        break
                            if matched_enrollment_id:
                                break

                    # If we have a matched enrollment, process it
                    if matched_enrollment_id:
                        # Check if we already registered this reply
                        existing_result = await db.execute(
                            select(ReplyEvent)
                            .where(ReplyEvent.enrollment_id == matched_enrollment_id)
                            .where(ReplyEvent.from_email == from_email)
                            .where(ReplyEvent.subject == subject)
                        )
                        existing_reply = existing_result.scalars().first()
                        
                        if not existing_reply:
                            logger.info(f"Detected reply from {from_email} on enrollment {matched_enrollment_id} - Subject: {subject}")
                            # Create ReplyEvent
                            reply_event = await crud.create_reply_event(
                                db=db,
                                enrollment_id=matched_enrollment_id,
                                from_email=from_email,
                                subject=subject,
                                snippet=snippet,
                                in_reply_to=matched_msg_id_ref,
                                raw_headers=f"Message-ID: {msg_id}\nIn-Reply-To: {in_reply_to}\nReferences: {references}"
                            )
                            # Pause sequence enrollment
                            await sequence_engine.pause_on_reply(db, matched_enrollment_id, reply_event)
                
        except Exception as e:
            logger.error(f"Error during reply detection IMAP poll: {e}")
        finally:
            if imap:
                try:
                    imap.close()
                except Exception:
                    pass
                try:
                    imap.logout()
                except Exception:
                    pass
                logger.info("IMAP Connection closed.")


reply_detector = ReplyDetector()
