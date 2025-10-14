from pydantic import BaseModel
from typing import Optional
from datetime import datetime, date

class InventoryStats(BaseModel):
    bloodbank_name: str
    blood_group: str
    total_units: int
    available_units: int
    reserved_units: int
    expiring_soon: int
    used_units: int
    expired_units: int
    last_updated: datetime


class AvailabilityReport(BaseModel):
    bloodbank_name: str
    location: str
    blood_group: str
    available_units: int
    nearest_expiry: Optional[date] = None
    farthest_expiry: Optional[date] = None
    avg_days_to_expiry: Optional[float] = None


class DemandForecast(BaseModel):
    blood_group: str
    total_requests: int
    total_units_requested: int
    avg_units_per_request: float
    units_fulfilled: int
    units_unfulfilled: int
    fulfillment_rate: float
    critical_requests: int
    high_urgency_requests: int
    avg_fulfillment_time_hours: Optional[float] = None


class HospitalSummary(BaseModel):
    hospital_name: str
    location: str
    contact_no: str
    total_patients: int
    total_requests: int
    total_units_requested: int
    units_fulfilled: int
    request_fulfillment_rate: float


class CampaignPerformance(BaseModel):
    camp_id: int
    campaign_name: str
    location: str
    date: date
    target_donors: int
    actual_donors: int
    registered_donors: int
    units_collected: int
    achievement_rate: float
    status: str


class DonorReferralAnalysis(BaseModel):
    donor_name: str
    blood_group: str
    total_donations: int
    total_referrals: int
    successful_referrals: int
    referral_success_rate: float
