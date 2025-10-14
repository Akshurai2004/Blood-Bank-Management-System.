from models.assignment import Assignment, AssignmentCreate, AssignmentUpdate
from services.assignment_service import AssignmentService
from fastapi import APIRouter, status
from models.common import SuccessResponse
router = APIRouter()

@router.post("/staff/{staff_id}/assignments", response_model=SuccessResponse, status_code=status.HTTP_201_CREATED)
async def create_assignment(staff_id: int, assignment: AssignmentCreate):
    assignment.staff_id = staff_id
    result = AssignmentService.create_assignment(assignment)
    return SuccessResponse(message="Assignment created successfully", data=result)

@router.get("/staff/{staff_id}/assignments", response_model=SuccessResponse)
async def get_staff_assignments(staff_id: int):
    result = AssignmentService.get_staff_assignments(staff_id)
    return SuccessResponse(message="Assignments retrieved successfully", data=result)

@router.get("/hospitals/{hospital_name}/staff", response_model=SuccessResponse)
async def get_hospital_staff(hospital_name: str):
    result = AssignmentService.get_hospital_staff(hospital_name)
    return SuccessResponse(message="Hospital staff retrieved successfully", data=result)

@router.put("/{staff_id}/{hospital_name}", response_model=SuccessResponse)
async def update_assignment(staff_id: int, hospital_name: str, update: AssignmentUpdate):
    result = AssignmentService.update_assignment(staff_id, hospital_name, update)
    return SuccessResponse(message="Assignment updated successfully", data=result)

@router.delete("/{staff_id}/{hospital_name}", response_model=SuccessResponse)
async def delete_assignment(staff_id: int, hospital_name: str):
    result = AssignmentService.delete_assignment(staff_id, hospital_name)
    return SuccessResponse(message=result["message"], data=None)

