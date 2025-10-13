from pydantic import BaseModel, Field, EmailStr
from typing import Optional


class BloodBankBase(BaseModel):
    location: str = Field(..., max_length=100)
    contact_no: str = Field(..., max_length=15, pattern=r'^\d{10,15}$')
    established_year: int = Field(..., ge=1900, le=2100)
    email: Optional[EmailStr] = None
    license_number: Optional[str] = Field(None, max_length=50)
    capacity: int = Field(default=1000, ge=0)


class BloodBankCreate(BloodBankBase):
    bloodbank_name: str = Field(..., max_length=100)


class BloodBankUpdate(BloodBankBase):
    location: Optional[str] = None
    contact_no: Optional[str] = None
    established_year: Optional[int] = None
    capacity: Optional[int] = None


class BloodBank(BloodBankBase):
    bloodbank_name: str
    
    class Config:
        from_attributes = True