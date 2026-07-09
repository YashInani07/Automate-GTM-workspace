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

## Directory Layout

```
app/
├── main.py                # App configuration, rate limiters, middlewares, routes
├── core/
│   ├── config.py          # Config loader and validation
│   ├── database.py        # SQLAlchemy async engine & session maker
│   ├── logging.py         # JSON structured log formatter
│   └── rate_limit.py      # IP-based API rate limiter
├── models/                # SQLAlchemy database models
├── schemas/               # Pydantic validation models
├── crud/                  # SQL async helpers and analytics epoch math
├── connectors/            # Scraper plugin system (Jina, BeautifulSoup)
├── normalizers/           # Heuristic HTML/Markdown clean-up normalizers
├── crm/                   # CRM sync plugin adapter system
└── services/              # Third-party integrations (Gemini, Gmail SMTP, Pipeline)
```

---

## Getting Started

### 1. Environment Configurations

Configure your `.env` file in the root directory (based on `.env.example`):
```env
PROJECT_NAME="GTM Automated Workflow"
DATABASE_URL="postgresql+asyncpg://postgres:postgres@db:5432/postgres"
DATABASE_URL_SYNC="postgresql+psycopg2://postgres:postgres@db:5432/postgres"
JINA_API_KEY="jina_..."
GEMINI_API_KEY="AQ..."
ZAPIER_WEBHOOK_URL="https://hooks.zapier.com/..."
CRM_WEBHOOK_URL="https://hooks.yourcrm.com/..."
GMAIL_USER="your-email@gmail.com"
GMAIL_APP_PASSWORD="your-app-password"
```

### 2. Running with Docker Compose

Start the services (PostgreSQL database and the FastAPI web server):
```bash
docker compose up --build -d
```

Apply database migrations:
```bash
docker compose exec web alembic upgrade head
```

---

## API Documentation & Verification

- Swagger UI docs: `http://localhost:8500/docs`
- Health check: `http://localhost:8500/api/v1/health`

### Testing the Workflow

#### 1. Create a Company Record
```bash
curl -X POST http://localhost:8500/api/v1/companies \
  -H "Content-Type: application/json" \
  -d '{"name": "Stripe", "domain": "stripe.com"}'
```

#### 2. Trigger the Enrichment Pipeline
```bash
curl -X POST http://localhost:8500/api/v1/companies/1/enrich?connector=jina \
  -H "Content-Type: application/json" \
  -d '{"draft_only": true, "outreach_objective": "Schedule a brief demo of our workflow automatons"}'
```
*Note: Set `draft_only` to `false` and configure Gmail credentials to automatically send the generated cold email.*

#### 3. Fetch Analytics
```bash
curl http://localhost:8500/api/v1/analytics
```
# Automate-GTM-workspace
