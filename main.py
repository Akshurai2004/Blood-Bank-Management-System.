from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import os
from dotenv import load_dotenv

# Import database
from config.database import test_connection

# Import all routes
from routes import (
    hospital, staff, assignment, bloodbank, campaign,
    donor, referral, transaction, blood_unit, patient,
    request as request_routes, allocation, alert,
    smart_operations, reports, maintenance
)

# Import exception handlers
#from utils.exceptions import BloodBankException

load_dotenv()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup and shutdown events"""
    # Startup
    print("🚀 Starting Blood Bank Management System...")
    
    # Test database connection
    if test_connection():
        print("✅ Database connection successful")
    else:
        print("❌ Database connection failed")
        raise Exception("Could not connect to database")
    
    print("✨ Application started successfully")
    
    yield
    
    # Shutdown
    print("👋 Shutting down Blood Bank Management System...")


# Create FastAPI app
app = FastAPI(
    title=os.getenv("API_TITLE", "Blood Bank Management System API"),
    version=os.getenv("API_VERSION", "1.0.0"),
    description=os.getenv("API_DESCRIPTION", "Smart Blood Matching Engine with Intelligence Layer"),
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Change this in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

'''
# Exception handler for custom exceptions
@app.exception_handler(BloodBankException)
async def blood_bank_exception_handler(request: Request, exc: BloodBankException):
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "success": False,
            "error": exc.detail
        }
    )
'''

# Global exception handler
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    return JSONResponse(
        status_code=500,
        content={
            "success": False,
            "error": "Internal server error",
            "detail": str(exc)
        }
    )


# Health check endpoint
@app.get("/", tags=["Health"])
async def root():
    """API health check"""
    return {
        "success": True,
        "message": "Blood Bank Management System API is running",
        "version": os.getenv("API_VERSION", "1.0.0"),
        "endpoints": {
            "docs": "/docs",
            "redoc": "/redoc"
        }
    }


@app.get("/health", tags=["Health"])
async def health_check():
    """Detailed health check"""
    db_status = test_connection()
    return {
        "success": True,
        "status": "healthy" if db_status else "unhealthy",
        "database": "connected" if db_status else "disconnected",
        "version": os.getenv("API_VERSION", "1.0.0")
    }


# Include all routers
app.include_router(hospital.router, prefix="/api/v1/hospitals", tags=["Hospitals"])
app.include_router(staff.router, prefix="/api/v1/staff", tags=["Staff"])
app.include_router(assignment.router, prefix="/api/v1/assignments", tags=["Staff Assignments"])
app.include_router(bloodbank.router, prefix="/api/v1/bloodbanks", tags=["Blood Banks"])
app.include_router(campaign.router, prefix="/api/v1/campaigns", tags=["Campaigns"])
app.include_router(donor.router, prefix="/api/v1/donors", tags=["Donors"])
app.include_router(referral.router, prefix="/api/v1/referrals", tags=["Referrals"])
app.include_router(transaction.router, prefix="/api/v1/transactions", tags=["Transactions"])
app.include_router(blood_unit.router, prefix="/api/v1/blood-units", tags=["Blood Units"])
app.include_router(patient.router, prefix="/api/v1/patients", tags=["Patients"])
app.include_router(request_routes.router, prefix="/api/v1/requests", tags=["Requests"])
app.include_router(allocation.router, prefix="/api/v1/allocations", tags=["Allocations"])
app.include_router(alert.router, prefix="/api/v1/alerts", tags=["Alerts"])
app.include_router(smart_operations.router, prefix="/api/v1/smart", tags=["Smart Operations"])
app.include_router(reports.router, prefix="/api/v1/reports", tags=["Reports & Analytics"])
app.include_router(maintenance.router, prefix="/api/v1/maintenance", tags=["Maintenance"])


if __name__ == "__main__":
    import uvicorn
    
    host = os.getenv("HOST", "0.0.0.0")
    port = int(os.getenv("PORT", 8000))
    reload = os.getenv("RELOAD", "True").lower() == "true"
    
    print(f"🌐 Starting server on http://{host}:{port}")
    print(f"📚 API Documentation: http://{host}:{port}/docs")
    
    uvicorn.run(
        "main:app",
        host=host,
        port=port,
        reload=reload
    )