from models.request import Request, RequestCreate, RequestUpdate, RequestStatus, UrgencyLevel
from services.request_service import RequestService
from fastapi import APIRouter, Query, status
from typing import Optional
from models.common import SuccessResponse, PaginationParams, PaginatedResponse

router = APIRouter()

@router.post("", response_model=SuccessResponse, status_code=status.HTTP_201_CREATED)
async def create_request(request: RequestCreate):
    result = RequestService.create_request(request)
    return SuccessResponse(message="Blood request created successfully", data=result)

@router.get("", response_model=PaginatedResponse[Request])
async def get_all_requests(
    status: Optional[RequestStatus] = None,
    urgency: Optional[UrgencyLevel] = None,
    bloodbank_name: Optional[str] = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100)
):
    pagination = PaginationParams(page=page, page_size=page_size)
    requests, total = RequestService.get_all_requests(
        status=status, urgency=urgency, bloodbank_name=bloodbank_name,
        skip=pagination.offset, limit=pagination.limit
    )
    return PaginatedResponse.create(data=requests, total=total, pagination=pagination)

@router.get("/pending", response_model=SuccessResponse)
async def get_pending_requests():
    result = RequestService.get_pending_requests()
    return SuccessResponse(message="Pending requests retrieved successfully", data=result)

@router.get("/{request_id}", response_model=SuccessResponse)
async def get_request(request_id: int):
    result = RequestService.get_request(request_id)
    return SuccessResponse(message="Request retrieved successfully", data=result)

@router.put("/{request_id}", response_model=SuccessResponse)
async def update_request(request_id: int, update: RequestUpdate):
    result = RequestService.update_request(request_id, update)
    return SuccessResponse(message="Request updated successfully", data=result)

@router.patch("/{request_id}/status", response_model=SuccessResponse)
async def update_request_status(request_id: int, status: RequestStatus):
    update = RequestUpdate(status=status)
    result = RequestService.update_request(request_id, update)
    return SuccessResponse(message="Request status updated successfully", data=result)

@router.delete("/{request_id}", response_model=SuccessResponse)
async def delete_request(request_id: int):
    result = RequestService.delete_request(request_id)
    return SuccessResponse(message=result["message"], data=None)
