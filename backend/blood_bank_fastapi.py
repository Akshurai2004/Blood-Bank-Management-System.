import os
from contextlib import asynccontextmanager
from typing import Optional, Literal
from datetime import datetime, timedelta, timezone

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

import bcrypt
import jwt
import uvicorn
from fastapi import FastAPI, HTTPException, Depends, Header, status, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel, EmailStr, Field

# Import database and message queue services
try:
    from .blood_bank_backend import BloodBankDB
    from .queue_service import message_queue
    from .email_service import OTPService, _otp_store
except ImportError:
    from blood_bank_backend import BloodBankDB
    from queue_service import message_queue
    from email_service import OTPService, _otp_store

# Shared literals for validation
BloodGroupLiteral = Literal['A+', 'A-', 'B+', 'B-', 'AB+', 'AB-', 'O+', 'O-']
GenderLiteral = Literal['M', 'F', 'O']
RequestStatusLiteral = Literal['Pending', 'Fulfilled', 'Denied']
RoleLiteral = Literal['Donor', 'Hospital', 'Admin', 'SuperAdmin']

# JWT Configuration
JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY", "bloodbank-jwt-secret-key-super-secure-2026")
JWT_ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "1440")) # 24 hours

security = HTTPBearer(auto_error=False)

def hash_password(password: str) -> str:
    salt = bcrypt.gensalt()
    return bcrypt.hashpw(password.encode("utf-8"), salt).decode("utf-8")

def verify_password(password: str, hashed: str) -> bool:
    try:
        return bcrypt.checkpw(password.encode("utf-8"), hashed.encode("utf-8"))
    except Exception:
        return False

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    to_encode = data.copy()
    if "sub" in to_encode:
        to_encode["sub"] = str(to_encode["sub"])
    expire = datetime.now(timezone.utc) + (expires_delta or timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES))
    to_encode.update({"exp": expire, "iat": datetime.now(timezone.utc)})
    return jwt.encode(to_encode, JWT_SECRET_KEY, algorithm=JWT_ALGORITHM)

async def get_current_user(credentials: Optional[HTTPAuthorizationCredentials] = Depends(security)) -> Optional[dict]:
    if not credentials:
        return None
    token = credentials.credentials
    try:
        payload = jwt.decode(token, JWT_SECRET_KEY, algorithms=[JWT_ALGORITHM])
        sub_val = payload.get("sub")
        if sub_val is None:
            return None
        user_id = int(sub_val)
        user = db.get_user_by_id(user_id)
        if not user:
            return None
        return user
    except Exception:
        return None

def require_auth(user: Optional[dict] = Depends(get_current_user)):
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Authentication token required or expired")
    return user

def require_roles(allowed_roles: list[str]):
    def _role_checker(user: dict = Depends(require_auth)):
        if user.get("Role") not in allowed_roles and user.get("Role") != "SuperAdmin":
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied: insufficient permissions")
        return user
    return _role_checker

