from pydantic import BaseModel, Field, EmailStr
from typing import Optional
from enum import Enum
from datetime import date, datetime

class BloodUnitStatus(str, Enum):
    AVAILABLE = "Available"
    RESERVED = "Reserved"
    USED = "Used"
    EXPIRED = "Expired"
    QUARANTINE = "Quarantine"


class ComponentType(str, Enum):
    WHOLE_BLOOD = "Whole Blood"
    RBC = "RBC"
    PLASMA = "Plasma"
    PLATELETS = "Platelets"
    CRYOPRECIPITATE = "Cryoprecipitate"


class TestStatus(str, Enum):
    PENDING = "Pending"
    CLEARED = "Cleared"
    REJECTED = "Rejected"


class BloodUnitBase(BaseModel):
    donor_name: Optional[str] = None
    bloodbank_name: str = Field(..., max_length=100)
    blood_group: str = Field(..., max_length=5, pattern=r'^(A|B|AB|O)[+-]$')
    quantity: int = Field(default=1, ge=1)
    collection_date: date
    expiration_date: date
    component: ComponentType = ComponentType.WHOLE_BLOOD
    storage_location: Optional[str] = Field(None, max_length=50)
    transaction_id: Optional[int] = None


class BloodUnitCreate(BloodUnitBase):
    pass


class BloodUnitUpdate(BaseModel):
    status: Optional[BloodUnitStatus] = None
    test_status: Optional[TestStatus] = None
    storage_location: Optional[str] = None


class BloodUnit(BloodUnitBase):
    unit_id: int
    status: BloodUnitStatus
    test_status: TestStatus
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True