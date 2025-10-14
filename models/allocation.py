from pydantic import BaseModel, Field
from typing import Optional
from enum import Enum
from datetime import datetime

class DeliveryStatus(str, Enum):
    PENDING = "Pending"
    IN_TRANSIT = "In_Transit"
    DELIVERED = "Delivered"
    FAILED = "Failed"


class AllocationBase(BaseModel):
    request_id: int
    unit_id: int
    allocated_by: Optional[str] = Field(None, max_length=100)
    received_by: Optional[str] = Field(None, max_length=100)
    notes: Optional[str] = None


class AllocationCreate(AllocationBase):
    pass


class AllocationUpdate(BaseModel):
    delivery_status: Optional[DeliveryStatus] = None
    received_by: Optional[str] = None
    notes: Optional[str] = None


class Allocation(AllocationBase):
    allocation_id: int
    allocation_date: datetime
    delivery_status: DeliveryStatus
    delivery_date: Optional[datetime] = None
    
    class Config:
        from_attributes = True