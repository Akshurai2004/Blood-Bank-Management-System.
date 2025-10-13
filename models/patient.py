from pydantic import BaseModel, Field, EmailStr
from typing import Optional
from enum import Enum
from datetime import datetime

class PatientBase(BaseModel):
    name: str = Field(..., max_length=100)
    age: int = Field(..., ge=1, lt=150)
    gender: Gender
    address: Optional[str] = Field(None, max_length=255)
    contact_no: str = Field(..., max_length=15, pattern=r'^\d{10,15}$')
    blood_group_required: str = Field(..., max_length=5, pattern=r'^(A|B|AB|O)[+-]$')
    hospital_name: str = Field(..., max_length=100)
    medical_condition: Optional[str] = None
    emergency_contact: Optional[str] = Field(None, max_length=15)


class PatientCreate(PatientBase):
    pass


class PatientUpdate(BaseModel):
    name: Optional[str] = None
    age: Optional[int] = Field(None, ge=1, lt=150)
    gender: Optional[Gender] = None
    address: Optional[str] = None
    contact_no: Optional[str] = None
    blood_group_required: Optional[str] = None
    hospital_name: Optional[str] = None
    medical_condition: Optional[str] = None
    emergency_contact: Optional[str] = None


class Patient(PatientBase):
    patient_id: int
    registration_date: datetime
    
    class Config:
        from_attributes = True