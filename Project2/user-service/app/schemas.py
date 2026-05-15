from datetime import date, datetime
from typing import List, Optional
from decimal import Decimal
from pydantic import BaseModel, field_validator, Field, ConfigDict

class UserCreate(BaseModel):
    username: str
    password: str
    full_name: str
    gender: str
    dob: date
    email: str
class UserLogin(BaseModel):
    username: str
    password: str

class UserResponse(BaseModel):
    id: int
    username: str
    full_name: str | None = None 
    email: str | None = None     
    gender: str | None = None    
    dob: date | None = None
    
    model_config = ConfigDict(from_attributes=True) 

class Token(BaseModel):
    access_token: str
    token_type: str

class UserUpdatePassword(BaseModel):
    old_password: str
    new_password: str

    @field_validator('new_password')
    @classmethod
    def validate_password(cls, value):
        if len(value) < 6:
            raise ValueError("Mật khẩu mới phải có ít nhất 6 ký tự.")
        if len(value) > 72:
            raise ValueError("Mật khẩu mới quá dài! Vui lòng nhập dưới 72 ký tự.")
        return value
    
class UserOut(BaseModel):
    id: int
    username: str
    full_name: str
    email: str
    gender: str | None = None
    dob: str | None = None
    financial_goal: str | None = "Chưa xác định"
    risk_tolerance: str | None = "Cân bằng"

    class Config:
        from_attributes = True 

class UserUpdateProfile(BaseModel):
    full_name: Optional[str] = None
    email: Optional[str] = None
    gender: Optional[str] = None
    dob: Optional[date] = None

    model_config = ConfigDict(from_attributes=True)
    
    # Validator này giúp "ép" chuỗi rỗng thành None để không bị lỗi 422
    @field_validator('dob', mode='before')
    @classmethod
    def parse_dob(cls, v):
        if v == "" or v is None:
            return None
        return v