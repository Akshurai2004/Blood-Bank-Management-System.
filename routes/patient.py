from models.patient import Patient, PatientCreate, PatientUpdate
from services.patient_service import PatientService
from fastapi import APIRouter, Query, status
from typing import Optional
from models.common import SuccessResponse, PaginationParams, PaginatedResponse

router = APIRouter()

@router.post("", response_model=SuccessResponse, status_code=status.HTTP_201_CREATED)
async def create_patient(patient: PatientCreate):
    result = PatientService.create_patient(patient)
    return SuccessResponse(message="Patient registered successfully", data=result)

@router.get("", response_model=PaginatedResponse[Patient])
async def get_all_patients(
    hospital_name: Optional[str] = None,
    blood_group: Optional[str] = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100)
):
    pagination = PaginationParams(page=page, page_size=page_size)
    patients, total = PatientService.get_all_patients(
        hospital_name=hospital_name, blood_group=blood_group,
        skip=pagination.offset, limit=pagination.limit
    )
    return PaginatedResponse.create(data=patients, total=total, pagination=pagination)

@router.get("/{patient_id}", response_model=SuccessResponse)
async def get_patient(patient_id: int):
    result = PatientService.get_patient(patient_id)
    return SuccessResponse(message="Patient retrieved successfully", data=result)

@router.put("/{patient_id}", response_model=SuccessResponse)
async def update_patient(patient_id: int, update: PatientUpdate):
    result = PatientService.update_patient(patient_id, update)
    return SuccessResponse(message="Patient updated successfully", data=result)

@router.delete("/{patient_id}", response_model=SuccessResponse)
async def delete_patient(patient_id: int):
    result = PatientService.delete_patient(patient_id)
    return SuccessResponse(message=result["message"], data=None)
