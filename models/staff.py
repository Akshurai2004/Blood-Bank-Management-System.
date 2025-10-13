from datetime import date
from enum import Enum
from pydantic import BaseModel, Field, EmailStr
from typing import Optional


class StaffRole(str, Enum):
    DOCTOR = "Doctor"
    NURSE = "Nurse"
    LAB_TECHNICIAN = "Lab_Technician"
    ADMINISTRATOR = "Administrator"
    COORDINATOR = "Coordinator"


class StaffBase(BaseModel):
    name: str = Field(..., max_length=100)
    role: StaffRole
    skill_set: Optional[str] = None
    contact_no: str = Field(..., max_length=15, pattern=r'^\d{10,15}$')
    email: Optional[EmailStr] = None


class StaffCreate(StaffBase):
    pass


class StaffUpdate(BaseModel):
    name: Optional[str] = Field(None, max_length=100)
    role: Optional[StaffRole] = None
    skill_set: Optional[str] = None
    contact_no: Optional[str] = Field(None, max_length=15)
    email: Optional[EmailStr] = None


class Staff(StaffBase):
    staff_id: int
    joining_date: date
    is_active: bool
    
    class Config:
        from_attributes = True