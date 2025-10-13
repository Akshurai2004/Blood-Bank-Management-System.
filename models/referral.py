from pydantic import BaseModel, Field, EmailStr
from datetime import date
from enum import Enum

class ReferralStatus(str, Enum):
    PENDING = "Pending"
    ACCEPTED = "Accepted"
    DONATED = "Donated"
    DECLINED = "Declined"


class ReferralCreate(BaseModel):
    donor_name: str = Field(..., max_length=100)
    referred_donor_name: str = Field(..., max_length=100)


class ReferralUpdate(BaseModel):
    status: ReferralStatus


class Referral(BaseModel):
    donor_name: str
    referred_donor_name: str
    referral_date: date
    status: ReferralStatus
    
    class Config:
        from_attributes = True