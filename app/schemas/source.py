from pydantic import BaseModel, Field, field_validator
from datetime import datetime

class SourceCreate(BaseModel):
    url: str = Field(..., max_length=500, description="The URL of the source")

    @field_validator("url")
    @classmethod
    def validate_url(cls, v: str) -> str:
        val = v.strip()
        if not val.startswith("http://") and not val.startswith("https://"):
            val = "https://" + val
        return val

class SourceResponse(BaseModel):
    id: int
    company_id: int
    url: str
    created_at: datetime

    class Config:
        from_attributes = True
