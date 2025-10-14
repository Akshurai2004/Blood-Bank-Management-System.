from pydantic import BaseModel
from typing import Optional
from enum import Enum
from datetime import datetime

class AlertType(str, Enum):
    LOW_STOCK = "Low_Stock"
    EXPIRING_SOON = "Expiring_Soon"
    CRITICAL_REQUEST = "Critical_Request"
    CAMPAIGN_DUE = "Campaign_Due"
    SYSTEM = "System"


class Severity(str, Enum):
    LOW = "Low"
    MEDIUM = "Medium"
    HIGH = "High"
    CRITICAL = "Critical"


class Alert(BaseModel):
    alert_id: int
    alert_type: AlertType
    blood_group: Optional[str] = None
    bloodbank_name: Optional[str] = None
    hospital_name: Optional[str] = None
    message: str
    severity: Severity
    is_read: bool
    action_required: bool
    created_at: datetime
    read_at: Optional[datetime] = None
    
    class Config:
        from_attributes = True