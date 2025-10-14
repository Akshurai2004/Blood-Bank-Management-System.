from models.referral import Referral, ReferralCreate, ReferralUpdate
from services.referral_service import ReferralService
from fastapi import APIRouter, status
from models.common import SuccessResponse

router = APIRouter()

@router.post("/donors/{donor_name}/referrals", response_model=SuccessResponse, status_code=status.HTTP_201_CREATED)
async def create_referral(donor_name: str, referral: ReferralCreate):
    referral.donor_name = donor_name
    result = ReferralService.create_referral(referral)
    return SuccessResponse(message="Referral created successfully", data=result)

@router.get("/donors/{donor_name}/referrals", response_model=SuccessResponse)
async def get_donor_referrals(donor_name: str):
    result = ReferralService.get_donor_referrals(donor_name)
    return SuccessResponse(message="Referrals retrieved successfully", data=result)

@router.put("/{donor_name}/{referred_donor_name}", response_model=SuccessResponse)
async def update_referral(donor_name: str, referred_donor_name: str, update: ReferralUpdate):
    result = ReferralService.update_referral(donor_name, referred_donor_name, update)
    return SuccessResponse(message="Referral updated successfully", data=result)

@router.delete("/{donor_name}/{referred_donor_name}", response_model=SuccessResponse)
async def delete_referral(donor_name: str, referred_donor_name: str):
    result = ReferralService.delete_referral(donor_name, referred_donor_name)
    return SuccessResponse(message=result["message"], data=None)

