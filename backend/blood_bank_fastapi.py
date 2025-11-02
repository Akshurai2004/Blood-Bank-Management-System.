import os
from contextlib import asynccontextmanager
from typing import Optional, Literal

import uvicorn
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, EmailStr, Field

# Import your database class (use package-relative import since this module is
# intended to be loaded as `backend.blood_bank_fastapi`)
from .blood_bank_backend import BloodBankDB

# Shared literals for validation
BloodGroupLiteral = Literal['A+', 'A-', 'B+', 'B-', 'AB+', 'AB-', 'O+', 'O-']
GenderLiteral = Literal['M', 'F', 'O']
RequestStatusLiteral = Literal['Pending', 'Fulfilled', 'Denied']

# Initialize database outside of app so it can be accessed by lifespan
DB_CONFIG = {
    "host": os.getenv("DB_HOST", "localhost"),
    "user": os.getenv("DB_USER", "root"),
    "password": os.getenv("DB_PASSWORD", "akshat@MySQL"),
    "database": os.getenv("DB_NAME", "BloodBankDB"),
}
db = BloodBankDB(**DB_CONFIG)

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan event handler to connect and disconnect DB"""
    if not db.connect():
        raise Exception("Failed to connect to database")
    yield
    db.disconnect()

# Initialize FastAPI app with lifespan
app = FastAPI(title="Blood Bank Management API", version="1.0.0", lifespan=lifespan)

# Add CORS middleware to allow React to connect
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, restrict to your React app URL origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Pydantic models for request validation
class DonorCreate(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    age: int = Field(ge=18, le=65)
    gender: GenderLiteral
    blood_group: BloodGroupLiteral
    contact: str = Field(min_length=6, max_length=20)
    email: Optional[EmailStr] = None
    address: Optional[str] = Field(default=None, max_length=255)


class DonorUpdate(BaseModel):
    DonorName: Optional[str] = None
    Age: Optional[int] = None
    Gender: Optional[GenderLiteral] = None
    ContactNo: Optional[str] = None
    Email: Optional[EmailStr] = None
    Address: Optional[str] = None
    IsActive: Optional[bool] = None


class BloodBankCreate(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    location: str = Field(min_length=1, max_length=100)
    contact: str = Field(min_length=6, max_length=20)
    capacity: int = Field(default=1000, ge=100)


class HospitalCreate(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    location: str = Field(min_length=1, max_length=100)
    contact: str = Field(min_length=6, max_length=20)
    email: Optional[EmailStr] = None


class PatientCreate(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    age: int = Field(ge=0, le=120)
    gender: GenderLiteral
    blood_group: BloodGroupLiteral
    hospital_id: int = Field(gt=0)
    contact: str = Field(min_length=6, max_length=20)
    condition: Optional[str] = Field(default=None, max_length=255)


class RequestCreate(BaseModel):
    patient_id: int = Field(gt=0)
    blood_bank_id: int = Field(gt=0)
    required_units: int = Field(default=1, ge=1)


class RequestUpdate(BaseModel):
    patient_id: Optional[int] = None
    blood_bank_id: Optional[int] = None
    required_units: Optional[int] = None


class DonationRecord(BaseModel):
    donor_id: int = Field(gt=0)
    blood_bank_id: int = Field(gt=0)
    component: str = Field(default='Whole Blood', min_length=2, max_length=50)
    quantity: int = Field(default=1, ge=1)


class AllocationCreate(BaseModel):
    request_id: int = Field(gt=0)
    unit_id: int = Field(gt=0)


class RequestStatusUpdate(BaseModel):
    status: RequestStatusLiteral

class PatientUpdate(BaseModel):
    PatientName: Optional[str] = None
    Age: Optional[int] = None
    Gender: Optional[GenderLiteral] = None
    BloodGroupRequired: Optional[BloodGroupLiteral] = None
    HospitalID: Optional[int] = None
    ContactNo: Optional[str] = None
    MedicalCondition: Optional[str] = None
    IsActive: Optional[bool] = None
# Health check endpoint
@app.get("/")
async def root():
    return {"message": "Blood Bank Management API is running", "status": "healthy"}


# ==================== DONOR ENDPOINTS ====================


@app.get("/api/donors")
async def get_all_donors():
    donors = db.get_all_donors()
    return {"success": True, "data": donors, "count": len(donors)}

@app.delete("/api/donors/{donor_id}")
async def delete_donor(donor_id: int):
    # Soft delete: set IsActive = FALSE
    success = db.update_donor(donor_id, IsActive=False)
    if not success:
        raise HTTPException(status_code=400, detail="Failed to delete donor")
    return {"success": True, "message": "Donor deleted successfully"}

@app.get("/api/donors/{donor_id}")
async def get_donor(donor_id: int):
    donor = db.get_donor_by_id(donor_id)
    if not donor:
        raise HTTPException(status_code=404, detail="Donor not found")
    return {"success": True, "data": donor}


@app.post("/api/donors")
async def create_donor(donor: DonorCreate):
    donor_id = db.add_donor(
        name=donor.name,
        age=donor.age,
        gender=donor.gender,
        blood_group=donor.blood_group,
        contact=donor.contact,
        email=donor.email,
        address=donor.address
    )
    if not donor_id:
        raise HTTPException(status_code=400, detail="Failed to add donor")
    return {"success": True, "message": "Donor added successfully", "donor_id": donor_id}


@app.put("/api/donors/{donor_id}")
async def update_donor(donor_id: int, donor: DonorUpdate):
    update_data = {k: v for k, v in donor.dict().items() if v is not None}
    if not update_data:
        raise HTTPException(status_code=400, detail="No data to update")
    success = db.update_donor(donor_id, **update_data)
    if not success:
        raise HTTPException(status_code=400, detail="Failed to update donor")
    return {"success": True, "message": "Donor updated successfully"}


@app.get("/api/donors/{donor_id}/eligibility")
async def check_eligibility(donor_id: int):
    eligibility = db.check_donor_eligibility(donor_id)
    return {"success": True, "eligibility": eligibility}


# ==================== BLOOD BANK ENDPOINTS ====================


@app.get("/api/bloodbanks")
async def get_all_blood_banks():
    banks = db.get_all_blood_banks()
    return {"success": True, "data": banks, "count": len(banks)}


@app.post("/api/bloodbanks")
async def create_blood_bank(bank: BloodBankCreate):
    bank_id = db.add_blood_bank(
        name=bank.name,
        location=bank.location,
        contact=bank.contact,
        capacity=bank.capacity
    )
    if not bank_id:
        raise HTTPException(status_code=400, detail="Failed to add blood bank")
    return {"success": True, "message": "Blood bank added successfully", "blood_bank_id": bank_id}


@app.get("/api/inventory")
async def get_inventory():
    inventory = db.get_available_inventory()
    return {"success": True, "data": inventory, "count": len(inventory)}


@app.get("/api/inventory/{blood_bank_id}")
async def get_bank_inventory(blood_bank_id: int):
    inventory = db.get_inventory_by_blood_bank(blood_bank_id)
    return {"success": True, "data": inventory, "count": len(inventory)}


# ==================== BLOOD UNIT ENDPOINTS ====================


@app.get("/api/bloodunits")
async def get_blood_units(status: Optional[str] = None, blood_group: Optional[str] = None):
    units = db.get_blood_units(status=status, blood_group=blood_group)
    return {"success": True, "data": units, "count": len(units)}


@app.post("/api/donations")
async def record_donation(donation: DonationRecord):
    success = db.record_donation(
        donor_id=donation.donor_id,
        blood_bank_id=donation.blood_bank_id,
        component=donation.component,
        quantity=donation.quantity
    )
    if not success:
        raise HTTPException(status_code=400, detail="Failed to record donation")
    return {"success": True, "message": "Donation recorded successfully"}


# ==================== HOSPITAL ENDPOINTS ====================


@app.get("/api/hospitals")
async def get_all_hospitals():
    hospitals = db.get_all_hospitals()
    return {"success": True, "data": hospitals, "count": len(hospitals)}


@app.post("/api/hospitals")
async def create_hospital(hospital: HospitalCreate):
    hospital_id = db.add_hospital(
        name=hospital.name,
        location=hospital.location,
        contact=hospital.contact,
        email=hospital.email
    )
    if not hospital_id:
        raise HTTPException(status_code=400, detail="Failed to add hospital")
    return {"success": True, "message": "Hospital added successfully", "hospital_id": hospital_id}


# ==================== PATIENT ENDPOINTS ====================


@app.get("/api/patients")
async def get_all_patients():
    patients = db.get_all_patients()
    return {"success": True, "data": patients, "count": len(patients)}

class PatientUpdate(BaseModel):
    PatientName: Optional[str] = None
    Age: Optional[int] = None
    Gender: Optional[GenderLiteral] = None
    BloodGroupRequired: Optional[BloodGroupLiteral] = None
    HospitalID: Optional[int] = None
    ContactNo: Optional[str] = None
    MedicalCondition: Optional[str] = None
    IsActive: Optional[bool] = None
# Update patient endpoint
@app.put("/api/patients/{patient_id}")
async def update_patient(patient_id: int, patient: PatientUpdate):
    update_data = {k: v for k, v in patient.dict().items() if v is not None}
    if not update_data:
        raise HTTPException(status_code=400, detail="No data to update")
    success = db.update_patient(patient_id, **update_data)
    if not success:
        raise HTTPException(status_code=400, detail="Failed to update patient")
    return {"success": True, "message": "Patient updated successfully"}

# Delete patient endpoint (soft delete)
@app.delete("/api/patients/{patient_id}")
async def delete_patient(patient_id: int):
    # Try soft-delete first (set IsActive = FALSE). If the database schema
    # doesn't include the IsActive column (older DB), update_patient will
    # return False — in that case attempt a hard delete as a fallback.
    success = db.update_patient(patient_id, IsActive=False)
    if success:
        return {"success": True, "message": "Patient deleted successfully"}

    # Soft-delete failed; attempt hard delete as a fallback.
    hard_delete = db.execute_query("DELETE FROM Patient WHERE PatientID = %s", (patient_id,))
    if hard_delete:
        return {"success": True, "message": "Patient deleted successfully (hard delete)"}

    # Both attempts failed.
    raise HTTPException(status_code=400, detail="Failed to delete patient")

@app.post("/api/patients")
async def create_patient(patient: PatientCreate):
    patient_id = db.add_patient(
        name=patient.name,
        age=patient.age,
        gender=patient.gender,
        blood_group=patient.blood_group,
        hospital_id=patient.hospital_id,
        contact=patient.contact,
        condition=patient.condition
    )
    if not patient_id:
        raise HTTPException(status_code=400, detail="Failed to add patient")
    return {"success": True, "message": "Patient added successfully", "patient_id": patient_id}


# ==================== REQUEST ENDPOINTS ====================


@app.get("/api/requests")
async def get_all_requests():
    requests = db.get_all_requests()
    return {"success": True, "data": requests, "count": len(requests)}


@app.post("/api/requests")
async def create_request(request: RequestCreate):
    request_id = db.create_request(
        patient_id=request.patient_id,
        blood_bank_id=request.blood_bank_id,
        required_units=request.required_units
    )
    if not request_id:
        raise HTTPException(status_code=400, detail="Failed to create request")
    return {"success": True, "message": "Request created successfully", "request_id": request_id}


@app.put("/api/requests/{request_id}")
async def update_request(request_id: int, request: RequestUpdate):
    update_data = {k: v for k, v in request.dict().items() if v is not None}
    if not update_data:
        raise HTTPException(status_code=400, detail="No data to update")

    # Server-side validation: ensure provided patient and blood bank exist
    if 'patient_id' in update_data:
        patient = db.get_patient_by_id(update_data['patient_id'])
        if not patient:
            raise HTTPException(status_code=404, detail="Patient not found")

    if 'blood_bank_id' in update_data:
        bank = db.get_blood_bank_by_id(update_data['blood_bank_id'])
        if not bank:
            raise HTTPException(status_code=404, detail="Blood bank not found")

    # Map payload keys to DB method parameters and call the DB update
    success = db.update_request(
        request_id,
        patient_id=update_data.get('patient_id'),
        blood_bank_id=update_data.get('blood_bank_id'),
        required_units=update_data.get('required_units')
    )
    if not success:
        raise HTTPException(status_code=400, detail="Failed to update request")
    return {"success": True, "message": "Request updated successfully"}


@app.delete("/api/requests/{request_id}")
async def delete_request(request_id: int):
    # Perform a soft-delete by setting the request status to 'Denied'
    success = db.update_request_status(request_id, 'Denied')
    if not success:
        raise HTTPException(status_code=400, detail="Failed to deny (delete) request")
    return {"success": True, "message": "Request denied (soft-deleted) successfully"}


@app.put("/api/requests/{request_id}/status")
async def update_request_status(request_id: int, status_update: RequestStatusUpdate):
    success = db.update_request_status(request_id, status_update.status)
    if not success:
        raise HTTPException(status_code=400, detail="Failed to update request status")
    return {"success": True, "message": "Request status updated successfully"}


# ==================== ALLOCATION ENDPOINTS ====================


@app.get("/api/allocations")
async def get_all_allocations():
    allocations = db.get_allocations()
    return {"success": True, "data": allocations, "count": len(allocations)}


@app.post("/api/allocations")
async def create_allocation(allocation: AllocationCreate):
    allocation_id = db.allocate_blood_unit(
        request_id=allocation.request_id,
        unit_id=allocation.unit_id
    )
    if not allocation_id:
        raise HTTPException(status_code=400, detail="Failed to create allocation")
    return {"success": True, "message": "Blood unit allocated successfully", "allocation_id": allocation_id}


# ==================== STATISTICS ENDPOINTS ====================


@app.get("/api/statistics/donors")
async def get_donor_stats():
    stats = db.get_donor_statistics()
    return {"success": True, "data": stats}


@app.get("/api/statistics/bloodbanks")
async def get_blood_bank_stats():
    stats = db.get_blood_bank_statistics()
    return {"success": True, "data": stats}


@app.get("/api/statistics/requests")
async def get_request_stats():
    stats = db.get_request_statistics()
    return {"success": True, "data": stats}


@app.get("/api/statistics/dashboard")
async def get_dashboard_stats():
    return {
        "success": True,
        "data": {
            "donors": db.get_donor_statistics(),
            "blood_banks": db.get_blood_bank_statistics(),
            "requests": db.get_request_statistics()
        }
    }


# Run the server
if __name__ == "__main__":
    uvicorn.run("blood_bank_fastapi:app", host="0.0.0.0", port=8000, reload=True)
