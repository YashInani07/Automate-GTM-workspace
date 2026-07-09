import json
import logging
import asyncio
from functools import partial
import google.generativeai as genai
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type
from app.core.config import settings

logger = logging.getLogger(__name__)

# Configure Gemini API
genai.configure(api_key=settings.GEMINI_API_KEY)

class LLMService:
    def __init__(self):
        self.model = genai.GenerativeModel("gemini-2.5-flash")

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        reraise=True
    )
    async def analyze_company_profile(self, profile: dict) -> dict:
        """Analyzes a company profile using Gemini to extract summary, pain points,
        buying signals, and outreach context.
        """
        logger.info(f"Triggering Gemini analysis for company: {profile.get('company')}")
        sources_mapping = profile.get("sources_mapping", {})
        
        prompt = f"""
        You are an expert sales analyst. Analyze the following company profile data:
        
        Company Name: {profile.get('company')}
        Description: {profile.get('description')}
        Industry: {profile.get('industry')}
        Products/Features: {profile.get('products')}
        Recent News/Blogs: {profile.get('recent_news')}
        
        Source URLs mapping table: {sources_mapping}
        
        Generate:
        1. A concise, professional company summary (2-3 sentences).
        2. 3-5 specific, realistic business pain points this company likely faces based on their profile.
        3. 2-3 realistic buying signals (e.g. hiring, expanding, launching products, tech stack indicators) shown by this company.
        4. A personalized outreach context (why we should reach out to them now, and what angle to use).
        
        CRITICAL CITATION RULES:
        - In the description above, sources are labeled as [Source #0], [Source #1], etc.
        - You MUST add inline citations like [0], [1], next to facts in the summary, pain points, or buying signals.
        - Only cite source indexes that exist in the mapping table.
        
        Return ONLY a valid JSON object matching the following structure. Do not include markdown code fences (like ```json), styling, or extra commentary.
        
        {{
            "summary": "company summary string containing inline citation numbers (e.g. [1])",
            "pain_points": ["pain point 1 [0]", "pain point 2 [1]"],
            "buying_signals": ["buying signal 1 [1]"],
            "outreach_context": "outreach context string with inline citations"
        }}
        """
        
        loop = asyncio.get_event_loop()
        response = await loop.run_in_executor(
            None,
            partial(
                self.model.generate_content,
                prompt,
                generation_config={"response_mime_type": "application/json"}
            )
        )
        
        logger.info(f"Gemini analysis completed for: {profile.get('company')}")
        result_text = response.text.strip()
        
        try:
            res = json.loads(result_text)
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse Gemini JSON output: {result_text}. Error: {e}")
            cleaned = result_text.replace("```json", "").replace("```", "").strip()
            res = json.loads(cleaned)

        # Append bibliography to outreach_context
        if sources_mapping:
            bib = "\n\nSources Cited:\n" + "\n".join([f"[{k}] {v}" for k, v in sources_mapping.items()])
            res["outreach_context"] = (res.get("outreach_context", "") or "") + bib
            
        return res

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        reraise=True
    )
    async def generate_cold_email(
        self,
        company_name: str,
        summary: str,
        pain_points: list,
        buying_signals: list,
        products: list,
        recent_news: list,
        outreach_objective: str,
        sources_mapping: dict = None
    ) -> dict:
        """Generates a personalized cold email using Gemini."""
        logger.info(f"Triggering Gemini cold email generation for company: {company_name}")
        sources_mapping = sources_mapping or {}
        
        prompt = f"""
        You are an expert sales representative. Write a highly personalized cold outreach email for:
        
        Target Company: {company_name}
        Company Summary: {summary}
        Key Pain Points: {pain_points}
        Buying Signals: {buying_signals}
        Products/Services: {products}
        Latest News/Context: {recent_news}
        Outreach Objective: {outreach_objective}
        
        Source URLs mapping table: {sources_mapping}
        
        Requirements:
        - The subject line must be catchy, relevant, personalized, and professional.
        - The email body should be short (under 150 words), conversational, addressing a specific pain point or buying signal, highlighting how we can help, and must NOT sound generic or overly salesy.
        - The CTA (Call to Action) must be clear, low-friction, and open-ended.
        - Do NOT include placeholder fields (like [My Name] or [Your Company]). Use generic professional sign-offs.
        - You MUST add inline citations like [1] or [2] inside the email body referencing facts derived from specific sources in the mapping table.
        
        CRITICAL: Return ONLY a valid JSON object matching the following structure. Do not include markdown code fences (like ```json), styling, or extra commentary.
        
        {{
            "subject": "Personalized Email Subject",
            "email": "Email body text containing inline citations...",
            "cta": "Clear CTA line"
        }}
        """
        
        loop = asyncio.get_event_loop()
        response = await loop.run_in_executor(
            None,
            partial(
                self.model.generate_content,
                prompt,
                generation_config={"response_mime_type": "application/json"}
            )
        )
        
        logger.info(f"Gemini cold email generation completed for: {company_name}")
        result_text = response.text.strip()
        
        try:
            res = json.loads(result_text)
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse Gemini email JSON output: {result_text}. Error: {e}")
            cleaned = result_text.replace("```json", "").replace("```", "").strip()
            res = json.loads(cleaned)

        # Append bibliography to email body
        if sources_mapping:
            bib = "\n\nSources:\n" + "\n".join([f"[{k}] {v}" for k, v in sources_mapping.items()])
            res["email"] = (res.get("email", "") or "") + bib
            
        return res

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        reraise=True
    )
    async def generate_follow_up_email(
        self,
        company_name: str,
        summary: str,
        pain_points: list,
        buying_signals: list,
        prompt_template: str,
        prior_messages: list,
        reply_snippet: str = None,
        sources_mapping: dict = None
    ) -> dict:
        """Generates a contextual, cited follow-up email using Gemini."""
        logger.info(f"Triggering Gemini follow-up email generation for company: {company_name}")
        sources_mapping = sources_mapping or {}
        
        prior_emails_text = ""
        for i, msg in enumerate(prior_messages, 1):
            prior_emails_text += f"\n--- Sent Email #{i} ---\nSubject: {msg.get('subject')}\nBody:\n{msg.get('body')}\n"
            
        reply_context = ""
        if reply_snippet:
            reply_context = f"\nNote: The prospect replied to our previous thread with: '{reply_snippet}'. Take this reply into account, but write a standard human follow-up to address their point or redirect to the objective (e.g. scheduling a demo)."

        prompt = f"""
        You are an expert sales representative. Write a highly personalized, contextual follow-up email for:
        
        Target Company: {company_name}
        Company Summary: {summary}
        Key Pain Points: {pain_points}
        Buying Signals: {buying_signals}
        
        Prior messages in this conversation thread:{prior_emails_text}
        {reply_context}
        
        Follow-up Step Prompt Template Guidelines:
        {prompt_template}
        
        Source URLs mapping table: {sources_mapping}
        
        Requirements:
        - The follow-up email must be threaded appropriately, keeping the conversation context of previous emails.
        - The subject line must be relevant and consistent (usually replying to the same subject by prefixing with 'Re:' is standard, e.g. "Re: {prior_messages[0]['subject'] if prior_messages else 'GTM Outreach'}").
        - The email body should be short (under 120 words), direct, and value-additive (referencing previous communications without sounding desperate, pushy, or repetitive).
        - The CTA (Call to Action) must be clear, low-friction, and open-ended.
        - Do NOT include placeholder fields (like [My Name] or [Your Company]). Use generic professional sign-offs.
        - You MUST add inline citations like [1] or [2] inside the email body referencing facts derived from specific sources in the mapping table.
        
        CRITICAL: Return ONLY a valid JSON object matching the following structure. Do not include markdown code fences (like ```json), styling, or extra commentary.
        
        {{
            "subject": "Follow-up Email Subject (e.g., Re: prior subject)",
            "email": "Email body text containing inline citations...",
            "cta": "Clear CTA line"
        }}
        """
        
        loop = asyncio.get_event_loop()
        response = await loop.run_in_executor(
            None,
            partial(
                self.model.generate_content,
                prompt,
                generation_config={"response_mime_type": "application/json"}
            )
        )
        
        logger.info(f"Gemini follow-up email generation completed for: {company_name}")
        result_text = response.text.strip()
        
        try:
            res = json.loads(result_text)
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse Gemini follow-up email JSON output: {result_text}. Error: {e}")
            cleaned = result_text.replace("```json", "").replace("```", "").strip()
            res = json.loads(cleaned)

        if sources_mapping:
            bib = "\n\nSources:\n" + "\n".join([f"[{k}] {v}" for k, v in sources_mapping.items()])
            res["email"] = (res.get("email", "") or "") + bib
            
        return res

llm_service = LLMService()
