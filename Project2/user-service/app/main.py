from fastapi import FastAPI
from routers import router as user_router  # Xóa chữ app. ở đây
from database import engine, Base

# Tạo bảng trong DB (nếu chưa có)
Base.metadata.create_all(bind=engine)

app = FastAPI(title="ExpenseOwl - User Service")

app.include_router(user_router, prefix="/api/auth", tags=["Users"])

@app.get("/health")
def health_check():
    return {"status": "User Service is running perfectly!"}