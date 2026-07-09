import re
from bs4 import BeautifulSoup
from typing import Dict, Any, List
from app.normalizers.base import BaseNormalizer

EMAIL_REGEX = re.compile(r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}")
PHONE_REGEX = re.compile(r"\+?\d{1,4}[-.\s]?\(?\d{1,3}?\)?[-.\s]?\d{1,4}[-.\s]?\d{1,4}[-.\s]?\d{1,9}")

class WebsiteNormalizer(BaseNormalizer):
    def normalize(self, raw_data: Dict[str, Any]) -> Dict[str, Any]:
        html = raw_data.get("html", "")
        domain = raw_data.get("domain", "")
        
        if not html:
            return self._empty_response(domain)

        soup = BeautifulSoup(html, "html.parser")
        
        # 1. Company Name
        company = ""
        og_site = soup.find("meta", property="og:site_name")
        if og_site and og_site.get("content"):
            company = og_site["content"].strip()
        else:
            title = soup.find("title")
            if title and title.string:
                title_str = title.string.strip()
                for suffix in ["|", "-", "–"]:
                    if suffix in title_str:
                        title_str = title_str.split(suffix)[0].strip()
                company = title_str
        if not company:
            company = domain.split(".")[0].capitalize()

        # 2. Description
        description = ""
        meta_desc = soup.find("meta", name="description") or soup.find("meta", property="og:description")
        if meta_desc and meta_desc.get("content"):
            description = meta_desc["content"].strip()

        # 3. Industry
        industry = ""
        meta_keywords = soup.find("meta", name="keywords")
        if meta_keywords and meta_keywords.get("content"):
            industry = meta_keywords["content"].split(",")[0].strip().capitalize()
        if not industry and description:
            desc_lower = description.lower()
            if "software" in desc_lower or "saas" in desc_lower or "tech" in desc_lower:
                industry = "Technology"
            elif "finance" in desc_lower or "bank" in desc_lower:
                industry = "Finance"
            elif "health" in desc_lower or "medical" in desc_lower:
                industry = "Healthcare"
        if not industry:
            industry = "Enterprise"

        links = soup.find_all("a", href=True)
        products = []
        recent_news = []
        social_links = []
        careers = []
        emails = []
        phones = []

        for link in links:
            href = link["href"].strip()
            text = link.get_text().strip().lower()
            
            if href.startswith("mailto:"):
                email = href[7:].split("?")[0].strip()
                if EMAIL_REGEX.match(email) and email not in emails:
                    emails.append(email)
                continue
                
            if href.startswith("tel:"):
                phone = href[4:].split("?")[0].strip()
                if phone not in phones:
                    phones.append(phone)
                continue

            for platform in ["linkedin.com", "twitter.com", "x.com", "facebook.com", "github.com", "youtube.com"]:
                if platform in href and href not in social_links:
                    social_links.append(href)

            if any(k in href.lower() or k in text for k in ["career", "job", "join-us", "work-at"]) and href not in careers:
                if href.startswith("/"):
                    href = f"https://{domain}{href}"
                if href.startswith("http") and href not in careers:
                    careers.append(href)

            if any(k in href.lower() or k in text for k in ["product", "features", "solutions", "pricing"]) and href not in products:
                if href.startswith("/"):
                    href = f"https://{domain}{href}"
                if href.startswith("http") and href not in products:
                    products.append(href)

            if any(k in href.lower() or k in text for k in ["blog", "news", "press", "media"]) and href not in recent_news:
                if href.startswith("/"):
                    href = f"https://{domain}{href}"
                if href.startswith("http") and href not in recent_news:
                    recent_news.append(href)

        body_text = soup.get_text()
        found_emails = EMAIL_REGEX.findall(body_text)
        for email in found_emails:
            if email not in emails:
                emails.append(email)
                
        found_phones = PHONE_REGEX.findall(body_text)
        for phone in found_phones:
            phone_clean = phone.strip()
            if len(phone_clean) >= 7 and phone_clean not in phones:
                phones.append(phone_clean)

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
