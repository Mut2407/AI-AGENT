from fastapi import FastAPI, Depends, HTTPException
from sqlalchemy.orm import Session
import models, schemas, auth
from database import engine, get_db
import os
from google import genai
from dotenv import load_dotenv

load_dotenv()
models.Base.metadata.create_all(bind=engine)

app = FastAPI(title="ExpenseOwl Budget AI Service")

# Cấu hình Gemini sử dụng SDK mới
client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))

@app.post("/api/ai/chat")
def chat_with_data(req: schemas.ChatRequest, db: Session = Depends(get_db), current_user_id: int = Depends(auth.get_current_user_id)):
    # Lấy dữ liệu từ DB để AI phân tích
    transactions = db.query(models.Transaction).filter(models.Transaction.user_id == current_user_id).all()
    
    # Logic tạo prompt và gọi Gemini (tương tự routers.py cũ)
    # ...
    return {"reply": "Cú Mèo đang lắng nghe đây!", "action": "chat"}

@app.get("/health")
def health():
    return {"status": "ok"}