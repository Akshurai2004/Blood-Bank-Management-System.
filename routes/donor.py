from models.donor import Donor, DonorCreate, DonorUpdate
from services.donor_service import DonorService
from fastapi import APIRouter, Query, status
from typing import Optional
from models.common import SuccessResponse, PaginationParams, PaginatedResponse

router = APIRouter()

@router.post("", response_model=SuccessResponse, status_code=status.HTTP_201_CREATED)
async def create_donor(donor: DonorCreate):
    result = DonorService.create_donor(donor)
    return SuccessResponse(message="Donor registered successfully", data=result)

@router.get("", response_model=PaginatedResponse[Donor])
async def get_all_donors(
    blood_group: Optional[str] = None,
    is_active: Optional[bool] = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100)
):
    pagination = PaginationParams(page=page, page_size=page_size)
    donors, total = DonorService.get_all_donors(
        blood_group=blood_group, is_active=is_active,
        skip=pagination.offset, limit=pagination.limit
    )
    return PaginatedResponse.create(data=donors, total=total, pagination=pagination)

@router.get("/{donor_name}", response_model=SuccessResponse)
async def get_donor(donor_name: str):
    result = DonorService.get_donor(donor_name)
    return SuccessResponse(message="Donor retrieved successfully", data=result)

@router.put("/{donor_name}", response_model=SuccessResponse)
async def update_donor(donor_name: str, update: DonorUpdate):
    result = DonorService.update_donor(donor_name, update)
    return SuccessResponse(message="Donor updated successfully", data=result)

@router.delete("/{donor_name}", response_model=SuccessResponse)
async def delete_donor(donor_name: str):
    result = DonorService.delete_donor(donor_name)
    return SuccessResponse(message=result["message"], data=None)

@router.patch("/{donor_name}/deactivate", response_model=SuccessResponse)
async def deactivate_donor(donor_name: str):
    result = DonorService.deactivate_donor(donor_name)
    return SuccessResponse(message="Donor deactivated successfully", data=result)

@router.get("/{donor_name}/eligibility", response_model=SuccessResponse)
async def check_donor_eligibility(donor_name: str):
    result = DonorService.check_eligibility(donor_name)
    return SuccessResponse(message="Eligibility checked successfully", data=result)

@router.get("/{donor_name}/statistics", response_model=SuccessResponse)
async def get_donor_statistics(donor_name: str):
    result = DonorService.get_donor_statistics(donor_name)
    return SuccessResponse(message="Donor statistics retrieved successfully", data=result)
