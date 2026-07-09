from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime

class EmailDraftResponse(BaseModel):
    id: int
    company_id: int
    subject: str
    body: str
    cta: str
    outreach_objective: str
    status: str
    sent_at: Optional[datetime] = None
    error_message: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True

class EmailSendRequest(BaseModel):
    draft_only: bool = Field(True, description="If True, only generates email and saves to DB. If False, generates and sends immediately.")
    outreach_objective: str = Field("Introduction and demo request", description="Objective of the cold email")
    additional_urls: List[str] = Field(default_factory=list, description="Custom URLs to crawl (e.g. blog posts, articles)")
    sequence_id: Optional[int] = Field(None, description="Optional sequence ID to auto-enroll company after enrichment")
    contact_email: Optional[str] = Field(None, description="Optional contact email for outreach")

