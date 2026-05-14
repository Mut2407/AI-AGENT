from fastapi import FastAPI, Body, Depends
from sqlalchemy.orm import Session
from routers import router as user_router
from database import engine, Base, get_db
import models
from auth import get_current_user # Giả định em đang dùng file auth.py để giải mã token

# Tạo bảng trong DB (nếu chưa có)
Base.metadata.create_all(bind=engine)

app = FastAPI(title="ExpenseOwl - User Service")
app.include_router(user_router, prefix="/api/auth", tags=["Users"])

# ==========================================
# API CẤU HÌNH (KẾT NỐI VĨNH VIỄN VỚI POSTGRESQL)
# ==========================================

# Hàm tiện ích: Lấy cấu hình của user, nếu chưa có thì tự động tạo mới
def get_or_create_config(db: Session, user_id: int):
    config = db.query(models.UserConfig).filter(models.UserConfig.user_id == user_id).first()
    if not config:
        config = models.UserConfig(
            user_id=user_id,
            categories={
                "expenseCategories": ["Ăn uống", "Đi lại", "Mua sắm", "Hóa đơn", "Giải trí"],
                "incomeCategories": ["Lương", "Thưởng", "Đầu tư", "Khác"]
            }
        )
        db.add(config)
        db.commit()
        db.refresh(config)
    return config

@app.get("/api/config")
@app.get("/api/config/")
@app.get("/api/config/config")
def get_user_config(db: Session = Depends(get_db), current_user: models.User = Depends(get_current_user)):
    # 🚀 Sửa ["id"] thành .id
    config = get_or_create_config(db, current_user.id)
    
    response_data = {
        "is_new_user": False,
        "currency": config.currency,
        "startDate": config.startDate,
        "financial_goal": config.financial_goal,
        "risk_tolerance": config.risk_tolerance,
        "is_email_sync_enabled": config.is_email_sync_enabled
    }
    
    if isinstance(config.categories, dict) and "expenseCategories" in config.categories:
        response_data["expenseCategories"] = config.categories.get("expenseCategories", [])
        response_data["incomeCategories"] = config.categories.get("incomeCategories", [])
    else:
        response_data["categories"] = config.categories
        
    return response_data

@app.post("/api/currency/edit")
def update_currency(currency: str = Body(...), db: Session = Depends(get_db), current_user: models.User = Depends(get_current_user)):
    config = get_or_create_config(db, current_user.id) # 🚀 Sửa ở đây
    config.currency = currency
    db.commit()
    return {"message": "Cập nhật tiền tệ thành công", "currency": currency}

@app.post("/api/startdate/edit")
def update_startdate(start_date: int = Body(...), db: Session = Depends(get_db), current_user: models.User = Depends(get_current_user)):
    config = get_or_create_config(db, current_user.id) # 🚀 Sửa ở đây
    config.startDate = start_date
    db.commit()
    return {"message": "Cập nhật ngày bắt đầu thành công", "startDate": start_date}

@app.post("/api/categories/edit")
def update_categories(payload: dict = Body(...), db: Session = Depends(get_db), current_user: models.User = Depends(get_current_user)):
    config = get_or_create_config(db, current_user.id) # 🚀 Sửa ở đây
    config.categories = payload 
    db.commit()
    return {"message": "Cập nhật danh mục thành công"}

@app.post("/api/profile/edit")
def update_profile(payload: dict = Body(...), db: Session = Depends(get_db), current_user: models.User = Depends(get_current_user)):
    config = get_or_create_config(db, current_user.id) # 🚀 Sửa ở đây
    if "goal" in payload: config.financial_goal = payload["goal"]
    if "risk" in payload: config.risk_tolerance = payload["risk"]
    db.commit()
    return {"message": "Cập nhật hồ sơ AI thành công"}

@app.post("/api/email-sync/toggle")
def toggle_email_sync(payload: dict = Body(...), db: Session = Depends(get_db), current_user: models.User = Depends(get_current_user)):
    config = get_or_create_config(db, current_user.id) # 🚀 Sửa ở đây
    config.is_email_sync_enabled = payload.get("is_enabled", False)
    db.commit()
    return {"message": "Cập nhật trạng thái đồng bộ Email thành công"}