import re
from pydantic import BaseModel, Field, field_validator
from typing import Optional
from datetime import datetime

DOMAIN_REGEX = re.compile(
    r"^(?:[a-zA-Z0-9](?:[a-zA-Z0-9\-]{0,61}[a-zA-Z0-9])?\.)+[a-zA-Z]{2,6}$"
)

class CompanyBase(BaseModel):
    name: str = Field(..., max_length=255, description="The name of the company")
    domain: str = Field(..., max_length=255, description="The domain of the company (e.g. stripe.com)")
    industry: Optional[str] = Field(None, max_length=255)
    notes: Optional[str] = None

    @field_validator("domain")
    @classmethod
    def validate_domain(cls, v: str) -> str:
        val = v.strip().lower()
        if val.startswith("https://"):
            val = val[8:]
        if val.startswith("http://"):
            val = val[7:]
        if val.startswith("www."):
            val = val[4:]
        val = val.split("/")[0]
        if not DOMAIN_REGEX.match(val):
            raise ValueError("Invalid domain format. Must be a valid domain like example.com")
        return val

class CompanyCreate(BaseModel):
    name: str = Field(..., max_length=255)
    domain: str = Field(..., max_length=255)

    @field_validator("domain")
    @classmethod
    def validate_domain(cls, v: str) -> str:
        return CompanyBase.validate_domain(v)

class CompanyUpdate(BaseModel):
    name: Optional[str] = Field(None, max_length=255)
    domain: Optional[str] = Field(None, max_length=255)
    industry: Optional[str] = Field(None, max_length=255)
    notes: Optional[str] = None

    @field_validator("domain")
    @classmethod
    def validate_domain(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return v
        return CompanyBase.validate_domain(v)

class CompanyResponse(CompanyBase):
    id: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
