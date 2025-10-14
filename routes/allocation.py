from models.allocation import Allocation, AllocationCreate, AllocationUpdate
from services.allocation_service import AllocationService
from fastapi import APIRouter, Query, status
from typing import Optional
from models.common import SuccessResponse, PaginationParams, PaginatedResponse

router = APIRouter()

@router.post("", response_model=SuccessResponse, status_code=status.HTTP_201_CREATED)
async def create_allocation(allocation: AllocationCreate):
    result = AllocationService.create_allocation(allocation)
    return SuccessResponse(message="Allocation created successfully", data=result)

@router.get("", response_model=PaginatedResponse[Allocation])
async def get_all_allocations(
    request_id: Optional[int] = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100)
):
    pagination = PaginationParams(page=page, page_size=page_size)
    allocations, total = AllocationService.get_all_allocations(
        request_id=request_id, skip=pagination.offset, limit=pagination.limit
    )
    return PaginatedResponse.create(data=allocations, total=total, pagination=pagination)

@router.get("/{allocation_id}", response_model=SuccessResponse)
async def get_allocation(allocation_id: int):
    result = AllocationService.get_allocation(allocation_id)
    return SuccessResponse(message="Allocation retrieved successfully", data=result)

@router.put("/{allocation_id}", response_model=SuccessResponse)
async def update_allocation(allocation_id: int, update: AllocationUpdate):
    result = AllocationService.update_allocation(allocation_id, update)
    return SuccessResponse(message="Allocation updated successfully", data=result)

@router.delete("/{allocation_id}", response_model=SuccessResponse)
async def delete_allocation(allocation_id: int):
    result = AllocationService.delete_allocation(allocation_id)
    return SuccessResponse(message=result["message"], data=None)

