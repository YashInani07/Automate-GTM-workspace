from pydantic import BaseModel

class AnalyticsResponse(BaseModel):
    companies_processed: int
    successful_enrichments: int
    failed_enrichments: int
    emails_generated: int
    emails_sent: int
    average_processing_time_seconds: float
