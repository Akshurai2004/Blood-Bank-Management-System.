from models.transaction import Transaction, TransactionCreate, TransactionUpdate, TransactionType
from services.transaction_service import TransactionService
from fastapi import APIRouter, Query, status
from typing import Optional
from models.common import SuccessResponse, PaginationParams, PaginatedResponse

router = APIRouter()

@router.post("", response_model=SuccessResponse, status_code=status.HTTP_201_CREATED)
async def create_transaction(transaction: TransactionCreate):
    result = TransactionService.create_transaction(transaction)
    return SuccessResponse(message="Transaction created successfully", data=result)

@router.get("", response_model=PaginatedResponse[Transaction])
async def get_all_transactions(
    transaction_type: Optional[TransactionType] = None,
    donor_name: Optional[str] = None,
    bloodbank_name: Optional[str] = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100)
):
    pagination = PaginationParams(page=page, page_size=page_size)
    transactions, total = TransactionService.get_all_transactions(
        transaction_type=transaction_type, donor_name=donor_name,
        bloodbank_name=bloodbank_name, skip=pagination.offset, limit=pagination.limit
    )
    return PaginatedResponse.create(data=transactions, total=total, pagination=pagination)

@router.get("/{transaction_id}", response_model=SuccessResponse)
async def get_transaction(transaction_id: int):
    result = TransactionService.get_transaction(transaction_id)
    return SuccessResponse(message="Transaction retrieved successfully", data=result)

@router.put("/{transaction_id}", response_model=SuccessResponse)
async def update_transaction(transaction_id: int, update: TransactionUpdate):
    result = TransactionService.update_transaction(transaction_id, update)
    return SuccessResponse(message="Transaction updated successfully", data=result)

@router.delete("/{transaction_id}", response_model=SuccessResponse)
async def delete_transaction(transaction_id: int):
    result = TransactionService.delete_transaction(transaction_id)
    return SuccessResponse(message=result["message"], data=None)

