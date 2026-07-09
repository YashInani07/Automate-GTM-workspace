import httpx
import logging
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type
from app.connectors.base import BaseConnector

logger = logging.getLogger(__name__)

class CompanyWebsiteConnector(BaseConnector):
    @property
    def name(self) -> str:
        return "website"

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_exception_type((httpx.HTTPStatusError, httpx.RequestError)),
        reraise=True
    )
    async def fetch(self, company_domain: str) -> dict:
        async with httpx.AsyncClient(timeout=15.0, follow_redirects=True) as client:
            if company_domain.startswith("http://") or company_domain.startswith("https://"):
                url = company_domain
                logger.info(f"Initiating direct HTML scrape for: {url}")
                response = await client.get(url)
                response.raise_for_status()
            else:
                url = f"https://{company_domain}"
                logger.info(f"Initiating direct HTML scrape for: {url}")
                try:
                    response = await client.get(url)
                    response.raise_for_status()
                except (httpx.ConnectError, httpx.ConnectTimeout):
                    url = f"http://{company_domain}"
                    logger.info(f"HTTPS failed for {company_domain}, trying HTTP: {url}")
                    response = await client.get(url)
                    response.raise_for_status()

            return {
                "url": url,
                "domain": company_domain,
                "status_code": response.status_code,
                "html": response.text,
                "headers": dict(response.headers)
            }
