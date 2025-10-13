from datetime import datetime
from pydantic import BaseModel, Field, EmailStr
from typing import Optional
from enum import Enum

class TransactionType(str, Enum):
    DONATION = "Donation"
    DISTRIBUTION = "Distribution"
    TRANSFER = "Transfer"


class TransactionBase(BaseModel):
    donor_name: Optional[str] = None
    bloodbank_name: Optional[str] = None
    transaction_type: TransactionType = TransactionType.DONATION
    quantity: int = Field(default=1, ge=1)
    notes: Optional[str] = None


class TransactionCreate(TransactionBase):
    pass


class TransactionUpdate(BaseModel):
    transaction_type: Optional[TransactionType] = None
    quantity: Optional[int] = Field(None, ge=1)
    notes: Optional[str] = None


class Transaction(TransactionBase):
    transaction_id: int
    date_of_donation: datetime
    
    class Config:
        from_attributes = True