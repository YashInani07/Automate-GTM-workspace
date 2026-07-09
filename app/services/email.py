import logging
import aiosmtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime, timezone
from app.core.config import settings

logger = logging.getLogger(__name__)

class GmailService:
    @property
    def is_configured(self) -> bool:
        return bool(settings.GMAIL_USER and settings.GMAIL_APP_PASSWORD)

    async def send_email(self, recipient_email: str, subject: str, body: str) -> dict:
        """Sends an email using Gmail SMTP asynchronously."""
        if not self.is_configured:
            logger.info("Gmail credentials are not configured. Email delivery skipped.")
            return {"status": "skipped", "message": "Gmail integration not configured"}

        logger.info(f"Sending email via Gmail SMTP to {recipient_email}")

        from email.utils import make_msgid

        message = MIMEMultipart()
        message["From"] = settings.GMAIL_USER
        message["To"] = recipient_email
        message["Subject"] = subject
        
        domain = "gtmworkflow.local"
        if settings.GMAIL_USER and "@" in settings.GMAIL_USER:
            domain = settings.GMAIL_USER.split("@")[-1]
        msg_id = make_msgid(domain=domain)
        message["Message-ID"] = msg_id
        
        message.attach(MIMEText(body, "plain"))

        try:
            smtp = aiosmtplib.SMTP(
                hostname="smtp.gmail.com",
                port=465,
                use_tls=True
            )
            await smtp.connect()
            await smtp.login(settings.GMAIL_USER, settings.GMAIL_APP_PASSWORD)
            await smtp.send_message(message)
            await smtp.quit()
            
            logger.info(f"Email sent successfully to {recipient_email}")
            return {
                "status": "sent",
                "timestamp": datetime.now(timezone.utc),
                "message_id": msg_id
            }
        except Exception as e:
            logger.error(f"Failed to send email via Gmail SMTP: {e}")
            return {"status": "failed", "error": str(e)}


gmail_service = GmailService()
