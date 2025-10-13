from datetime import time, date
from pydantic import BaseModel, Field, EmailStr
from typing import Optional
from enum import Enum

class CampaignStatus(str, Enum):
    SCHEDULED = "Scheduled"
    ONGOING = "Ongoing"
    COMPLETED = "Completed"
    CANCELLED = "Cancelled"


class CampaignBase(BaseModel):
    campaign_name: str = Field(..., max_length=150)
    location: str = Field(..., max_length=100)
    date: date
    start_time: Optional[time] = None
    end_time: Optional[time] = None
    organized_by: Optional[str] = Field(None, max_length=100)
    target_donors: int = Field(default=50, ge=0)
    bloodbank_name: Optional[str] = None


class CampaignCreate(CampaignBase):
    pass


class CampaignUpdate(BaseModel):
    campaign_name: Optional[str] = None
    location: Optional[str] = None
    date: Optional[date] = None
    start_time: Optional[time] = None
    end_time: Optional[time] = None
    organized_by: Optional[str] = None
    target_donors: Optional[int] = None
    actual_donors: Optional[int] = None
    bloodbank_name: Optional[str] = None
    status: Optional[CampaignStatus] = None


class Campaign(CampaignBase):
    camp_id: int
    actual_donors: int
    status: CampaignStatus
    
    class Config:
        from_attributes = True