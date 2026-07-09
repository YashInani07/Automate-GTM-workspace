import logging
import httpx
from datetime import datetime, timezone
from app.core.database import SessionLocal
from app.core.config import settings
from app.connectors.registry import registry as connector_registry
from app.normalizers import get_normalizer
from app.services.llm import llm_service
from app.services.email import gmail_service
from app.crm.registry import crm_registry
import app.crud as crud

logger = logging.getLogger(__name__)

async def run_enrichment_pipeline(
    company_id: int,
    connector_name: str,
    outreach_objective: str,
    draft_only: bool = True,
    additional_urls: list = None,
    sequence_id: int = None,
    contact_email: str = None
):
    logger.info(f"Starting pipeline run for company ID {company_id} using connector {connector_name}")
    
    async with SessionLocal() as db:
        # 1. Fetch Company
        company = await crud.get_company(db, company_id)
        if not company:
            logger.error(f"Company ID {company_id} not found. Pipeline aborted.")
            return

        await crud.create_audit_log(db, company_id, "pipeline_started", "success", {
            "connector": connector_name,
            "objective": outreach_objective,
            "draft_only": draft_only,
            "additional_urls": additional_urls
        })

        # 2. Enrichment
        await crud.create_audit_log(db, company_id, "enrichment_started", "success", {"connector": connector_name})
        connector = connector_registry.get_connector(connector_name)
        if not connector:
            err_msg = f"Connector '{connector_name}' not found in registry."
            logger.error(err_msg)
            await crud.create_audit_log(db, company_id, "enriched", "failed", {"error": err_msg})
            return

        try:
            # Query pre-saved database sources
            db_sources = await crud.get_company_sources(db, company_id)
            db_source_urls = [s.url for s in db_sources]

            # Merge with form additional URLs, removing duplicates
            urls_to_scrape = []
            if db_source_urls:
                urls_to_scrape.extend(db_source_urls)
            if additional_urls:
                for url in additional_urls:
                    url_clean = url.strip()
                    if url_clean and url_clean not in urls_to_scrape:
                        urls_to_scrape.append(url_clean)

            # Fetch main website domain url
            raw_data = await connector.fetch(company.domain)
            normalizer = get_normalizer(connector_name)
            clean_data = normalizer.normalize(raw_data)
            
            enrichment_rec = await crud.create_enrichment(
                db, company_id, connector_name, raw_data, clean_data
            )
            await crud.create_audit_log(db, company_id, "enriched", "success", {
                "enrichment_id": enrichment_rec.id,
                "company_extracted": clean_data.get("company"),
                "emails_found": len(clean_data.get("contact_information", {}).get("emails", []))
            })
            
            # Setup sources mapping dictionary
            sources_mapping = {
                "0": f"https://{company.domain}"
            }
            source_contents = [
                f"[Source #0] URL: https://{company.domain}\nContent:\n{clean_data.get('description', '')}"
            ]
            
            # Scrape additional sources
            for idx, url in enumerate(urls_to_scrape, start=1):
                await crud.create_audit_log(db, company_id, "enrichment_started", "success", {"url": url})
                try:
                    add_raw = await connector.fetch(url)
                    add_clean = normalizer.normalize(add_raw)
                    
                    sources_mapping[str(idx)] = url
                    source_contents.append(f"[Source #{idx}] URL: {url}\nContent:\n{add_clean.get('description', '') or ''}")
                    
                    # Merge array metrics
                    clean_data["products"] = list(set((clean_data.get("products", []) or []) + (add_clean.get("products", []) or [])))
                    clean_data["recent_news"] = list(set((clean_data.get("recent_news", []) or []) + (add_clean.get("recent_news", []) or [])))
                    clean_data["social_links"] = list(set((clean_data.get("social_links", []) or []) + (add_clean.get("social_links", []) or [])))
                    clean_data["careers"] = list(set((clean_data.get("careers", []) or []) + (add_clean.get("careers", []) or [])))
                    
                    clean_emails = clean_data.get("contact_information", {}).get("emails", []) or []
                    add_emails = add_clean.get("contact_information", {}).get("emails", []) or []
                    clean_data["contact_information"]["emails"] = list(set(clean_emails + add_emails))
                    
                    clean_phones = clean_data.get("contact_information", {}).get("phones", []) or []
                    add_phones = add_clean.get("contact_information", {}).get("phones", []) or []
                    clean_data["contact_information"]["phones"] = list(set(clean_phones + add_phones))
                    
                    # Save additional enrichment record
                    await crud.create_enrichment(db, company_id, connector_name, add_raw, add_clean)
                    await crud.create_audit_log(db, company_id, "enriched", "success", {"url": url})
                except Exception as sub_err:
                    logger.error(f"Failed to scrape source {url}: {sub_err}")
                    await crud.create_audit_log(db, company_id, "enriched", "failed", {"url": url, "error": str(sub_err)})

            # Replace description with combined content index-tagged
            clean_data["description"] = "\n\n".join(source_contents)
            clean_data["sources_mapping"] = sources_mapping
        except Exception as e:
            err_msg = f"Enrichment scraping failed: {str(e)}"
            logger.exception(err_msg)
            await crud.create_audit_log(db, company_id, "enriched", "failed", {"error": err_msg})
            return

        # 3. AI Profile Analysis
        await crud.create_audit_log(db, company_id, "ai_analysis_started", "success")
        try:
            analysis_dict = await llm_service.analyze_company_profile(clean_data)
            analysis_rec = await crud.create_ai_analysis(
                db=db,
                company_id=company_id,
                summary=analysis_dict.get("summary", ""),
                pain_points=analysis_dict.get("pain_points", []),
                buying_signals=analysis_dict.get("buying_signals", []),
                outreach_context=analysis_dict.get("outreach_context", "")
            )
            # Update company fields if empty
            company.notes = company.notes or analysis_dict.get("summary")
            company.industry = company.industry or clean_data.get("industry") or "Technology"
            db.add(company)
            await db.commit()

            await crud.create_audit_log(db, company_id, "ai_analyzed", "success", {
                "analysis_id": analysis_rec.id
            })
        except Exception as e:
            err_msg = f"LLM profile analysis failed: {str(e)}"
            logger.exception(err_msg)
            await crud.create_audit_log(db, company_id, "ai_analyzed", "failed", {"error": err_msg})
            return

        # 4. Cold Email Drafting
        await crud.create_audit_log(db, company_id, "email_drafting_started", "success")
        try:
            email_dict = await llm_service.generate_cold_email(
                company_name=clean_data.get("company", company.name),
                summary=analysis_dict.get("summary", ""),
                pain_points=analysis_dict.get("pain_points", []),
                buying_signals=analysis_dict.get("buying_signals", []),
                products=clean_data.get("products", []),
                recent_news=clean_data.get("recent_news", []),
                outreach_objective=outreach_objective,
                sources_mapping=clean_data.get("sources_mapping", {})
            )
            email_rec = await crud.create_email_draft(
                db=db,
                company_id=company_id,
                subject=email_dict.get("subject", ""),
                body=email_dict.get("email", ""),
                cta=email_dict.get("cta", ""),
                outreach_objective=outreach_objective,
                status="draft"
            )
            await crud.create_audit_log(db, company_id, "email_drafted", "success", {
                "draft_id": email_rec.id
            })
        except Exception as e:
            err_msg = f"LLM email generation failed: {str(e)}"
            logger.exception(err_msg)
            await crud.create_audit_log(db, company_id, "email_drafted", "failed", {"error": err_msg})
            return

        # 5. Zapier Integration
        if settings.ZAPIER_WEBHOOK_URL:
            await crud.create_audit_log(db, company_id, "zapier_webhook_started", "success")
            try:
                zapier_payload = {
                    "company_id": company_id,
                    "company_name": company.name,
                    "domain": company.domain,
                    "profile": clean_data,
                    "ai_summary": analysis_dict,
                    "email_draft": email_dict
                }
                async with httpx.AsyncClient(timeout=10.0) as client:
                    resp = await client.post(settings.ZAPIER_WEBHOOK_URL, json=zapier_payload)
                    resp.raise_for_status()
                await crud.create_audit_log(db, company_id, "zapier_webhook_completed", "success")
            except Exception as e:
                logger.error(f"Zapier webhook push failed: {e}")
                await crud.create_audit_log(db, company_id, "zapier_webhook_completed", "failed", {"error": str(e)})
        else:
            await crud.create_audit_log(db, company_id, "zapier_webhook_skipped", "success")

        # 6. CRM Webhook Sync
        await crud.create_audit_log(db, company_id, "crm_sync_started", "success")
        crm = crm_registry.get_crm("webhook")
        if crm:
            try:
                company_payload = {"id": company.id, "name": company.name, "domain": company.domain}
                sync_res = await crm.sync_company(
                    company_data=company_payload,
                    analysis_data=analysis_dict,
                    email_data=email_dict
                )
                
                await crud.create_crm_sync(
                    db=db,
                    company_id=company_id,
                    provider="webhook",
                    status=sync_res.get("status", "failed"),
                    response_payload=sync_res,
                    error_message=sync_res.get("error")
                )
                await crud.create_audit_log(
                    db,
                    company_id,
                    "crm_synced",
                    "success" if sync_res.get("status") == "success" else "failed",
                    {"response": sync_res}
                )
            except Exception as e:
                logger.error(f"CRM sync failed: {e}")
                await crud.create_crm_sync(
                    db=db,
                    company_id=company_id,
                    provider="webhook",
                    status="failed",
                    error_message=str(e)
                )
                await crud.create_audit_log(db, company_id, "crm_synced", "failed", {"error": str(e)})

        # 7. Gmail Email Delivery
        if not draft_only and gmail_service.is_configured and not sequence_id:
            await crud.create_audit_log(db, company_id, "email_sending_started", "success")
            recipient = ""
            emails_found = clean_data.get("contact_information", {}).get("emails", [])
            if emails_found:
                recipient = emails_found[0]
            else:
                recipient = settings.GMAIL_USER
                logger.info(f"No emails found. Self-sending email to {recipient} as fallback.")

            try:
                await crud.update_email_draft_status(db, email_rec.id, "sending")
                
                mail_res = await gmail_service.send_email(
                    recipient_email=recipient,
                    subject=email_rec.subject,
                    body=f"{email_rec.body}\n\n{email_rec.cta}"
                )
                
                if mail_res.get("status") == "sent":
                    await crud.update_email_draft_status(
                        db, email_rec.id, "sent", sent_at=datetime.now(timezone.utc)
                    )
                    await crud.create_audit_log(db, company_id, "email_sent", "success", {
                        "recipient": recipient
                    })
                else:
                    err = mail_res.get("error", "delivery failure")
                    await crud.update_email_draft_status(db, email_rec.id, "failed", error_message=err)
                    await crud.create_audit_log(db, company_id, "email_sent", "failed", {"error": err})
            except Exception as e:
                logger.error(f"Gmail delivery failed: {e}")
                await crud.update_email_draft_status(db, email_rec.id, "failed", error_message=str(e))
                await crud.create_audit_log(db, company_id, "email_sent", "failed", {"error": str(e)})
        else:
            reason = "draft_only mode" if draft_only else "Gmail not configured"
            if sequence_id:
                reason = "handled by sequence workflow"
            await crud.create_audit_log(db, company_id, "email_sending_skipped", "success", {
                "reason": reason
            })

        # Auto-enroll in sequence if requested
        if sequence_id:
            try:
                from app.services.sequence_engine import sequence_engine
                
                recipient = contact_email
                if not recipient:
                    emails_found = clean_data.get("contact_information", {}).get("emails", [])
                    if emails_found:
                        recipient = emails_found[0]
                    else:
                        recipient = settings.GMAIL_USER
                
                await sequence_engine.enroll_company_from_pipeline(
                    db=db,
                    company_id=company_id,
                    sequence_id=sequence_id,
                    contact_email=recipient,
                    draft_subject=email_rec.subject,
                    draft_body=email_rec.body,
                    draft_cta=email_rec.cta,
                    draft_only=draft_only
                )
            except Exception as se_err:
                logger.error(f"Failed to auto-enroll company in sequence {sequence_id}: {se_err}")
                await crud.create_audit_log(db, company_id, "sequence_enroll_failed", "failed", {"error": str(se_err)})

        await crud.create_audit_log(db, company_id, "pipeline_completed", "success")
        logger.info(f"Pipeline completed successfully for company ID {company_id}")

