from fastapi import FastAPI
from routers import router as user_router  # Xóa chữ app. ở đây
from database import engine, Base

# Tạo bảng trong DB (nếu chưa có)
Base.metadata.create_all(bind=engine)

app = FastAPI(title="ExpenseOwl - User Service")

app.include_router(user_router, prefix="/api/auth", tags=["Users"])

@app.get("/api/config")
@app.get("/api/config/")
@app.get("/api/config/config") # Thêm cái này để bắt trường hợp Gateway ghép dư chữ
@app.get("/api/config/config/")
def get_user_config():
    return {"is_new_user": False}