# Initialize database outside of app so it can be accessed by lifespan
DB_CONFIG = {
    "host": os.getenv("DB_HOST", "localhost"),
    "user": os.getenv("DB_USER", "root"),
    "password": os.getenv("DB_PASSWORD", "Pes@2004"),
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
app = FastAPI(title="Blood Bank Management API", version="2.0.0", lifespan=lifespan)

# Add CORS middleware to allow React to connect
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Pydantic models for Auth
class UserRegister(BaseModel):
    full_name: str = Field(min_length=2, max_length=100)
    email: EmailStr
    password: str = Field(min_length=6, max_length=100)
    role: RoleLiteral = 'Donor'
    # Optional fields for auto-linking profiles
    donor_id: Optional[int] = None
    age: Optional[int] = Field(default=None, ge=18, le=65)
    gender: Optional[GenderLiteral] = None
    blood_group: Optional[BloodGroupLiteral] = None
    contact: Optional[str] = None
    address: Optional[str] = None
    hospital_id: Optional[int] = None
    blood_bank_id: Optional[int] = None

class SendRegistrationOTPRequest(BaseModel):
    full_name: str = Field(min_length=2, max_length=100)
    email: EmailStr
    password: str = Field(min_length=6, max_length=100)
    role: RoleLiteral = 'Donor'
    donor_id: Optional[int] = None
    age: Optional[int] = Field(default=None, ge=18, le=65)
    gender: Optional[GenderLiteral] = None
    blood_group: Optional[BloodGroupLiteral] = None
    contact: Optional[str] = None
    address: Optional[str] = None
    hospital_id: Optional[int] = None
    blood_bank_id: Optional[int] = None

class VerifyRegistrationOTPRequest(BaseModel):
    email: EmailStr
    otp: str = Field(min_length=6, max_length=6)

class SendLoginOTPRequest(BaseModel):
    email: EmailStr

class VerifyLoginOTPRequest(BaseModel):
    email: EmailStr
    otp: str = Field(min_length=6, max_length=6)

class ResendOTPRequest(BaseModel):
    email: EmailStr
    purpose: Literal['registration', 'login'] = 'registration'

class UserLogin(BaseModel):
    email: EmailStr
    password: str

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
    return {"message": "Blood Bank Management API is running", "status": "healthy", "version": "2.0.0"}


# ==================== AUTHENTICATION ENDPOINTS ====================

@app.post("/api/auth/send-registration-otp")
async def send_registration_otp(req: SendRegistrationOTPRequest):
    clean_email = req.email.strip().lower()
    existing = db.get_user_by_email(clean_email)
    if existing:
        raise HTTPException(status_code=400, detail="An account with this email already exists. Please log in.")
    
    # Extra validation for Donor fields if provided
    if req.role == "Donor":
        if req.contact and len(req.contact.strip()) != 10:
            raise HTTPException(status_code=400, detail="Donor contact number must be exactly 10 digits.")
        if req.age and (req.age < 18 or req.age > 65):
            raise HTTPException(status_code=400, detail="Donor age must be between 18 and 65.")

    payload = req.model_dump()
    success, msg = OTPService.create_registration_otp(clean_email, payload)
    if not success:
        raise HTTPException(status_code=429, detail=msg)
    
    return {
        "success": True,
        "message": msg,
        "email": clean_email,
    }


@app.post("/api/auth/verify-registration-otp")
async def verify_registration_otp(req: VerifyRegistrationOTPRequest):
    clean_email = req.email.strip().lower()
    is_valid, payload, err_msg = OTPService.verify_registration_otp(clean_email, req.otp)
    if not is_valid or not payload:
        raise HTTPException(status_code=400, detail=err_msg)

    # Check again if user exists to prevent double registration
    if db.get_user_by_email(clean_email):
        raise HTTPException(status_code=400, detail="User already registered. Please log in.")

    donor_id = payload.get("donor_id")
    hospital_id = payload.get("hospital_id")
    blood_bank_id = payload.get("blood_bank_id")
    role = payload.get("role", "Donor")

    # If registering as Donor and donor profile not linked, link to existing donor or auto-create Donor record
    if role == "Donor" and not donor_id:
        existing_donor = None
        if clean_email:
            existing_donor = db.get_donor_by_email(clean_email)
        if not existing_donor and payload.get("contact"):
            existing_donor = db.get_donor_by_contact(payload["contact"])

        if existing_donor:
            donor_id = existing_donor.get("DonorID")
        elif payload.get("age") and payload.get("blood_group") and payload.get("contact"):
            donor_id = db.add_donor(
                name=payload["full_name"],
                age=payload["age"],
                gender=payload.get("gender") or 'M',
                blood_group=payload["blood_group"],
                contact=payload["contact"],
                email=clean_email,
                address=payload.get("address") or ''
            )

    pwd_hash = hash_password(payload["password"])
    user_id = db.create_user(
        full_name=payload["full_name"],
        email=clean_email,
        password_hash=pwd_hash,
        role=role,
        donor_id=donor_id,
        hospital_id=hospital_id,
        blood_bank_id=blood_bank_id
    )

    if not user_id:
        raise HTTPException(status_code=500, detail="Failed to create user account in database.")

    token = create_access_token({"sub": user_id, "role": role, "email": clean_email})
    return {
        "success": True,
        "message": "Account created and verified successfully!",
        "token": token,
        "user": {
            "id": user_id,
            "name": payload["full_name"],
            "email": clean_email,
            "role": role,
            "donor_id": donor_id,
            "hospital_id": hospital_id,
            "blood_bank_id": blood_bank_id
        }
    }


@app.post("/api/auth/send-login-otp")
async def send_login_otp(req: SendLoginOTPRequest):
    clean_email = req.email.strip().lower()
    user = db.get_user_by_email(clean_email)
    if not user:
        raise HTTPException(status_code=404, detail="No account registered with this email address.")
    
    success, msg = OTPService.create_login_otp(clean_email, user["FullName"])
    if not success:
        raise HTTPException(status_code=429, detail=msg)
    
    return {
        "success": True,
        "message": msg,
        "email": clean_email
    }


@app.post("/api/auth/verify-login-otp")
async def verify_login_otp(req: VerifyLoginOTPRequest):
    clean_email = req.email.strip().lower()
    is_valid, msg = OTPService.verify_login_otp(clean_email, req.otp)
    if not is_valid:
        raise HTTPException(status_code=400, detail=msg)
    
    user = db.get_user_by_email(clean_email)
    if not user:
        raise HTTPException(status_code=404, detail="User account not found.")

    token = create_access_token({"sub": user["UserID"], "role": user["Role"], "email": user["Email"]})
    return {
        "success": True,
        "message": "Logged in successfully via OTP!",
        "token": token,
        "user": {
            "id": user["UserID"],
            "name": user["FullName"],
            "email": user["Email"],
            "role": user["Role"],
            "donor_id": user.get("DonorID"),
            "hospital_id": user.get("HospitalID"),
            "blood_bank_id": user.get("BloodBankID")
        }
    }


@app.post("/api/auth/resend-otp")
async def resend_otp(req: ResendOTPRequest):
    clean_email = req.email.strip().lower()
    if req.purpose == "login":
        user = db.get_user_by_email(clean_email)
        if not user:
            raise HTTPException(status_code=404, detail="No account found with this email.")
        success, msg = OTPService.create_login_otp(clean_email, user["FullName"])
    else:
        # registration
        record = _otp_store.get(clean_email)
        if not record or record.get("purpose") != "registration":
            raise HTTPException(status_code=400, detail="No pending registration session found. Please re-fill registration form.")
        payload = record["payload"]
        success, msg = OTPService.create_registration_otp(clean_email, payload)
    
    if not success:
        raise HTTPException(status_code=429, detail=msg)
    
    return {"success": True, "message": msg, "email": clean_email}


@app.post("/api/auth/register")
async def register(user_data: UserRegister):
    clean_email = user_data.email.strip().lower()
    existing = db.get_user_by_email(clean_email)
    if existing:
        raise HTTPException(status_code=400, detail="User with this email already exists")

    donor_id = user_data.donor_id
    hospital_id = user_data.hospital_id
    blood_bank_id = user_data.blood_bank_id

    # If registering as Donor and donor profile not linked, link to existing donor or auto-create Donor record
    if user_data.role == "Donor" and not donor_id:
        existing_donor = None
        if clean_email:
            existing_donor = db.get_donor_by_email(clean_email)
        if not existing_donor and user_data.contact:
            existing_donor = db.get_donor_by_contact(user_data.contact)

        if existing_donor:
            donor_id = existing_donor.get("DonorID")
        elif user_data.age and user_data.blood_group and user_data.contact:
            donor_id = db.add_donor(
                name=user_data.full_name,
                age=user_data.age,
                gender=user_data.gender or 'M',
                blood_group=user_data.blood_group,
                contact=user_data.contact,
                email=clean_email,
                address=user_data.address or ''
            )

    pwd_hash = hash_password(user_data.password)
    user_id = db.create_user(
        full_name=user_data.full_name,
        email=clean_email,
        password_hash=pwd_hash,
        role=user_data.role,
        donor_id=donor_id,
        hospital_id=hospital_id,
        blood_bank_id=blood_bank_id
    )

    if not user_id:
        raise HTTPException(status_code=500, detail="Failed to create user account")

    token = create_access_token({"sub": user_id, "role": user_data.role, "email": clean_email})
    return {
        "success": True,
        "token": token,
        "user": {
            "id": user_id,
            "name": user_data.full_name,
            "email": clean_email,
            "role": user_data.role,
            "donor_id": donor_id,
            "hospital_id": hospital_id,
            "blood_bank_id": blood_bank_id
        }
    }


@app.post("/api/auth/login")
async def login(credentials: UserLogin):
    clean_email = credentials.email.strip().lower()
    user = db.get_user_by_email(clean_email)
    if not user or not verify_password(credentials.password, user["PasswordHash"]):
        raise HTTPException(status_code=401, detail="Invalid email or password")

    token = create_access_token({"sub": user["UserID"], "role": user["Role"], "email": user["Email"]})
    return {
        "success": True,
        "token": token,
        "user": {
            "id": user["UserID"],
            "name": user["FullName"],
            "email": user["Email"],
            "role": user["Role"],
            "donor_id": user.get("DonorID"),
            "hospital_id": user.get("HospitalID"),
            "blood_bank_id": user.get("BloodBankID")
        }
    }


@app.get("/api/auth/me")
async def get_me(user: dict = Depends(require_auth)):
    user_copy = dict(user)
    user_copy.pop("PasswordHash", None)
    
    # Enrich with linked donor or hospital info if present
    donor_info = None
    if user.get("DonorID"):
        donor_info = db.get_donor_by_id(user["DonorID"])
        if donor_info:
            donor_info["eligibility"] = db.check_donor_eligibility(user["DonorID"])
    
    return {
        "success": True,
        "user": user_copy,
        "donor_profile": donor_info
    }


@app.post("/api/auth/logout")
async def logout():
    return {"success": True, "message": "Successfully logged out"}


# ==================== DONOR SELF-SERVICE PORTAL ====================

@app.get("/api/donor/portal-data")
async def get_donor_portal_data(user: dict = Depends(require_auth)):
    donor_id = user.get("DonorID")
    donor_info = None
    history = []
    eligibility = "Register as a donor to check eligibility"

    if donor_id:
        donor_info = db.get_donor_by_id(donor_id)
        eligibility = db.check_donor_eligibility(donor_id)
        # Fetch donations made by this donor
        history_query = """
        SELECT bu.UnitID, bu.BloodGroup, bu.Component, bu.CollectionDate, bu.ExpirationDate, bu.Status, bb.BloodBankName, bb.Location
        FROM BloodUnit bu
        JOIN BloodBank bb ON bu.BloodBankID = bb.BloodBankID
        WHERE bu.DonorID = %s
        ORDER BY bu.CollectionDate DESC
        """
        history = db.fetch_query(history_query, (donor_id,))
    
    return {
        "success": True,
        "donor": donor_info,
        "eligibility": eligibility,
        "donation_history": history,
        "bloodbanks": db.get_all_blood_banks()
    }


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
async def create_request(request: RequestCreate, background_tasks: BackgroundTasks):
    request_id = db.create_request(
        patient_id=request.patient_id,
        blood_bank_id=request.blood_bank_id,
        required_units=request.required_units
    )
    if not request_id:
        raise HTTPException(status_code=400, detail="Failed to create request")

    # Fetch patient & hospital context for decoupled emergency alert queue
    patient = db.get_patient_by_id(request.patient_id)
    hospital_name = "Emergency Healthcare Facility"
    if patient and patient.get("HospitalID"):
        hosp = db.get_hospital_by_id(patient["HospitalID"])
        if hosp:
            hospital_name = hosp.get("HospitalName", hospital_name)

    bank = db.get_blood_bank_by_id(request.blood_bank_id)
    bank_name = bank.get("BloodBankName", "Blood Bank") if bank else "Blood Bank"

    # Enqueue emergency notification job into message queue
    job_payload = {
        "request_id": request_id,
        "patient_id": request.patient_id,
        "patient_name": patient.get("PatientName", "Urgent Patient") if patient else "Urgent Patient",
        "blood_group": patient.get("BloodGroupRequired", "O+") if patient else "O+",
        "hospital_name": hospital_name,
        "blood_bank_id": request.blood_bank_id,
        "blood_bank_name": bank_name,
        "required_units": request.required_units
    }
    job_id = message_queue.enqueue_alert(job_payload)

    # Dispatch asynchronous worker task without blocking HTTP response
    background_tasks.add_task(message_queue.process_emergency_job, job_payload, db)

    return {
        "success": True,
        "message": "Emergency request created & queued via Message Queue",
        "request_id": request_id,
        "job_id": job_id,
        "queue_broker": "Redis 7.0" if message_queue.is_redis_active() else "FastAPI Async Worker"
    }


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
    # Get request details to check blood type
    request_data = db.fetch_query(
        """
        SELECT r.RequestID, r.RequiredUnits, p.BloodGroupRequired, r.Status
        FROM Request r
        JOIN Patient p ON r.PatientID = p.PatientID
        WHERE r.RequestID = %s
        """,
        (allocation.request_id,)
    )
    
    if not request_data:
        raise HTTPException(status_code=404, detail="Request not found")
    
    request_info = request_data[0]
    
    # Check if request is already fulfilled or denied
    if request_info['Status'] in ['Fulfilled', 'Denied']:
        raise HTTPException(status_code=400, detail=f"Request is already {request_info['Status']}")
    
    # Get blood unit details
    unit_data = db.fetch_query(
        "SELECT UnitID, BloodGroup, Status FROM BloodUnit WHERE UnitID = %s",
        (allocation.unit_id,)
    )
    
    if not unit_data:
        raise HTTPException(status_code=404, detail="Blood unit not found")
    
    unit_info = unit_data[0]
    
    # Check if unit is available
    if unit_info['Status'] != 'Available':
        raise HTTPException(status_code=400, detail="Blood unit is not available")
    
    # Check if blood types match
    required_blood_group = request_info['BloodGroupRequired']
    unit_blood_group = unit_info['BloodGroup']
    
    if required_blood_group == unit_blood_group:
        # Blood types match - allocate and mark as fulfilled
        allocation_id = db.allocate_blood_unit(
            request_id=allocation.request_id,
            unit_id=allocation.unit_id
        )
        if not allocation_id:
            raise HTTPException(status_code=400, detail="Failed to create allocation")
        
        # Update request status to Fulfilled
        db.update_request_status(allocation.request_id, 'Fulfilled')
        
        return {
            "success": True,
            "message": "Blood unit allocated successfully and request marked as Fulfilled",
            "allocation_id": allocation_id,
            "status": "Fulfilled"
        }
    else:
        # Blood types don't match - mark request as denied and log the attempt
        db.update_request_status(allocation.request_id, 'Denied')
        
        # Log the denied allocation attempt
        db.execute_query(
            """
            INSERT INTO Allocation (RequestID, UnitID, DeliveryStatus)
            VALUES (%s, %s, 'Failed')
            """,
            (allocation.request_id, allocation.unit_id)
        )
        
        return {
            "success": False,
            "message": f"Blood type mismatch: Request requires {required_blood_group} but unit is {unit_blood_group}. Request marked as Denied.",
            "status": "Denied",
            "required_blood_group": required_blood_group,
            "unit_blood_group": unit_blood_group
        }


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


# ==================== MESSAGE QUEUE & NOTIFICATIONS ENDPOINTS ====================


@app.get("/api/notifications/queue-status")
async def get_queue_status():
    return {"success": True, "telemetry": message_queue.get_queue_telemetry()}


@app.get("/api/notifications/recent")
async def get_recent_notifications(limit: int = 15):
    broadcasts = message_queue.get_recent_broadcasts(limit=limit)
    return {"success": True, "data": broadcasts, "count": len(broadcasts)}


# Run the server
if __name__ == "__main__":
    uvicorn.run("blood_bank_fastapi:app", host="0.0.0.0", port=8000, reload=True)
