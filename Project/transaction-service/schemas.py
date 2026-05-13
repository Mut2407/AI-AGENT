from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, Field, ConfigDict

class TransactionBase(BaseModel):
    name: str
    amount: float
    category: str
    date: datetime
    tags: Optional[List[str]] = Field(default_factory=list)
    note: Optional[str] = None
    recurring_interval: Optional[str] = ""

class TransactionCreate(TransactionBase):
    pass

class TransactionResponse(TransactionBase):
    id: str
    user_id: int
    model_config = ConfigDict(from_attributes=True)

class RecurringTransactionCreate(BaseModel):
    name: str
    amount: float
    category: str
    tags: Optional[List[str]] = Field(default_factory=list)
    interval: str
    startDate: datetime
    occurrences: int