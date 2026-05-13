import os
from sqlalchemy import func, extract
from fastapi import FastAPI, Depends, HTTPException
from sqlalchemy.orm import Session
from dotenv import load_dotenv
from typing import List
from fastapi.staticfiles import StaticFiles  # <-- THÊM DÒNG NÀY
from fastapi.responses import FileResponse   # <-- THÊM DÒNG NÀY

from database import engine, Base, get_db
import models
import schemas

# Tự động tạo bảng DB nếu chưa có
Base.metadata.create_all(bind=engine)

load_dotenv()

APP_NAME = os.getenv("APP_NAME", "Expense Service")
PORT = int(os.getenv("PORT", 8001))

app = FastAPI(
    title=APP_NAME,
    description="Microservice quản lý chi tiêu",
    version="1.0.0"
)

@app.get("/api/v1/health")
def health_check():
    return {"service": "expense-service", "status": "UP"}

# ==========================================
# CÁC API QUẢN LÝ CHI TIÊU (MỚI THÊM)
# ==========================================

@app.post("/api/v1/expenses", response_model=schemas.ExpenseResponse)
def create_expense(expense: schemas.ExpenseCreate, db: Session = Depends(get_db)):
    """API để thêm một khoản chi tiêu mới"""
    # Tạo đối tượng model từ dữ liệu user gửi lên
    db_expense = models.Expense(
        amount=expense.amount,
        category=expense.category,
        description=expense.description
    )
    # Lưu vào database
    db.add(db_expense)
    db.commit()
    db.refresh(db_expense)
    return db_expense

@app.get("/api/v1/expenses", response_model=List[schemas.ExpenseResponse])
def get_expenses(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    """API lấy danh sách các khoản chi tiêu"""
    expenses = db.query(models.Expense).offset(skip).limit(limit).all()
    return expenses

@app.get("/api/v1/expenses/summary")
def get_expense_summary(year: int, month: int, db: Session = Depends(get_db)):
    """API thống kê tổng chi tiêu theo tháng và danh mục (Dành cho AI Agent gọi)"""
    
    # 1. Tính tổng số tiền đã chi trong tháng
    total_amount = db.query(func.sum(models.Expense.amount)).filter(
        extract('year', models.Expense.date) == year,
        extract('month', models.Expense.date) == month
    ).scalar() or 0.0

    # 2. Tính tổng chi tiêu gom nhóm theo từng danh mục (Food, Transport...)
    category_breakdown = db.query(
        models.Expense.category, 
        func.sum(models.Expense.amount).label('total')
    ).filter(
        extract('year', models.Expense.date) == year,
        extract('month', models.Expense.date) == month
    ).group_by(models.Expense.category).all()

    # Chuyển đổi kết quả gom nhóm thành định dạng list dễ đọc cho frontend/AI
    breakdown_list = [{"category": row.category, "total": row.total} for row in category_breakdown]

    return {
        "year": year,
        "month": month,
        "total_expense": total_amount,
        "breakdown": breakdown_list
    }

# ==========================================
# CẤU HÌNH GIAO DIỆN FRONTEND (UI)
# Đặt đoạn này ở dưới cùng để không đè lên các API
# ==========================================

# Mở quyền truy cập cho thư mục ảnh (logo, icon)
app.mount("/assets", StaticFiles(directory="assets"), name="assets")

# Trỏ thẳng tên miền gốc (/) vào thư mục chứa HTML/CSS/JS
app.mount("/", StaticFiles(directory="internal/web/templates", html=True), name="frontend")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=PORT, reload=True)