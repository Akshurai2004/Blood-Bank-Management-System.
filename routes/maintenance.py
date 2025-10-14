from services.maintenance_service import MaintenanceService
from fastapi import APIRouter, Query
from typing import Optional
from models.common import SuccessResponse

router = APIRouter()

@router.post("/daily", response_model=SuccessResponse)
async def run_daily_maintenance():
    """Run all daily maintenance tasks"""
    result = MaintenanceService.run_daily_maintenance()
    return SuccessResponse(message=result["message"], data=result)

@router.post("/mark-expired", response_model=SuccessResponse)
async def mark_expired_units():
    """Mark expired blood units"""
    result = MaintenanceService.mark_expired_units()
    return SuccessResponse(message=result["message"], data=result)

@router.post("/generate-alerts", response_model=SuccessResponse)
async def generate_expiry_alerts():
    """Generate alerts for expiring blood units"""
    result = MaintenanceService.generate_expiry_alerts()
    return SuccessResponse(message=result["message"], data=result)

@router.post("/update-inventory-stats", response_model=SuccessResponse)
async def update_inventory_stats():
    """Update inventory statistics"""
    result = MaintenanceService.update_inventory_statistics()
    return SuccessResponse(message=result["message"], data=result)

@router.get("/expiry-alerts", response_model=SuccessResponse)
async def get_expiry_alerts():
    """Get all expiry alerts"""
    result = MaintenanceService.get_expiry_alerts()
    return SuccessResponse(message="Expiry alerts retrieved", data=result)

@router.post("/cleanup-logs", response_model=SuccessResponse)
async def cleanup_old_logs(days: int = Query(30, ge=1, le=365)):
    """Cleanup old performance logs"""
    result = MaintenanceService.cleanup_old_logs(days)
    return SuccessResponse(message=result["message"], data=result)_model=PaginatedResponse[Staff])
async def get_all_staff(
    role: Optional[StaffRole] = None,
    is_active: Optional[bool] = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100)
):
    pagination = PaginationParams(page=page, page_size=page_size)
    staff_list, total = StaffService.get_all_staff(
        role=role, is_active=is_active, skip=pagination.offset, limit=pagination.limit
    )
    return PaginatedResponse.create(data=staff_list, total=total, pagination=pagination)

@router.get("/{staff_id}", response_model=SuccessResponse)
async def get_staff(staff_id: int):
    result = StaffService.get_staff(staff_id)
    return SuccessResponse(message="Staff retrieved successfully", data=result)

@router.put("/{staff_id}", response_model=SuccessResponse)
async def update_staff(staff_id: int, staff_update: StaffUpdate):
    result = StaffService.update_staff(staff_id, staff_update)
    return SuccessResponse(message="Staff updated successfully", data=result)

@router.delete("/{staff_id}", response_model=SuccessResponse)
async def delete_staff(staff_id: int):
    result = StaffService.delete_staff(staff_id)
    return SuccessResponse(message=result["message"], data=None)

@router.patch("/{staff_id}/deactivate", response_model=SuccessResponse)
async def deactivate_staff(staff_id: int):
    result = StaffService.deactivate_staff(staff_id)
    return SuccessResponse(message="Staff deactivated successfully", data=result)

