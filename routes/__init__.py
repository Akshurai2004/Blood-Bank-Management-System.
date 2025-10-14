from . import hospital
from . import staff
from . import assignment
from . import bloodbank
from . import campaign
from . import donor
from . import referral
from . import transaction
from . import blood_unit
from . import patient
from . import request as request_routes  # Renamed to avoid conflict
from . import allocation
from . import alert
from . import smart_operations
from . import reports
from . import maintenance

__all__ = [
    "hospital",
    "staff",
    "assignment",
    "bloodbank",
    "campaign",
    "donor",
    "referral",
    "transaction",
    "blood_unit",
    "patient",
    "request_routes",
    "allocation",
    "alert",
    "smart_operations",
    "reports",
    "maintenance"
]
