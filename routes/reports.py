from services.report_service import ReportService
from fastapi import APIRouter, Query
from typing import Optional
from models.common import SuccessResponse

router = APIRouter()

@router.get("/inventory-stats", response_model=SuccessResponse)
async def get_inventory_stats():
    """Get current inventory statistics"""
    result = ReportService.get_inventory_stats()
    return SuccessResponse(message="Inventory statistics retrieved", data=result)

@router.get("/hospital-summary", response_model=SuccessResponse)
async def get_hospital_summary():
    """Get hospital-wise request summary"""
    result = ReportService.get_hospital_summary()
    return SuccessResponse(message="Hospital summary retrieved", data=result)

@router.get("/campaign-performance", response_model=SuccessResponse)
async def get_campaign_performance(camp_id: Optional[int] = None):
    """Get campaign performance report"""
    result = ReportService.get_campaign_performance(camp_id)
    return SuccessResponse(message="Campaign performance retrieved", data=result)

@router.get("/donor-referrals", response_model=SuccessResponse)
async def analyze_donor_referrals():
    """Analyze donor referral network"""
    result = ReportService.analyze_donor_referrals()
    return SuccessResponse(message="Donor referral analysis completed", data=result)

@router.get("/performance-analysis", response_model=SuccessResponse)
async def analyze_performance():
    """Analyze system performance metrics"""
    result = ReportService.analyze_performance()
    return SuccessResponse(message="Performance analysis completed", data=result)

@router.get("/staff-assignments", response_model=SuccessResponse)
async def get_staff_assignments(hospital_name: Optional[str] = None):
    """Get staff assignment report"""
    result = ReportService.get_staff_assignments(hospital_name)
    return SuccessResponse(message="Staff assignments retrieved", data=result)

