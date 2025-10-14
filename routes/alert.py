from models.alert import Alert, AlertType, Severity
from services.alert_service import AlertService
from fastapi import APIRouter, Query
from typing import Optional
from models.common import SuccessResponse, PaginationParams, PaginatedResponse

router = APIRouter()

@router.get("", response_model=PaginatedResponse[Alert])
async def get_all_alerts(
    alert_type: Optional[AlertType] = None,
    severity: Optional[Severity] = None,
    is_read: Optional[bool] = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100)
):
    pagination = PaginationParams(page=page, page_size=page_size)
    alerts, total = AlertService.get_all_alerts(
        alert_type=alert_type, severity=severity, is_read=is_read,
        skip=pagination.offset, limit=pagination.limit
    )
    return PaginatedResponse.create(data=alerts, total=total, pagination=pagination)

@router.get("/{alert_id}", response_model=SuccessResponse)
async def get_alert(alert_id: int):
    result = AlertService.get_alert(alert_id)
    return SuccessResponse(message="Alert retrieved successfully", data=result)

@router.patch("/{alert_id}/mark-read", response_model=SuccessResponse)
async def mark_alert_as_read(alert_id: int):
    result = AlertService.mark_as_read(alert_id)
    return SuccessResponse(message="Alert marked as read", data=result)

@router.delete("/{alert_id}", response_model=SuccessResponse)
async def delete_alert(alert_id: int):
    result = AlertService.delete_alert(alert_id)
    return SuccessResponse(message=result["message"], data=None)
