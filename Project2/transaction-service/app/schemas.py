from datetime import datetime
from typing import List, Optional
from decimal import Decimal
from pydantic import BaseModel, field_validator, Field, ConfigDict

# ==========================================
# 1. SCHEMAS CHO GIAO DỊCH THƯỜNG
# ==========================================

class CategoriesPayload(BaseModel):
    """Schema dùng để hứng dữ liệu 2 mảng Thu - Chi từ Frontend gửi lên"""
    expenseCategories: List[str] = Field(default_factory=list)
    incomeCategories: List[str] = Field(default_factory=list)

class TransactionBase(BaseModel):
    name: str
    amount: Decimal
    category: str
    date: datetime
    tags: Optional[List[str]] = Field(default_factory=list)
    
    note: Optional[str] = None
    recurring_interval: Optional[str] = ""

    @field_validator('amount')
    @classmethod
    def validate_amount(cls, value: Decimal):
        if value == Decimal('0'):
            raise ValueError("Số tiền giao dịch không được bằng 0.")
        if value > Decimal('1000000000000') or value < Decimal('-1000000000000'):  
            raise ValueError("Số tiền giao dịch quá lớn (vượt quá 1,000 tỷ VNĐ), hệ thống từ chối ghi nhận!")
        return value

    @field_validator('name')
    @classmethod
    def validate_name(cls, value):
        if len(value.strip()) < 2:
            raise ValueError("Tên giao dịch không hợp lệ (phải có ít nhất 2 ký tự).")
        return value

    @field_validator('date')
    @classmethod
    def validate_date(cls, value):
        if value.year > 2050:
            raise ValueError("Năm giao dịch vô lý (Không được vượt quá năm 2050).")
        return value

class TransactionCreate(TransactionBase):
    jar_id: Optional[int] = None

class TransactionResponse(TransactionBase):
    id: str
    jar_id: Optional[int] = None
    user_id: str # Đã đổi thành str để khớp với chuỗi UUID từ Token
    
    model_config = ConfigDict(from_attributes=True)


# ==========================================
# 2. SCHEMAS CHO GIAO DỊCH ĐỊNH KỲ
# ==========================================

class RecurringTransactionBase(BaseModel):
    name: str
    amount: Decimal
    category: str
    tags: Optional[List[str]] = Field(default_factory=list) 
    interval: str
    startDate: datetime
    occurrences: int

    @field_validator('amount')
    @classmethod
    def validate_amount(cls, value: Decimal):
        if value == Decimal('0'):
            raise ValueError("Số tiền giao dịch không được bằng 0.")
        if value > Decimal('1000000000000') or value < Decimal('-1000000000000'):  
            raise ValueError("Số tiền giao dịch quá lớn (vượt quá 1,000 tỷ VNĐ).")
        return value

    @field_validator('name')
    @classmethod
    def validate_name(cls, value):
        if len(value.strip()) < 2:
            raise ValueError("Tên giao dịch phải có ít nhất 2 ký tự.")
        return value

class RecurringTransactionCreate(RecurringTransactionBase):
    pass

class RecurringTransactionResponse(RecurringTransactionBase):
    id: str
    user_id: str # Đã đổi thành str để khớp với chuỗi UUID từ Token
    
    model_config = ConfigDict(from_attributes=True)