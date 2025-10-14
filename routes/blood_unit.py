from models.blood_unit import BloodUnit, BloodUnitCreate, BloodUnitUpdate, BloodUnitStatus
from services.blood_unit_service import BloodUnitService
from fastapi import APIRouter, Query, status
from typing import Optional
from models.common import SuccessResponse, PaginationParams, PaginatedResponse

router = APIRouter()

@router.post("", response_model=SuccessResponse, status_code=status.HTTP_201_CREATED)
async def create_blood_unit(unit: BloodUnitCreate):
    result = BloodUnitService.create_blood_unit(unit)
    return SuccessResponse(message="Blood unit created successfully", data=result)

@router.get("", response_model=PaginatedResponse[BloodUnit])
async def get_all_blood_units(
    blood_group: Optional[str] = None,
    status: Optional[BloodUnitStatus] = None,
    bloodbank_name: Optional[str] = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100)
):
    pagination = PaginationParams(page=page, page_size=page_size)
    units, total = BloodUnitService.get_all_blood_units(
        blood_group=blood_group, status=status, bloodbank_name=bloodbank_name,
        skip=pagination.offset, limit=pagination.limit
    )
    return PaginatedResponse.create(data=units, total=total, pagination=pagination)

@router.get("/expiring-soon", response_model=SuccessResponse)
async def get_expiring_units(days: int = Query(7, ge=1, le=30)):
    result = BloodUnitService.get_expiring_soon(days)
    return SuccessResponse(message=f"Units expiring in {days} days retrieved", data=result)

@router.get("/available", response_model=SuccessResponse)
async def get_available_inventory():
    result = BloodUnitService.get_available_inventory()
    return SuccessResponse(message="Available inventory retrieved successfully", data=result)

@router.get("/{unit_id}", response_model=SuccessResponse)
async def get_blood_unit(unit_id: int):
    result = BloodUnitService.get_blood_unit(unit_id)
    return SuccessResponse(message="Blood unit retrieved successfully", data=result)

@router.put("/{unit_id}", response_model=SuccessResponse)
async def update_blood_unit(unit_id: int, update: BloodUnitUpdate):
    result = BloodUnitService.update_blood_unit(unit_id, update)
    return SuccessResponse(message="Blood unit updated successfully", data=result)

@router.patch("/{unit_id}/status", response_model=SuccessResponse)
async def update_unit_status(unit_id: int, status: BloodUnitStatus):
    update = BloodUnitUpdate(status=status)
    result = BloodUnitService.update_blood_unit(unit_id, update)
    return SuccessResponse(message="Blood unit status updated successfully", data=result)

@router.delete("/{unit_id}", response_model=SuccessResponse)
async def delete_blood_unit(unit_id: int):
    result = BloodUnitService.delete_blood_unit(unit_id)
    return SuccessResponse(message=result["message"], data=None)

