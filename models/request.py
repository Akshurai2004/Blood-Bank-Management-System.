from pydantic import BaseModel, Field, EmailStr
from typing import Optional
from enum import Enum
from datetime import datetime

class RequestStatus(str, Enum):
    PENDING = "Pending"
    PROCESSING = "Processing"
    FULFILLED = "Fulfilled"
    PARTIALLY_FULFILLED = "Partially_Fulfilled"
    DENIED = "Denied"
    CANCELLED = "Cancelled"


class UrgencyLevel(str, Enum):
    LOW = "Low"
    MEDIUM = "Medium"
    HIGH = "High"
    CRITICAL = "Critical"


class RequestBase(BaseModel):
    patient_name: str = Field(..., max_length=100)
    bloodbank_name: Optional[str] = None
    required_units: int = Field(default=1, ge=1)
    urgency_level: UrgencyLevel = UrgencyLevel.MEDIUM
    requested_by: Optional[str] = Field(None, max_length=100)
    notes: Optional[str] = None


class RequestCreate(RequestBase):
    pass


class RequestUpdate(BaseModel):
    status: Optional[RequestStatus] = None
    bloodbank_name: Optional[str] = None
    required_units: Optional[int] = Field(None, ge=1)
    urgency_level: Optional[UrgencyLevel] = None
    approved_by: Optional[str] = None
    notes: Optional[str] = None


class Request(RequestBase):
    request_id: int
    request_date: datetime
    status: RequestStatus
    priority: int
    approved_by: Optional[str] = None
    fulfilled_date: Optional[datetime] = None
    
    class Config:
        from_attributes = True