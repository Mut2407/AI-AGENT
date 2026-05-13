from fastapi import APIRouter, HTTPException, UploadFile, File, Depends
from pydantic import BaseModel
from typing import List
import os
import json
import time
import uuid
import random
import requests
from datetime import datetime
import io
import base64
from PIL import Image
import fitz
import pandas as pd

import services

# GIẢ ĐỊNH: Đã có hàm giải mã JWT thành dict chứa "id"
from auth import get_current_user 

router = APIRouter(prefix="/api/ai", tags=["AI & OCR"])

# ==========================================
# CẤU HÌNH & HELPER GEMINI
# ==========================================
class ChatRequest(BaseModel):
    message: str
    history: list = []
    currency: str = "vnd"
    rate: float = 1.0

def get_random_api_key():
    keys_str = os.getenv("GEMINI_API_KEY", "")
    keys = [k.strip() for k in keys_str.split(",") if k.strip()]
    return random.choice(keys) if keys else None

def call_gemini_with_backoff(url, payload, headers=None, timeout=30, retries=3):
    headers = headers or {"Content-Type": "application/json"}
    for attempt in range(retries):
        try:
            response = requests.post(url, json=payload, headers=headers, timeout=timeout)
            if response.status_code in (429, 503):
                time.sleep((2**attempt) + random.random())
                continue
            if response.status_code >= 400:
                raise HTTPException(status_code=response.status_code, detail=response.text)
            return response
        except requests.exceptions.RequestException:
            time.sleep((2**attempt) + random.random())
    raise HTTPException(status_code=502, detail="Không thể liên hệ Gemini lúc này.")


# ==========================================
# 1. OCR QUÉT HÓA ĐƠN (ẢNH, PDF, CSV)
# ==========================================

@router.post("/scan-receipt")
async def scan_receipt(file: UploadFile = File(...), current_user: dict = Depends(get_current_user)):
    user_id = current_user["id"]
    api_key = get_random_api_key()
    if not api_key: raise HTTPException(status_code=500, detail="Chưa cấu hình API Key")

    config = services.get_user_config(user_id)
    categories_str = ", ".join(config.get("expenseCategories", [])) if config else "Ăn uống, Đi lại, Mua sắm"

    try:
        # Tiền xử lý ảnh Pillow
        original_bytes = await file.read()
        img = Image.open(io.BytesIO(original_bytes))
        if img.mode in ("RGBA", "P"): img = img.convert("RGB")
        img.thumbnail((1024, 1024), Image.Resampling.LANCZOS)

        output_buffer = io.BytesIO()
        img.save(output_buffer, format="JPEG", quality=85)
        base64_image = base64.b64encode(output_buffer.getvalue()).decode("utf-8")

        prompt = f"""Hôm nay là {datetime.now().strftime("%Y-%m-%d")}.
Phân tích hóa đơn, trả về DUY NHẤT một JSON object thuần:
{{
    "name": "Tên cửa hàng",
    "category": "Chọn ĐÚNG MỘT danh mục: {categories_str}",
    "amount": số_âm_đại_diện_chi_tiêu,
    "date": "YYYY-MM-DD",
    "tags": ["OCR"],
    "notes": ""
}}"""
        url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-3.1-flash-lite-preview:generateContent?key={api_key}"
        payload = {
            "contents": [{"parts": [{"text": prompt}, {"inlineData": {"mimeType": "image/jpeg", "data": base64_image}}]}],
            "generationConfig": {"temperature": 0.1}
        }

        response = call_gemini_with_backoff(url, payload)
        result_data = response.json()
        ai_text = result_data["candidates"][0]["content"]["parts"][0]["text"]
        clean_text = ai_text.strip().replace("```json", "").replace("```", "").strip()
        
        extracted_data = json.loads(clean_text)
        return {"status": "success", "data": extracted_data}
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Lỗi quét hóa đơn: {str(e)}")

# Tương tự, em giữ nguyên logic cho /scan-pdf (dùng fitz) và /scan-csv (dùng pandas) 
# như code cũ, chỉ cần thay phần get_db() bằng services.get_user_config()

# ==========================================
# 2. CHATBOT CỐ VẤN (AGENTIC AI)
# ==========================================

