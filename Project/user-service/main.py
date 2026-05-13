from fastapi import FastAPI, Depends, HTTPException, Body
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
import models, schemas, auth
from database import engine, get_db
from dotenv import load_dotenv

load_dotenv()
models.Base.metadata.create_all(bind=engine)

app = FastAPI(title="ExpenseOwl User Service")

# --- AUTH ENDPOINTS ---
@app.post("/api/auth/register")
def register_user(user: schemas.UserCreate, db: Session = Depends(get_db)):
    if db.query(models.User).filter(models.User.username == user.username).first():
        raise HTTPException(status_code=400, detail="Tên đăng nhập đã tồn tại")
    hashed_password = auth.get_password_hash(user.password)
    new_user = models.User(
        username=user.username, hashed_password=hashed_password,
        full_name=user.full_name, gender=user.gender, dob=user.dob, email=user.email
    )
    db.add(new_user)
    db.commit()
    return {"message": "Đăng ký thành công"}

@app.post("/api/auth/login")
def login_user(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    user = db.query(models.User).filter(models.User.username == form_data.username).first()
    if not user or not auth.verify_password(form_data.password, user.hashed_password):
        raise HTTPException(status_code=401, detail="Thông tin đăng nhập không chính xác")
    return {"access_token": auth.create_access_token(data={"sub": user.username}), "token_type": "bearer"}

# --- CONFIG ENDPOINTS ---
@app.get("/api/config")
def get_config(db: Session = Depends(get_db), current_user: models.User = Depends(auth.get_current_user)):
    user_config = db.query(models.UserConfig).filter(models.UserConfig.user_id == current_user.id).first()
    if not user_config:
        return {"currency": "usd", "startDate": 1, "categories": ["Ăn uống", "Đi lại", "Mua sắm"]}
    return {"currency": user_config.currency, "startDate": user_config.startDate, "categories": user_config.categories}

@app.post("/api/currency/edit")
def edit_currency(currency_code: str = Body(...), db: Session = Depends(get_db), current_user: models.User = Depends(auth.get_current_user)):
    config = db.query(models.UserConfig).filter(models.UserConfig.user_id == current_user.id).first()
    if not config:
        config = models.UserConfig(user_id=current_user.id, currency=currency_code.lower())
        db.add(config)
    else:
        config.currency = currency_code.lower()
    db.commit()
    return {"message": "Thành công"}