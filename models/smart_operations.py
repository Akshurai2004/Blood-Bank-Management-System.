from pydantic import BaseModel
from typing import Optional
from datetime import date

class SmartAllocationResult(BaseModel):
    request_id: int
    status: str
    allocated_units: int
    message: str


class CompatibleBloodSource(BaseModel):
    bloodbank_name: str
    location: str
    contact_no: str
    blood_group: str
    available_units: int
    nearest_expiry: date
    available_components: str
    unit_ids: Optional[str] = None