import re
from typing import Dict, Any, List
from app.normalizers.base import BaseNormalizer

EMAIL_REGEX = re.compile(r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}")
PHONE_REGEX = re.compile(r"\+?\d{1,4}[-.\s]?\(?\d{1,3}?\)?[-.\s]?\d{1,4}[-.\s]?\d{1,4}[-.\s]?\d{1,9}")
LINK_REGEX = re.compile(r"\[([^\]]+)\]\((https?://[^\)]+)\)")

class JinaNormalizer(BaseNormalizer):
    def normalize(self, raw_data: Dict[str, Any]) -> Dict[str, Any]:
        markdown = raw_data.get("markdown", "")
        domain = raw_data.get("domain", "")

        if not markdown:
            return self._empty_response(domain)

        # 1. Company Name
        company = ""
        header_match = re.search(r"^#\s+(.+)$", markdown, re.MULTILINE)
        if header_match:
            company = header_match.group(1).strip()
            for suffix in ["|", "-", "–"]:
                if suffix in company:
                    company = company.split(suffix)[0].strip()
        
        if not company:
            title_match = re.search(r"^Title:\s+(.+)$", markdown, re.MULTILINE)
            if title_match:
                company = title_match.group(1).strip()
                for suffix in ["|", "-", "–"]:
                    if suffix in company:
                        company = company.split(suffix)[0].strip()

        if not company:
            company = domain.split(".")[0].capitalize()

        # 2. Description
        description = ""
        paragraphs = [p.strip() for p in markdown.split("\n\n") if p.strip()]
        for p in paragraphs:
            if p.startswith("#") or p.startswith("Title:") or p.startswith("URL:") or p.startswith("!["):
                continue
            description = p
            break

        # 3. Industry
        industry = ""
        if description:
            desc_lower = description.lower()
            if "software" in desc_lower or "saas" in desc_lower or "tech" in desc_lower:
                industry = "Technology"
            elif "finance" in desc_lower or "bank" in desc_lower:
                industry = "Finance"
            elif "health" in desc_lower or "medical" in desc_lower:
                industry = "Healthcare"
        if not industry:
            industry = "Enterprise"

        # 4. Links and Contact Details
        products = []
        recent_news = []
        social_links = []
        careers = []
        emails = EMAIL_REGEX.findall(markdown)
        phones = PHONE_REGEX.findall(markdown)

        emails = list(set([e.strip() for e in emails]))
        phones = list(set([p.strip() for p in phones if len(p.strip()) >= 7]))

        all_links = LINK_REGEX.findall(markdown)
        for text, url in all_links:
            text_lower = text.lower()
            url_lower = url.lower()

            for platform in ["linkedin.com", "twitter.com", "x.com", "facebook.com", "github.com", "youtube.com"]:
                if platform in url_lower and url not in social_links:
                    social_links.append(url)

            if any(k in url_lower or k in text_lower for k in ["career", "job", "join-us", "work-at"]) and url not in careers:
                careers.append(url)

            if any(k in url_lower or k in text_lower for k in ["product", "features", "solutions", "pricing"]) and url not in products:
                products.append(url)

            if any(k in url_lower or k in text_lower for k in ["blog", "news", "press", "media"]) and url not in recent_news:
                recent_news.append(url)

        return {
            "company": company,
            "industry": industry,
            "description": description,
            "products": products[:10],
            "recent_news": recent_news[:5],
            "social_links": social_links,
            "careers": careers[:5],
            "contact_information": {
                "emails": emails[:5],
                "phones": phones[:5]
            }
        }

    def _empty_response(self, domain: str) -> Dict[str, Any]:
        return {
            "company": domain.split(".")[0].capitalize(),
            "industry": "Unknown",
            "description": "",
            "products": [],
            "recent_news": [],
            "social_links": [],
            "careers": [],
            "contact_information": {
                "emails": [],
                "phones": []
            }
        }
