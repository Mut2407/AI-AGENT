from fastapi import APIRouter, Depends, HTTPException, status, Request, Body
from sqlalchemy.orm import Session
from sqlalchemy.orm.attributes import flag_modified
from fastapi.security import OAuth2PasswordRequestForm
from pydantic import BaseModel
import models, schemas, auth
from database import get_db
import json

router = APIRouter()

# ==========================================
# 1. CÁC API AUTH & USER PROFILE CƠ BẢN
# ==========================================
@router.post("/register", response_model=schemas.UserResponse)
def register_user(user: schemas.UserCreate, db: Session = Depends(get_db)):
    db_user = db.query(models.User).filter(models.User.username == user.username).first()
    if db_user: raise HTTPException(status_code=400, detail="Tên đăng nhập đã tồn tại")
    
    hashed_password = auth.get_password_hash(user.password)
    new_user = models.User(username=user.username, hashed_password=hashed_password, full_name=user.full_name, gender=user.gender, dob=user.dob, email=user.email)
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    
    new_config = models.UserConfig(user_id=new_user.id)
    db.add(new_config)
    db.commit()
    return new_user

@router.post("/login", response_model=schemas.Token)
def login_for_access_token(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    db_user = db.query(models.User).filter(models.User.username == form_data.username).first()
    if not db_user or not auth.verify_password(form_data.password, db_user.hashed_password):
        raise HTTPException(status_code=401, detail="Sai tên đăng nhập hoặc mật khẩu")
        
    access_token = auth.create_access_token(data={"sub": db_user.username})
    return {"access_token": access_token, "token_type": "bearer"}

@router.get("/me", response_model=schemas.UserResponse)
def read_users_me(current_user: models.User = Depends(auth.get_current_user)):
    return current_user

@router.put("/me/update", response_model=schemas.UserResponse)
def update_user_me(user_update: schemas.UserUpdateProfile, db: Session = Depends(get_db), current_user: models.User = Depends(auth.get_current_user)):
    if user_update.full_name is not None: current_user.full_name = user_update.full_name
    if user_update.email is not None: current_user.email = user_update.email
    if user_update.gender is not None: current_user.gender = user_update.gender
    if user_update.dob is not None: current_user.dob = user_update.dob
    db.commit()
    db.refresh(current_user)
    return current_user

# ==========================================
# 2. CÁC API PHỤC VỤ TRỰC TIẾP CHO GIAO DIỆN WEB (WIZARD & SETTINGS)
# ==========================================
class CategoryUpdate(BaseModel):
    expenseCategories: list
    incomeCategories: list

class ProfileUpdate(BaseModel):
    goal: str
    risk: str

# Mở file: Project2/user-service/app/routers.py
# Tìm và thay thế toàn bộ hàm này:

@router.get("/config")
@router.get("/config/")
def get_user_config(db: Session = Depends(get_db), current_user: models.User = Depends(auth.get_current_user)):
    config = db.query(models.UserConfig).filter(models.UserConfig.user_id == current_user.id).first()

    if not config:
        config = models.UserConfig(user_id=current_user.id)
        db.add(config)
        db.commit()
        db.refresh(config)

    # 1. Lấy dữ liệu danh mục hiện tại
    cats = config.categories if config.categories else []
    if isinstance(cats, str):
        try:
            cats = json.loads(cats.replace("'", '"'))
        except Exception:
            cats = []

    # 🚀 2. BÍ KÍP NHẬN DIỆN NEW USER: 
    # Nếu cats là một MẢNG (List), chắc chắn 100% đây là tài khoản mới tinh chưa qua Setup!
    is_new = isinstance(cats, list)

    if is_new:
        # Gán lại danh mục chuẩn tiếng Việt cho Frontend hiển thị
        exp_cats = ["Ăn uống", "Đi lại", "Mua sắm", "Hóa đơn", "Giải trí"]
        inc_cats = ["Lương", "Thưởng", "Đầu tư", "Khác"]
    else:
        # Khách cũ thì moi dữ liệu từ trong Dict ra
        exp_cats = cats.get("expenseCategories", ["Ăn uống", "Đi lại", "Mua sắm", "Hóa đơn", "Giải trí"])
        inc_cats = cats.get("incomeCategories", ["Lương", "Thưởng", "Đầu tư", "Khác"])

    return {
        "is_new_user": is_new, # 🚀 Báo chuẩn xác cho Frontend mở bảng Setup
        "expenseCategories": exp_cats,
        "incomeCategories": inc_cats,
        "currency": getattr(config, 'currency', 'vnd'),
        "startDate": getattr(config, 'startDate', 1),
        "financial_goal": getattr(config, 'financial_goal', 'Chưa xác định'),
        "risk_tolerance": getattr(config, 'risk_tolerance', 'Cân bằng'),
        "is_email_sync_enabled": getattr(config, 'is_email_sync_enabled', False)
    }

@router.post("/categories/edit")
def update_categories(data: CategoryUpdate, db: Session = Depends(get_db), current_user: models.User = Depends(auth.get_current_user)):
    config = db.query(models.UserConfig).filter(models.UserConfig.user_id == current_user.id).first()
    if config:
        config.categories = {"expenseCategories": data.expenseCategories, "incomeCategories": data.incomeCategories}
        if hasattr(config, 'is_new_user'): config.is_new_user = False
        flag_modified(config, "categories") 
        db.commit()
    return {"message": "Cập nhật danh mục thành công"}

@router.post("/profile/edit")
def update_user_profile(data: ProfileUpdate, db: Session = Depends(get_db), current_user: models.User = Depends(auth.get_current_user)):
    config = db.query(models.UserConfig).filter(models.UserConfig.user_id == current_user.id).first()
    if config:
        config.financial_goal = data.goal
        config.risk_tolerance = data.risk
        db.commit()
    return {"message": "Cập nhật hồ sơ AI thành công"}

@router.post("/currency/edit")
def update_currency(currency: str = Body(...), db: Session = Depends(get_db), current_user: models.User = Depends(auth.get_current_user)):
    config = db.query(models.UserConfig).filter(models.UserConfig.user_id == current_user.id).first()
    if config:
        config.currency = currency
        db.commit()
    return {"message": "Cập nhật tiền tệ thành công", "currency": currency}

@router.post("/startdate/edit")
def update_startdate(start_date: int = Body(...), db: Session = Depends(get_db), current_user: models.User = Depends(auth.get_current_user)):
    config = db.query(models.UserConfig).filter(models.UserConfig.user_id == current_user.id).first()
    if config:
        config.startDate = start_date
        db.commit()
    return {"message": "Cập nhật ngày bắt đầu thành công", "startDate": start_date}

@router.post("/email-sync/toggle")
def toggle_email_sync(payload: dict = Body(...), db: Session = Depends(get_db), current_user: models.User = Depends(auth.get_current_user)):
    config = db.query(models.UserConfig).filter(models.UserConfig.user_id == current_user.id).first()
    if config:
        config.is_email_sync_enabled = payload.get("is_enabled", False)
        db.commit()
    return {"message": "Cập nhật trạng thái đồng bộ Email thành công"}

# ==========================================
# 3. CÁC API NỘI BỘ (DÀNH CHO AI SERVICE & TRANSACTIONS)
# ==========================================
@router.get("/internal/config/{user_id}")
def get_internal_user_config(user_id: str, db: Session = Depends(get_db)):
    config = db.query(models.UserConfig).filter(models.UserConfig.user_id == str(user_id)).first()
    return config if config else {}

@router.put("/internal/config/update-profile")
def update_internal_profile(request: Request, data: dict, db: Session = Depends(get_db)):
    user_id_str = request.headers.get("X-Internal-User-Id")
    if not user_id_str: raise HTTPException(status_code=401, detail="Thiếu thẻ thông hành nội bộ")
        
    config = db.query(models.UserConfig).filter(models.UserConfig.user_id == str(user_id_str)).first()
    if config:
        if "goal" in data and data["goal"]: config.financial_goal = data["goal"]
        if "risk" in data and data["risk"]: config.risk_tolerance = data["risk"]
        db.commit()
        return {"message": "Cập nhật hồ sơ AI thành công"}
    raise HTTPException(status_code=404, detail="Không tìm thấy UserConfig")



@router.get("/internal/by-email")
def get_user_by_email(email: str, db: Session = Depends(get_db)):
    user = db.query(models.User).filter(models.User.email == email).first()
    if not user:
        raise HTTPException(status_code=404, detail="Not found")
    
    config = db.query(models.UserConfig).filter(models.UserConfig.user_id == user.id).first()
    
    # Lúc này nó sẽ ném nguyên cục này sang mà không bị mất chữ nào
    return {
        "username": user.username,
        "is_email_sync_enabled": config.is_email_sync_enabled if config else False
    }