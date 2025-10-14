from typing import List, Optional
from fastapi import APIRouter, Query, status
from models.common import SuccessResponse, PaginationParams, PaginatedResponse
from models.bloodbank import BloodBank, BloodBankCreate, BloodBankUpdate
from services.bloodbank_service import BloodBankService

router = APIRouter()

@router.post("", response_model=SuccessResponse, status_code=status.HTTP_201_CREATED)
async def create_bloodbank(bloodbank: BloodBankCreate):
    result = BloodBankService.create_bloodbank(bloodbank)
    return SuccessResponse(message="Blood bank created successfully", data=result)

@router.get("", response_model=PaginatedResponse[BloodBank])
async def get_all_bloodbanks(
    location: Optional[str] = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100)
):
    pagination = PaginationParams(page=page, page_size=page_size)
    bloodbanks, total = BloodBankService.get_all_bloodbanks(
        location=location, skip=pagination.offset, limit=pagination.limit
    )
    return PaginatedResponse.create(data=bloodbanks, total=total, pagination=pagination)

@router.get("/{bloodbank_name}", response_model=SuccessResponse)
async def get_bloodbank(bloodbank_name: str):
    result = BloodBankService.get_bloodbank(bloodbank_name)
    return SuccessResponse(message="Blood bank retrieved successfully", data=result)

@router.put("/{bloodbank_name}", response_model=SuccessResponse)
async def update_bloodbank(bloodbank_name: str, update: BloodBankUpdate):
    result = BloodBankService.update_bloodbank(bloodbank_name, update)
    return SuccessResponse(message="Blood bank updated successfully", data=result)

@router.delete("/{bloodbank_name}", response_model=SuccessResponse)
async def delete_bloodbank(bloodbank_name: str):
    result = BloodBankService.delete_bloodbank(bloodbank_name)
    return SuccessResponse(message=result["message"], data=None)