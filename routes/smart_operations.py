from services.smart_service import SmartService
from fastapi import APIRouter, Query
from typing import Optional
from models.common import SuccessResponse

router = APIRouter()

@router.post("/allocate-blood/{request_id}", response_model=SuccessResponse)
async def allocate_blood_smart(request_id: int):
    """Smart blood allocation using AI-powered matching"""
    result = SmartService.allocate_blood_smart(request_id)
    return SuccessResponse(message="Smart allocation completed", data=result)

@router.post("/process-pending-requests", response_model=SuccessResponse)
async def process_pending_requests():
    """Process all pending blood requests automatically"""
    result = SmartService.process_pending_requests()
    return SuccessResponse(message=result["message"], data=result)

@router.get("/availability-report", response_model=SuccessResponse)
async def get_availability_report(blood_group: Optional[str] = None):
    """Get comprehensive blood availability report"""
    result = SmartService.get_availability_report(blood_group)
    return SuccessResponse(message="Availability report generated", data=result)

@router.get("/compatibility/{blood_type}/{required_units}", response_model=SuccessResponse)
async def find_compatible_blood(blood_type: str, required_units: int):
    """Find compatible blood sources for specific blood type"""
    result = SmartService.find_compatible_blood(blood_type, required_units)
    return SuccessResponse(message="Compatible blood sources found", data=result)

@router.get("/forecast-demand", response_model=SuccessResponse)
async def forecast_demand(days_back: int = Query(30, ge=1, le=365)):
    """Forecast blood demand based on historical data"""
    result = SmartService.forecast_demand(days_back)
    return SuccessResponse(message="Demand forecast generated", data=result)

