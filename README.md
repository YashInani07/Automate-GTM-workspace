# GTM Automated Workflow Engine

A modular, production-ready FastAPI backend designed to automate company enrichment and personalized cold outreach.

## Features

- **Extensible Scraping Connectors**: Support for Jina AI Reader and direct HTTP scraper (BeautifulSoup-based). Plugin-based registration allows introducing new scraping connectors seamlessly.
- **Normalization Layer**: Maps varying connector outputs to a standardized JSON schema.
- **Gemini AI Integrations**: Analyzes company profiles (summaries, pain points, buying signals, outreach context) and generates personalized cold emails (subject, body, CTA).
- **Extensible CRM Adapters**: Includes modular adapters (configured with a registry pattern) to sync GTM profiles to external CRMs (generic webhook provider initially implemented).
- **SMTP Gmail Delivery**: Integrates with Gmail App Passwords to automatically send cold emails or schedule them as drafts.
- **Zapier Webhooks**: Emits GTM profiles and generated outreach emails to custom Zapier webhooks.
- **Process Auditing & Analytics**: Detailed audit trail mapping every step of the background execution and analytics summarizing process duration and completion rates.
- **Production Enhancements**: Robust exception handling, rate limiting (`slowapi`), retries with exponential backoffs (`tenacity`), and JSON structured logging.

---


