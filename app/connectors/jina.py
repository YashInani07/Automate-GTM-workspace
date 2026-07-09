import httpx
import logging
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type
from app.connectors.base import BaseConnector
from app.core.config import settings

logger = logging.getLogger(__name__)

class JinaConnector(BaseConnector):
    @property
    def name(self) -> str:
        return "jina"

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_exception_type((httpx.HTTPStatusError, httpx.RequestError)),
        reraise=True
    )
    async def fetch(self, company_domain: str) -> dict:
        if company_domain.startswith("http://") or company_domain.startswith("https://"):
            url = f"https://r.jina.ai/{company_domain}"
        else:
            url = f"https://r.jina.ai/https://{company_domain}"
        headers = {
            "Authorization": f"Bearer {settings.JINA_API_KEY}"
        }
        logger.info(f"Initiating Jina Reader scrape for domain: {company_domain}")
        
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(url, headers=headers)
            response.raise_for_status()
            
            return {
                "url": url,
                "domain": company_domain,
                "status_code": response.status_code,
                "markdown": response.text,
                "headers": dict(response.headers)
            }
