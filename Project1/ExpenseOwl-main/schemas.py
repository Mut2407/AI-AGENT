from pydantic import BaseModel
from datetime import datetime
from typing import Optional

# Dữ liệu người dùng gửi lên khi thêm chi tiêu mới
class ExpenseCreate(BaseModel):
    amount: float
    category: str
    description: Optional[str] = None

# Dữ liệu API trả về cho Frontend
class ExpenseResponse(BaseModel):
    id: int
    amount: float
    category: str
    description: Optional[str]
    date: datetime

    class Config:
        from_attributes = True # Cho phép Pydantic đọc dữ liệu trực tiếp từ SQLAlchemy