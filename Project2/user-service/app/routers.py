from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
import models, schemas, auth
from database import get_db
from fastapi.security import OAuth2PasswordRequestForm
from pydantic import BaseModel
from typing import Optional
from fastapi import HTTPException, status
from auth import get_current_user, verify_password, get_password_hash
import models
from datetime import datetime # 🚀 Nhớ thêm dòng này ở đỉnh file


router = APIRouter()

@router.post("/register", response_model=schemas.UserResponse)
def register_user(user: schemas.UserCreate, db: Session = Depends(get_db)):
    # 1. Kiểm tra xem username đã tồn tại chưa
    db_user = db.query(models.User).filter(models.User.username == user.username).first()
    if db_user:
        raise HTTPException(status_code=400, detail="Tên đăng nhập đã tồn tại")
    
    # 2. Băm mật khẩu và lưu User
    hashed_password = auth.get_password_hash(user.password)
    new_user = models.User(
        username=user.username,
        hashed_password=hashed_password,
        full_name=user.full_name,
        gender=user.gender,
        dob=user.dob,
        email=user.email
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    
    # 3. Tạo cấu hình UserConfig mặc định cho người dùng mới
    new_config = models.UserConfig(user_id=new_user.id)
    db.add(new_config)
    db.commit()
    
    return new_user

@router.post("/login", response_model=schemas.Token)
def login_for_access_token(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    # 1. Tìm user trong DB dựa trên username từ form_data
    db_user = db.query(models.User).filter(models.User.username == form_data.username).first()
    
    # 2. Kiểm tra mật khẩu
    if not db_user or not auth.verify_password(form_data.password, db_user.hashed_password):
        raise HTTPException(status_code=401, detail="Sai tên đăng nhập hoặc mật khẩu")
        
    # 3. Tạo JWT Token
    access_token = auth.create_access_token(data={"sub": db_user.username})
    return {"access_token": access_token, "token_type": "bearer"}

@router.get("/me", response_model=schemas.UserResponse)
def read_users_me(current_user: models.User = Depends(auth.get_current_user)):
    return current_user

# ==========================================
# KHAI BÁO CẤU TRÚC DỮ LIỆU NHẬN VÀO
# ==========================================
class ProfileUpdate(BaseModel):
    full_name: str
    dob: Optional[str] = None
    gender: Optional[str] = None

class PasswordChange(BaseModel):
    old_password: str
    new_password: str

# ==========================================
# API CẬP NHẬT TÀI KHOẢN (Đổi tên, ngày sinh, giới tính)
# ==========================================
@router.put("/me/update")
def update_profile_info(profile_data: ProfileUpdate, db: Session = Depends(get_db), current_user: models.User = Depends(get_current_user)):
    user = db.query(models.User).filter(models.User.id == current_user.id).first()
    
    user.full_name = profile_data.full_name
    user.gender = profile_data.gender
    
    # 🚀 Chuyển đổi String thành đối tượng Date của Python trước khi lưu
    if profile_data.dob:
        try:
            user.dob = datetime.strptime(profile_data.dob, '%Y-%m-%d').date()
        except Exception as e:
            print(f"Lỗi định dạng ngày: {e}")
            
    db.commit()
    db.refresh(user) # Làm tươi dữ liệu
    return {"message": "Cập nhật thông tin thành công"}

# ==========================================
# API ĐỔI MẬT KHẨU
# ==========================================
@router.put("/change-password")
def change_password(pass_data: PasswordChange, db: Session = Depends(get_db), current_user: models.User = Depends(get_current_user)):
    user = db.query(models.User).filter(models.User.id == current_user.id).first()
    
    # 1. Kiểm tra mật khẩu cũ có đúng không (Lưu ý: thay hàm verify_password bằng hàm kiểm tra của em)
    if not verify_password(pass_data.old_password, user.hashed_password):
        raise HTTPException(status_code=400, detail="Mật khẩu hiện tại không đúng!")
        
    # 2. Mã hóa mật khẩu mới (Lưu ý: thay hàm get_password_hash bằng hàm mã hóa của em)
    user.hashed_password = get_password_hash(pass_data.new_password)
    db.commit()
    
    return {"message": "Đổi mật khẩu thành công"}