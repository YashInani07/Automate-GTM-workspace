from pydantic import BaseModel
from typing import Optional, Any
from datetime import datetime

class CRMSyncResponse(BaseModel):
    id: int
    company_id: int
    provider: str
    status: str
    response_payload: Optional[Any] = None
    error_message: Optional[str] = None
    synced_at: datetime

    class Config:
        from_attributes = True
