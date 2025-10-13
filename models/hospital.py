from pydantic import BaseModel, Field, EmailStr
from typing import Optional


class HospitalBase(BaseModel):
    location: str = Field(..., max_length=100)
    contact_no: str = Field(..., max_length=15, pattern=r'^\d{10,15}$')
    email: Optional[EmailStr] = None


class HospitalCreate(HospitalBase):
    hospital_name: str = Field(..., max_length=100)


class HospitalUpdate(HospitalBase):
    location: Optional[str] = Field(None, max_length=100)
    contact_no: Optional[str] = Field(None, max_length=15, pattern=r'^\d{10,15}$')


class Hospital(HospitalBase):
    hospital_name: str
    
    class Config:
        from_attributes = True