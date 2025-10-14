from fastapi import APIRouter, Query, status
from typing import Optional
from models.staff import Staff, StaffCreate, StaffUpdate, StaffRole
from models.common import SuccessResponse, PaginationParams, PaginatedResponse
from services.staff_service import StaffService

router = APIRouter()

@router.post("", response_model=SuccessResponse, status_code=status.HTTP_201_CREATED)
async def create_staff(staff: StaffCreate):
    result = StaffService.create_staff(staff)
    return SuccessResponse(message="Staff created successfully", data=result)

@router.get("", response_model=PaginatedResponse[Staff])
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

