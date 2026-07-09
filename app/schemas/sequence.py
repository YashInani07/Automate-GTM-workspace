from pydantic import BaseModel, Field, EmailStr
from typing import Optional, List
from datetime import datetime


class SequenceStepCreate(BaseModel):
    step_number: int = Field(..., ge=1)
    delay_days: int = Field(0, ge=0)
    channel: str = Field("email", max_length=50)
    prompt_template: str
    auto_send: bool = True


class SequenceStepResponse(BaseModel):
    id: int
    sequence_id: int
    step_number: int
    delay_days: int
    channel: str
    prompt_template: str
    auto_send: bool
    created_at: datetime

    class Config:
        from_attributes = True


class SequenceCreate(BaseModel):
    name: str = Field(..., max_length=255)
    description: Optional[str] = None
    default_objective: str = Field(
        "Introduce our solutions and request a brief demo", max_length=500
    )
    is_active: bool = True
    steps: List[SequenceStepCreate] = Field(default_factory=list)


class SequenceUpdate(BaseModel):
    name: Optional[str] = Field(None, max_length=255)
    description: Optional[str] = None
    default_objective: Optional[str] = Field(None, max_length=500)
    is_active: Optional[bool] = None
    steps: Optional[List[SequenceStepCreate]] = None


class SequenceResponse(BaseModel):
    id: int
    name: str
    description: Optional[str] = None
    default_objective: str
    is_active: bool
    created_at: datetime
    updated_at: datetime
    steps: List[SequenceStepResponse] = Field(default_factory=list)

    class Config:
        from_attributes = True


class EnrollmentCreate(BaseModel):
    sequence_id: int
    contact_email: EmailStr
    start_immediately: bool = True


class OutreachMessageResponse(BaseModel):
    id: int
    enrollment_id: int
    step_id: Optional[int] = None
    step_number: int
    subject: str
    body: str
    cta: str
    recipient_email: str
    status: str
    scheduled_at: Optional[datetime] = None
    sent_at: Optional[datetime] = None
    message_id: Optional[str] = None
    error_message: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True


class ReplyEventResponse(BaseModel):
    id: int
    enrollment_id: int
    from_email: str
    subject: str
    snippet: str
    detected_at: datetime

    class Config:
        from_attributes = True


class EnrollmentResponse(BaseModel):
    id: int
    company_id: int
    sequence_id: int
    contact_email: str
    status: str
    current_step: int
    enrolled_at: datetime
    completed_at: Optional[datetime] = None
    messages: List[OutreachMessageResponse] = Field(default_factory=list)
    reply_events: List[ReplyEventResponse] = Field(default_factory=list)

    class Config:
        from_attributes = True
