from pydantic import BaseModel
from typing import List
from datetime import datetime

class AIAnalysisResponse(BaseModel):
    id: int
    company_id: int
    summary: str
    pain_points: List[str]
    buying_signals: List[str]
    outreach_context: str
    created_at: datetime

    class Config:
        from_attributes = True
