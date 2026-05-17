from fastapi import FastAPI
from sqlalchemy.orm import Session
from routers import router as user_router
from database import engine, Base
from prometheus_fastapi_instrumentator import Instrumentator
# Tạo bảng trong DB (nếu chưa có)
Base.metadata.create_all(bind=engine)

app = FastAPI(title="ExpenseOwl - User Service")
Instrumentator().instrument(app).expose(app)
# 1. Nhúng router cho Xác thực (Login/Register)
app.include_router(user_router, prefix="/api/auth", tags=["Auth"])

# 2. Nhúng router cho toàn bộ Config, Profile, Categories vào thư mục "users"
app.include_router(user_router, prefix="/api/users", tags=["Users"])
