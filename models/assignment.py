from pydantic import BaseModel, Field, EmailStr
from enum import Enum
from datetime import date

class AssignmentStatus(str, Enum):
    ACTIVE = "Active"
    TRANSFERRED = "Transferred"
    RESIGNED = "Resigned"


class AssignmentCreate(BaseModel):
    staff_id: int
    hospital_name: str = Field(..., max_length=100)


class AssignmentUpdate(BaseModel):
    status: AssignmentStatus


class Assignment(BaseModel):
    staff_id: int
    hospital_name: str
    assignment_date: date
    status: AssignmentStatus
    
    class Config:
        from_attributes = True