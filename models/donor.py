from pydantic import BaseModel, Field, EmailStr
from typing import Optional
from datetime import date
from enum import Enum

class Gender(str, Enum):
    MALE = "M"
    FEMALE = "F"
    OTHER = "O"


class DonorBase(BaseModel):
    age: int = Field(..., ge=18, le=65)
    gender: Gender
    blood_group: str = Field(..., max_length=5, pattern=r'^(A|B|AB|O)[+-]$')
    contact_no: str = Field(..., max_length=15, pattern=r'^\d{10,15}$')
    email: Optional[EmailStr] = None
    address: Optional[str] = Field(None, max_length=255)
    camp_id: Optional[int] = None


class DonorCreate(DonorBase):
    donor_name: str = Field(..., max_length=100)


class DonorUpdate(BaseModel):
    age: Optional[int] = Field(None, ge=18, le=65)
    gender: Optional[Gender] = None
    blood_group: Optional[str] = None
    contact_no: Optional[str] = None
    email: Optional[EmailStr] = None
    address: Optional[str] = None
    camp_id: Optional[int] = None


class Donor(DonorBase):
    donor_name: str
    last_donation_date: Optional[date] = None
    total_donations: int
    registration_date: date
    is_active: bool
    
    class Config:
        from_attributes = True


class DonorEligibility(BaseModel):
    donor_name: str
    is_eligible: bool
    message: str
    days_since_last_donation: Optional[int] = None
    last_donation_date: Optional[date] = None
    can_donate_now: str
