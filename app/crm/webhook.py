import httpx
import logging
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type
from app.crm.base import BaseCRM
from app.core.config import settings

logger = logging.getLogger(__name__)

class WebhookCRM(BaseCRM):
    @property
    def name(self) -> str:
        return "webhook"

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_exception_type((httpx.HTTPStatusError, httpx.RequestError)),
        reraise=True
    )
    async def sync_company(
        self,
        company_data: dict,
        analysis_data: dict,
        email_data: dict
    ) -> dict:
        url = settings.CRM_WEBHOOK_URL
        if not url:
            logger.info("CRM Webhook URL not configured. Sync skipped.")
            return {"status": "skipped", "message": "CRM_WEBHOOK_URL not set"}

        logger.info(f"Syncing company {company_data.get('name')} to CRM webhook: {url}")
        
        payload = {
            "event": "crm_sync",
            "company": company_data,
            "analysis": analysis_data,
            "email_draft": email_data
        }

        async with httpx.AsyncClient(timeout=15.0) as client:
            response = await client.post(url, json=payload)
            response.raise_for_status()
            
            # Retrieve JSON response safely if header permits, else return raw text
            res_content = ""
            try:
                if "application/json" in response.headers.get("content-type", "").lower():
                    res_content = response.json()
                else:
                    res_content = response.text
            except Exception:
                res_content = response.text

            return {
                "status": "success",
                "status_code": response.status_code,
                "response": res_content
            }

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_exception_type((httpx.HTTPStatusError, httpx.RequestError)),
        reraise=True
    )
    async def trigger_event(
        self,
        event_type: str,
        company_data: dict,
        extra_data: dict = None
    ) -> dict:
        url = settings.CRM_WEBHOOK_URL
        if not url:
            logger.info("CRM Webhook URL not configured. CRM event skipped.")
            return {"status": "skipped", "message": "CRM_WEBHOOK_URL not set"}

        logger.info(f"Triggering event {event_type} for company {company_data.get('name')} to CRM webhook: {url}")
        
        payload = {
            "event": event_type,
            "company": company_data,
            **(extra_data or {})
        }

        async with httpx.AsyncClient(timeout=15.0) as client:
            response = await client.post(url, json=payload)
            response.raise_for_status()
            
            res_content = ""
            try:
                if "application/json" in response.headers.get("content-type", "").lower():
                    res_content = response.json()
                else:
                    res_content = response.text
            except Exception:
                res_content = response.text

            return {
                "status": "success",
                "status_code": response.status_code,
                "response": res_content
            }

