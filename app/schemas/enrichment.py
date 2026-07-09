from pydantic import BaseModel
from typing import Optional, Any
from datetime import datetime

class EnrichmentResponse(BaseModel):
    id: int
    company_id: int
    connector: str
    raw_data: Optional[Any] = None
    clean_data: Optional[Any] = None
    created_at: datetime

    class Config:
        from_attributes = True
