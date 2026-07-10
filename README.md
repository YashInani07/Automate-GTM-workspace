# GTM Automated Workflow Engine

[![Deploy to Render](https://img.shields.io/badge/Deploy-Render-blue)](https://gtm-web-86hu.onrender.com)
🚀 **Live URL:** [https://gtm-web-86hu.onrender.com](https://gtm-web-86hu.onrender.com)

The GTM (Go-To-Market) Automated Workflow Engine is an intelligent, agent-driven platform designed to automate lead enrichment, company profile research, and highly personalized sales outreach. By combining web parsing, large language model analysis, and background automation queues, the engine enables growth and sales teams to scale high-quality outreach campaigns while maintaining the context-rich touch of a human researcher.

## Core Capabilities

### 1. Extensible Web Harvesting & Parsing
The engine features a modular connector framework that navigates and harvests company data:
- **Direct HTML Parsing**: Processes direct HTML responses from targeted target pages using advanced DOM parsers.
- **Markdown Conversion**: Utilizes reader APIs to clean clutter and parse raw web content into easily digestible Markdown.
- **Source Management**: Keeps track of custom crawl paths such as company blog posts, news releases, LinkedIn profiles, and product pages.

### 2. Standardized Normalization Engine
Raw harvested website data is run through a strict schema mapping layer. This transforms disparate web structures, contact forms, and textual content into normalized, structured corporate metadata profiles.

### 3. AI-Driven Intent & Pain-Point Analysis
Using advanced Large Language Models (Gemini AI), the workflow reads the normalized company profiles to identify:
- **Corporate Summary**: High-level value propositions, target audiences, and core product offerings.
- **Pain Points**: Concrete challenges and scaling friction points the company is likely experiencing.
- **Buying Signals**: Key trigger events (recent funding, product updates, hiring signals, expansion announcements).
- **Outreach Context**: Custom context guides explaining exactly how to position solutions during outreach.

### 4. Hyper-Personalized Outreach Drafting
Once research is completed, the generative engine drafts personalized emails tailored directly to the specific target audience and objective:
- **Contextual Subjects**: Eye-catching subject lines relevant to the company's domain and recent updates.
- **Personalized Bodies**: Content referencing the specific pain points and signals found during research.
- **CTAs (Call to Actions)**: Value-driven, direct calls to action requesting brief discussions or demos.

### 5. Multi-Channel Synchronization & Dispatch
- **Drafting Mode**: Places generated campaigns directly into draft states for review.
- **SMTP Mailer**: Dispatches outreach campaigns securely through automated email workspace integrations.
- **CRM Webhooks**: Seamlessly emits structured company profiles and outreach data to target webhooks (like Zapier, HubSpot, Salesforce).
- **Sequence Timeline Manager**: Orchestrates multiple stages of emails, scheduling delay intervals, and monitoring campaign progress.