@router.post("/chat")
def chat_with_data(req: ChatRequest, current_user: dict = Depends(get_current_user)):
    user_id = current_user["id"]
    api_key = get_random_api_key()
    today_str = datetime.now().strftime("%Y-%m-%d")

    # 1. GOM DỮ LIỆU TỪ CÁC MICROSERVICES KHÁC (HTTP CALLS)
    user_config = services.get_user_config(user_id)
    all_txns = services.get_user_transactions(user_id)
    jars = services.get_jars(user_id)
    budgets = services.get_active_budgets(user_id, f"{datetime.now().year}-{datetime.now().month:02d}-01", today_str)

    # 2. XỬ LÝ LƯỢNG DỮ LIỆU BẰNG PYTHON (Thay cho SQL Queries)
    total_income = sum(t["amount"] for t in all_txns if t["amount"] > 0)
    total_expense = sum(abs(t["amount"]) for t in all_txns if t["amount"] < 0)
    total_wallet = total_income - total_expense
    
    total_in_jars = sum(j["balance"] for j in jars)
    free_bal = total_wallet - total_in_jars

    categories_str = ", ".join(user_config.get("expenseCategories", [])) if user_config else "Ăn uống, Đi lại, Mua sắm"
    goal = user_config.get("financial_goal", "Chưa có") if user_config else "Chưa có"

    # Định dạng chuỗi lịch sử hũ và ngân sách
    jars_context = "\n".join([f"- Hũ '{j['name']}': {j['balance']}" for j in jars]) or "Chưa có hũ."
    budgets_context = "\n".join([f"- Mục '{b['category']}': Đã tiêu {b['spent_amount']}/{b['limit_amount']}" for b in budgets]) or "Chưa có ngân sách."

    # 3. ÉP PROMPT CHO GEMINI
    prompt = f"""Bạn là Cú Mèo, cố vấn tài chính. Hôm nay: {today_str}.
TIỀN TỆ: {req.currency.upper()} (Tỷ giá: {req.rate}). MỤC TIÊU: {goal}.
DANH MỤC HỢP LỆ: {categories_str}

SỐ LIỆU TÀI CHÍNH (Đã quy đổi, tuyệt đối tin tưởng):
- TỔNG TÀI SẢN: {total_wallet / req.rate:,.0f}
- SỐ DƯ RẢNH RỖI (KHẢ DỤNG): {free_bal / req.rate:,.0f}
HŨ HIỆN CÓ:
{jars_context}
NGÂN SÁCH THÁNG NÀY:
{budgets_context}

LỊCH SỬ CHAT GẦN ĐÂY: {req.history[-3:] if req.history else 'Trống'}
CÂU HỎI TỪ KHÁCH HÀNG: "{req.message}"

TRẢ VỀ DUY NHẤT KHỐI JSON:
{{
    "reply": "Câu tư vấn",
    "action": "chat" | "save" | "jar_transfer" | "update_profile",
    "data": [
        {{ "name": "...", "amount": số (ÂM=chi, DƯƠNG=thu), "category": "...", "date": "YYYY-MM-DD", "jar_id": ID Hũ (nếu có) }}
    ] | null,
    "jar_data": {{ "type": "deposit" | "withdraw", "from_id": 1, "to_id": 2, "amount": số }} | null,
    "profile": {{ "goal": "...", "risk": "..." }} | null
}}
"""
    
    # 4. GỌI GEMINI VÀ BÓC TÁCH JSON
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-3.1-flash-lite-preview:generateContent?key={api_key}"
    response = call_gemini_with_backoff(url, {"contents": [{"parts": [{"text": prompt}]}], "generationConfig": {"temperature": 0.2}})
    ai_text = response.json()["candidates"][0]["content"]["parts"][0]["text"]
    clean_text = ai_text.strip().replace("```json", "").replace("```", "")
    result_json = json.loads(clean_text)

    # 5. XỬ LÝ HÀNH ĐỘNG DO AI YÊU CẦU
    final_action = result_json.get("action", "chat")
    transaction_data = None

    if final_action == "save" and result_json.get("data"):
        for item in result_json["data"]:
            tx_data = {
                "name": item.get("name", "Giao dịch AI"),
                "amount": float(item.get("amount", 0)) * req.rate,
                "category": item.get("category", "Khác"),
                "date": item.get("date", today_str),
                "tags": ["AI Chatbot"]
            }
            # LƯU Ý: Ở đây ta KHÔNG trừ tiền Hũ hay Ngân sách. 
            # Ta chỉ gọi API lưu Transaction. Kafka sẽ tự động lo phần còn lại!
            transaction_data = services.save_transaction(user_id, tx_data)

    elif final_action == "jar_transfer" and result_json.get("jar_data"):
        services.transfer_jars(user_id, result_json["jar_data"])
        
    elif final_action == "update_profile" and result_json.get("profile"):
        services.update_user_profile(user_id, result_json["profile"].get("goal"), result_json["profile"].get("risk"))

    return {
        "reply": result_json.get("reply", "Cú Mèo đã ghi nhận!"),
        "action": final_action,
        "transaction_data": transaction_data
    }