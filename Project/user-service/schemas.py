from datetime import date
from typing import List, Optional
from pydantic import BaseModel, field_validator, ConfigDict

class UserCreate(BaseModel):
    username: str
    password: str
    full_name: str
    gender: str
    dob: date
    email: str

class UserResponse(BaseModel):
    id: int
    username: str
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
        return value