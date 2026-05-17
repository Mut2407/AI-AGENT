import os
import json
import time
import random
import requests
import re
import base64
from prometheus_fastapi_instrumentator import Instrumentator
import io
import traceback
from datetime import datetime, timedelta

from fastapi import Body, FastAPI, Depends, HTTPException, Request, File, UploadFile
from fastapi.middleware.cors import CORSMiddleware
# 🚀 ĐÃ THÊM: jsonable_encoder để xử lý lỗi sập FastAPI khi trả về dữ liệu DB
from fastapi.encoders import jsonable_encoder 
from pydantic import BaseModel
from PIL import Image
import fitz  # PyMuPDF dùng cho file PDF
import pandas as pd # Dùng cho file CSV

import services

# 🚀 BƯỚC 1: KHỞI TẠO APP VÀ MIDDLEWARE NGAY TRÊN CÙNG
app = FastAPI(title="ExpenseOwl AI Service")
Instrumentator().instrument(app).expose(app)
app.add_middleware(
    CORSMiddleware, 
    allow_origins=["*"], 
    allow_credentials=True, 
    allow_methods=["*"], 
    allow_headers=["*"],
)

# 🚀 BƯỚC 2: KHAI BÁO CÁC BIẾN MÔI TRƯỜNG 
USER_SERVICE_URL = os.getenv("USER_SERVICE_URL", "http://user-service:8000")
TXN_SERVICE_URL = os.getenv("TXN_SERVICE_URL", "http://transaction-service:8000")

# 🚀 BƯỚC 3: CÁC MODEL VÀ API CỦA EM
class ChatRequest(BaseModel):
    message: str
    history: list = []
    currency: str = "vnd"
    rate: float = 1.0
    
class SuggestionRequest(BaseModel):
    month_window: int
    goal_name: str
    goal_amount: float
    goal_months: int
    currency: str
    symbol: str
    rate: float
    
def get_current_user(req: Request):
    auth_header = req.headers.get("Authorization")
    if not auth_header:
        raise HTTPException(status_code=401, detail="Cú Mèo không thấy thẻ thông hành!")
    try:
        res = requests.get(f"{USER_SERVICE_URL}/api/auth/me", headers={"Authorization": auth_header})
        if res.status_code == 200:
            return res.json() 
        raise HTTPException(status_code=401, detail="Thẻ thông hành sai.")
    except requests.exceptions.RequestException:
        raise HTTPException(status_code=500, detail="Lỗi liên lạc User Service.")

def get_random_api_key():
    keys_str = os.getenv("GEMINI_API_KEY", "")
    keys = [k.strip() for k in keys_str.split(",") if k.strip()]
    return random.choice(keys) if keys else None

def call_gemini_with_backoff(url, payload, headers=None, timeout=30, retries=3):
    headers = headers or {"Content-Type": "application/json"}
    last_error = None
    for attempt in range(retries):
        try:
            response = requests.post(url, json=payload, headers=headers, timeout=timeout)
            if response.status_code in (429, 503):
                time.sleep((2**attempt) + random.random())
                continue
            if response.status_code >= 400:
                raise HTTPException(status_code=response.status_code, detail=response.text)
            return response
        except requests.exceptions.RequestException as e:
            print(f"⚠️ Lỗi mạng gọi Gemini (Lần {attempt+1}): {e}")
            last_error = e
            time.sleep((2**attempt) + random.random())
    raise HTTPException(status_code=502, detail=f"Mất kết nối Internet/DNS. Chi tiết: {last_error}")

@app.get("/")
def read_root():
    return {"status": "Cú Mèo AI Service đang hoạt động tốt! 🦉"}

@app.get("/api/users/config")
def get_user_categories(current_user: dict = Depends(get_current_user)):
    db_user_id = current_user.get("id")
    user_config = services.get_user_config(db_user_id) or {}
    
    exp_cats = user_config.get("expenseCategories", ["Ăn uống", "Đi lại", "Mua sắm", "Hóa đơn", "Giải trí"])
    inc_cats = user_config.get("incomeCategories", ["Lương", "Thưởng", "Đầu tư", "Khác"])
    
    all_categories = exp_cats + inc_cats
    return {"categories": all_categories}


# ==========================================
# API QUÉT HÓA ĐƠN BẰNG ẢNH 
# ==========================================
@app.post("/api/ai/extract")
async def extract_expense_info(file: UploadFile = File(...), current_user: dict = Depends(get_current_user)):
    try:
        api_key = get_random_api_key()
        if not api_key: raise HTTPException(status_code=500, detail="Chưa cấu hình GEMINI_API_KEY")

        content = await file.read()
        img = Image.open(io.BytesIO(content))
        if img.mode in ("RGBA", "P"): img = img.convert("RGB")
        img.thumbnail((1024, 1024), Image.Resampling.LANCZOS)
        
        output_buffer = io.BytesIO()
        img.save(output_buffer, format="JPEG", quality=85)
        base64_image = base64.b64encode(output_buffer.getvalue()).decode("utf-8")

        prompt = """Bạn là trợ lý tài chính. Trích xuất thông tin giao dịch trong ảnh.
        QUY TẮC QUAN TRỌNG VỀ SỐ TIỀN (amount):
        - Nếu là hóa đơn mua hàng, thanh toán, chuyển tiền ĐI (Chi tiêu) -> BẮT BUỘC biến 'amount' phải là SỐ ÂM (ví dụ: -50000).
        - Nếu là biên lai nhận tiền, chuyển tiền ĐẾN (Thu nhập) -> Biến 'amount' là SỐ DƯƠNG (ví dụ: 50000).
        - Trả về số nguyên hoặc số thực, KHÔNG chứa dấu phẩy/chấm phân cách hàng nghìn.

        Trả về DUY NHẤT một chuỗi JSON hợp lệ, KHÔNG GIẢI THÍCH:
        {
            "name": "Tên cửa hàng/người nhận/người gửi",
            "amount": -50000,
            "category": "Ăn uống, Mua sắm, Di chuyển, Hóa đơn, Lương, Khác",
            "date": "YYYY-MM-DD",
            "type": "chi" hoặc "thu"
        }"""

        url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-3.1-flash-lite-preview:generateContent?key={api_key}"
        payload = {
            "contents": [
                {
                    "parts": [
                        {"text": prompt},
                        {"inlineData": {"mimeType": "image/jpeg", "data": base64_image}}
                    ]
                }
            ],
            "generationConfig": {"temperature": 0.1, "responseMimeType": "application/json"}
        }

        response = call_gemini_with_backoff(url, payload)
        result_data = response.json()

        if "candidates" not in result_data or len(result_data["candidates"]) == 0:
            raise HTTPException(status_code=400, detail="Gemini từ chối phân tích ảnh.")
            
        ai_text = result_data["candidates"][0]["content"]["parts"][0].get("text", "")
        match = re.search(r"\{.*\}", ai_text, re.DOTALL)
        clean_text = match.group(0) if match else ai_text.strip()
        
        return {"status": "success", "data": json.loads(clean_text)}

    except Exception as e:
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


# ==========================================
# API QUÉT SAO KÊ PDF 
# ==========================================
@app.post("/api/ai/scan-pdf")
async def scan_pdf_statement(file: UploadFile = File(...), current_user: dict = Depends(get_current_user)):
    try:
        api_key = get_random_api_key()
        if not api_key: raise HTTPException(status_code=500, detail="Chưa cấu hình API Key")

        if file.content_type != "application/pdf":
            raise HTTPException(status_code=400, detail="Chỉ hỗ trợ file PDF!")

        pdf_bytes = await file.read()
        text_content = ""
        with fitz.open(stream=pdf_bytes, filetype="pdf") as doc:
            for page in doc:
                text_content += page.get_text() + "\n"

        if not text_content.strip():
            raise HTTPException(status_code=400, detail="PDF không có chữ để phân tích.")
        text_content = text_content[:40000]

        prompt = f"""Trích xuất danh sách giao dịch từ nội dung PDF sao kê/biên lai sau. 
        QUY TẮC QUAN TRỌNG VỀ SỐ TIỀN (amount):
        - Giao dịch GHI NỢ, chuyển tiền ĐI, thanh toán, trừ phí (Chi tiêu) -> BẮT BUỘC 'amount' là SỐ ÂM (ví dụ: -100000).
        - Giao dịch GHI CÓ, nhận tiền, lương, hoàn tiền (Thu nhập) -> BẮT BUỘC 'amount' là SỐ DƯƠNG (ví dụ: 100000).
        - Trả về số, KHÔNG chứa dấu phẩy/chấm phân cách.

        Trả về MẢNG JSON, KHÔNG BÌNH LUẬN GÌ THÊM:
        [
            {{ "name": "Tên giao dịch/Người nhận/Gửi", "amount": -100000, "category": "Khác", "date": "YYYY-MM-DD", "type": "chi" }}
        ]
        Nội dung: {text_content}"""

        url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-3.1-flash-lite-preview:generateContent?key={api_key}"
        payload = {"contents": [{"parts": [{"text": prompt}]}], "generationConfig": {"temperature": 0.1, "responseMimeType": "application/json"}}

        response = call_gemini_with_backoff(url, payload)
        result_data = response.json()

        ai_text = result_data["candidates"][0]["content"]["parts"][0].get("text", "")
        match = re.search(r"\[.*\]", ai_text, re.DOTALL)
        clean_text = match.group(0) if match else ai_text.strip()
        transactions = json.loads(clean_text)
        if not isinstance(transactions, list): transactions = [transactions]
        
        return {"status": "success", "data": transactions}
    except Exception as e:
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))

# ==========================================
# API QUÉT FILE CSV 
# ==========================================
@app.post("/api/ai/scan-csv")
async def scan_csv_file(file: UploadFile = File(...), current_user: dict = Depends(get_current_user)):
    try:
        api_key = get_random_api_key()
        if not file.filename.lower().endswith(".csv"):
            raise HTTPException(status_code=400, detail="Chỉ hỗ trợ file .csv")

        content = await file.read()
        df = pd.read_csv(io.BytesIO(content))
        df.dropna(how="all", inplace=True)
        csv_text = df.head(50).to_csv(index=False)

        prompt = f"""Trích xuất danh sách giao dịch từ nội dung CSV sao kê ngân hàng sau. 
        QUY TẮC QUAN TRỌNG VỀ SỐ TIỀN (amount):
        - Giao dịch GHI NỢ, chuyển tiền ĐI, thanh toán, trừ phí (Chi tiêu) -> BẮT BUỘC 'amount' là SỐ ÂM (ví dụ: -100000).
        - Giao dịch GHI CÓ, nhận tiền, lương, hoàn tiền (Thu nhập) -> BẮT BUỘC 'amount' là SỐ DƯƠNG (ví dụ: 100000).
        - Trả về số, KHÔNG chứa dấu phẩy/chấm phân cách.

        Trả về MẢNG JSON, KHÔNG BÌNH LUẬN GÌ THÊM:
        [
            {{ "name": "Tên giao dịch/Người nhận/Gửi", "amount": -100000, "category": "Khác", "date": "YYYY-MM-DD", "type": "chi" }}
        ]
        Nội dung: {csv_text}"""

        url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-3.1-flash-lite-preview:generateContent?key={api_key}"
        payload = {"contents": [{"parts": [{"text": prompt}]}], "generationConfig": {"temperature": 0.1, "responseMimeType": "application/json"}}

        response = call_gemini_with_backoff(url, payload)
        result_data = response.json()

        ai_text = result_data["candidates"][0]["content"]["parts"][0].get("text", "")
        match = re.search(r"\[.*\]", ai_text, re.DOTALL)
        clean_text = match.group(0) if match else ai_text.strip()
        transactions = json.loads(clean_text)
        if not isinstance(transactions, list): transactions = [transactions]
        
        return {"status": "success", "data": transactions}
    except Exception as e:
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))
    

# ==========================================
# API CHATBOX
# ==========================================
@app.post("/api/ai/chat")
def chat_with_data(req: ChatRequest, current_user: dict = Depends(get_current_user)):
    db_user_id = current_user.get("id")          
    username = current_user.get("username")      
    
    api_key = get_random_api_key()
    if not api_key:
        raise HTTPException(status_code=500, detail="Chưa cấu hình GEMINI_API_KEY")

    today_str = datetime.now().strftime("%Y-%m-%d")
    current_month = datetime.now().month
    current_year = datetime.now().year

    # 1. GỌI DỮ LIỆU TỪ CÁC MICROSERVICES
    user_config = services.get_user_config(db_user_id) or {}
    all_txns = services.get_user_transactions(username) or []
    jars = services.get_jars(username) or []
    budgets = services.get_active_budgets(username, f"{current_year}-{current_month:02d}-01", today_str) or []

    # 2. XỬ LÝ DANH MỤC HỢP LỆ
    exp_cats = user_config.get("expenseCategories", ["Ăn uống", "Đi lại", "Mua sắm", "Hóa đơn", "Giải trí"])
    inc_cats = user_config.get("incomeCategories", ["Lương", "Thưởng", "Đầu tư", "Khác"])
    allowed_categories = exp_cats + inc_cats
    if "Khác" not in allowed_categories: allowed_categories.append("Khác")
    categories_str = f"Chi tiêu gồm ({', '.join(exp_cats)}) | Thu nhập gồm ({', '.join(inc_cats)})"

    current_goal = user_config.get("financial_goal", "Chưa xác định")
    current_risk = user_config.get("risk_tolerance", "Cân bằng")

    # 3. TÍNH TOÁN SỐ DƯ
    total_income_all = sum(float(t.get("amount", 0) or 0) for t in all_txns if float(t.get("amount", 0) or 0) > 0)
    total_expense_all = sum(abs(float(t.get("amount", 0) or 0)) for t in all_txns if float(t.get("amount", 0) or 0) < 0)
    balance_all = total_income_all - total_expense_all

    txns_this_month = []
    for t in all_txns:
        try:
            d = datetime.fromisoformat(t.get("date", "").replace("Z", ""))
            if d.month == current_month and d.year == current_year: txns_this_month.append(t)
        except: pass

    total_income_month = sum(float(t.get("amount", 0) or 0) for t in txns_this_month if float(t.get("amount", 0) or 0) > 0)
    total_expense_month = sum(abs(float(t.get("amount", 0) or 0)) for t in txns_this_month if float(t.get("amount", 0) or 0) < 0)

    # 4. TÌM GIAO DỊCH ĐỂ SỬA
    recent_txns = sorted(all_txns, key=lambda x: x.get("date", ""), reverse=True)[:5]
    text_to_search = req.message + (" " + req.history[-1].get("user", "") if req.history else "")
    stop_words = {"bạn", "hãy", "ghi", "rõ", "lại", "là", "tháng", "ngày", "thứ", "cho", "tôi", "nhé", "vào", "của", "đã", "sửa", "thành", "nhầm"}
    keywords = [word for word in text_to_search.split() if len(word) > 2 and word.lower() not in stop_words]
    
    related_txns = []
    if keywords:
        for t in all_txns:
            if any(kw.lower() in str(t.get("name", "")).lower() for kw in keywords):
                related_txns.append(t)
    related_txns = sorted(related_txns, key=lambda x: x.get("date", ""), reverse=True)[:10]

    all_context_txns = {t["id"]: t for t in (recent_txns + related_txns)}.values()
    data_context = "GIAO DỊCH ĐỂ SỬA:\n"
    if not all_context_txns: data_context += "Trống.\n"
    else:
        for t in all_context_txns:
            amt_float = float(t.get('amount', 0) or 0)
            data_context += f"ID: {t['id']} | Ngày: {t.get('date', '').split('T')[0]} | Tên: {t.get('name')} | Tiền: {amt_float} | Nhóm: {t.get('category')}\n"

    total_in_jars = sum(float(j.get("balance", 0) or 0) for j in jars)
    
    # 5. CHUẨN BỊ BIẾN CHO PROMPT
    t_bal_all = balance_all / req.rate
    free_bal_all = (balance_all - total_in_jars) / req.rate
    t_inc_month = total_income_month / req.rate
    t_exp_month = total_expense_month / req.rate

    jars_context = "QUỸ (HŨ):\n" + ("".join([f"- '{j['name']}': Số dư {(float(j.get('balance', 0) or 0) / req.rate):,.0f} | Mục tiêu {(float(j.get('goal_amount', 0) or 0) / req.rate):,.0f}\n" for j in jars]) if jars else "Trống.\n")
    budgets_context = "NGÂN SÁCH:\n" + ("".join([f"- '{b['category']}': Đã tiêu {(abs(float(b.get('spent_amount',0) or 0)) / req.rate):,.0f} / Hạn mức {(float(b.get('limit_amount',0) or 0)) / req.rate:,.0f}\n" for b in budgets]) if budgets else "Trống.\n")
    history_text = "LỊCH SỬ CHAT:\n" + "".join([f"User: {turn.get('user', '')}\nAI: {turn.get('ai', '')}\n" for turn in req.history[-3:]]) if req.history else ""

    # 6. GỬI PROMPT (ĐÃ BAO GỒM TOÀN BỘ LUẬT THÉP)
    prompt = f"""
    Bạn là "Cú Mèo" - Cố vấn tài chính cá nhân của ExpenseOwl. Hôm nay: {today_str}.
    TIỀN TỆ HIỆN TẠI: {req.currency.upper()} (Tỷ giá 1 {req.currency.upper()} = {req.rate} VNĐ).
    HỒ SƠ KHÁCH HÀNG: Mục tiêu: {current_goal} | Khẩu vị rủi ro: {current_risk}.
    
    🚨 DANH MỤC HỢP LỆ CỦA KHÁCH HÀNG (QUAN TRỌNG):
    {categories_str}
    (AI TUYỆT ĐỐI KHÔNG tự chế ra tên danh mục mới ngoài danh sách trên).
    
    🚨 CẤU TRÚC TÀI SẢN & THỐNG KÊ (TUYỆT ĐỐI TIN TƯỞNG SỐ NÀY, KHÔNG TỰ CỘNG LẠI):
    - 🏦 TỔNG TÀI SẢN (Gồm tất cả tiền): {t_bal_all:,.0f} {req.currency.upper()}
    - 💰 SỐ DƯ KHẢ DỤNG (Tiền rảnh rỗi chưa cất vào hũ): {free_bal_all:,.0f} {req.currency.upper()}
    [THÁNG {current_month}/{current_year}] Tổng thu: {t_inc_month:,.0f} | Tổng chi: {t_exp_month:,.0f}
    
    {jars_context}
    {budgets_context}
    {data_context}
    {history_text}
    
    CÂU HỎI TỪ KHÁCH HÀNG: "{req.message}"
    
    NHIỆM VỤ: Trả về DUY NHẤT 1 KHỐI JSON TỰ THUẦN (Không kèm markdown ```).

    🚨 QUY TẮC TỐI THƯỢNG (KIỂM TRA ĐẦU TIÊN TRƯỚC KHI LÀM VIỆC KHÁC):
    Nếu câu nói của khách CÓ SỐ TIỀN nhưng KHÔNG CÓ TÊN MÓN HÀNG/MỤC ĐÍCH (VD: "Hôm qua tiêu mất 500k", "Mới rớt 100k"):
    => BẮT BUỘC PHẢI DỪNG MỌI TƯ VẤN KHÁC. Trả về action "chat" và đặt câu hỏi ép khách khai báo: "Cú Mèo rất tiếc/chúc mừng bạn! Nhưng khoản [Số tiền] đó bạn dùng vào việc gì vậy? Khai báo để Cú Mèo lưu sổ nhé!". TUYỆT ĐỐI KHÔNG báo cáo số dư hay khuyên bảo dài dòng trong trường hợp này.

    🚨 LUẬT THÉP VỀ HŨ (JARS) & NGÂN SÁCH (BUDGETS):
    1. LUẬT NẠP HŨ: Nạp hũ là LẤY TIỀN TỪ "SỐ DƯ KHẢ DỤNG" đưa vào hũ. Phải kiểm tra "SỐ DƯ KHẢ DỤNG" xem có đủ tiền nạp không.
    2. LUẬT CHI TIÊU HŨ: Khách hàng chi tiêu bình thường sẽ bị trừ ở "SỐ DƯ KHẢ DỤNG". Nếu khách nói rõ "tiêu từ hũ X", hãy đưa tên hũ X vào trường "jar_name".
    3. LUẬT CẢNH BÁO NGÂN SÁCH THEO MỨC ĐỘ: Khi ghi nhận khoản chi tiêu mới, bạn PHẢI tự nhẩm tính: Tỷ lệ % = (Đã tiêu + Khoản chi mới) / Hạn mức. Hãy phản hồi theo đúng 4 mức độ sau:
       - Mức Xanh (<75%): Khen ngợi.
       - Mức Vàng (75-89%): Nhắc nhở.
       - Mức Đỏ (90-100%): Cảnh báo sắp lố.
       - Lố ngân sách (>100%): Cảnh báo vượt giới hạn.

    🚨 QUY TẮC CHỌN "ACTION" VÀ XỬ LÝ DỮ LIỆU:
    1. "reply": Tư vấn thân thiện, ngắn gọn. 🚨 KHI NHẮC ĐẾN SỐ DƯ HAY TIỀN BẠC: Bạn BẮT BUỘC phải dùng định dạng Markdown in đậm cho con số (Ví dụ: **5,000,000 VND**). Lưu ý: Nếu bạn chọn lệnh "save", hệ thống Python sẽ tự động tính và chèn số dư mới nhất vào cuối câu bằng Markdown, bạn không cần tự tính lại số dư trong câu nói của mình để tránh sai sót.
    2. "category" (DANH MỤC): TUYỆT ĐỐI KHÔNG TỰ BỊA. Nếu không có danh mục phù hợp, ép vào "Khác" VÀ dặn khách: "Cú Mèo tạm xếp vào [Khác]. Bạn hãy vào Cài đặt thêm danh mục mới nhé!".
    3. CÁC HÀNH ĐỘNG HỢP LỆ:
       - "save": TẠO MỚI (Có ĐỦ Tên khoản VÀ Số tiền). Giá trị lưu 'amount' CHỈ LẤY SỐ THEO ĐƠN VỊ {req.currency.upper()}, KHÔNG TỰ NHÂN TỶ GIÁ.
       - "update": SỬA giao dịch. ⚠️ LUẬT THÉP CHỐNG ĐOÁN MÒ: Hãy kiểm tra loại mặt hàng khách nhắc đến (VD: "sách", "trà sữa"). NẾU TRONG DANH SÁCH GIAO DỊCH GẦN ĐÂY CÓ TỪ 2 GIAO DỊCH TRỞ LÊN CHỨA MẶT HÀNG ĐÓ, TUYỆT ĐỐI KHÔNG TỰ ĐOÁN (kể cả khi khách nói "lúc nãy", "vừa xong"). Bắt buộc chuyển action thành "chat" và hỏi: "Cú Mèo thấy có nhiều giao dịch liên quan đến [Tên mặt hàng], bạn muốn sửa khoản chính xác nào?". CHỈ dùng "update" khi danh sách chỉ có DUY NHẤT 1 kết quả khớp.
       - "update_profile": CHỈ KHI khách đổi mục tiêu DÀI HẠN. ⚠️ BẮT BUỘC GOM NHÓM YÊU CẦU: Điền vào trường "financial_goal" ĐÚNG 1 CỤM TỪ TRONG: [Tiết kiệm phòng thân, Đầu tư sinh lời, Trả dứt điểm nợ, Mua sắm tài sản lớn, Cải thiện dòng tiền]. Điền vào "risk_tolerance" ĐÚNG 1 TỪ TRONG: [An toàn, Cân bằng, Mạo hiểm].
       - "create_jar" / "delete_jar": Tạo mới hoặc Xóa hũ.
       🚨 LUẬT BẮT BUỘC KHI XÓA HŨ:
         Trước khi thực hiện xóa, bạn PHẢI kiểm tra 'Số dư' của hũ đó trong dữ liệu QUỸ (HŨ) được cung cấp.
         + Nếu Số dư = 0: Thực hiện trả về action "delete_jar" bình thường.
         + Nếu Số dư > 0: TUYỆT ĐỐI KHÔNG trả về action "delete_jar". Bạn phải dùng action "chat" để cảnh báo người dùng: "Hũ [Tên hũ] đang có số dư [Số tiền]. Nếu xóa, số tiền này sẽ được hoàn lại về ví chính của bạn. Bạn có chắc chắn muốn xóa không?".
         + Khi và chỉ khi người dùng chat lại xác nhận (VD: "chắc chắn", "đồng ý", "cứ xóa đi"), bạn mới được phép gọi action "delete_jar".
       - "jar_transfer": NẠP/RÚT/CHUYỂN tiền giữa các hũ.
       - "chat": Trò chuyện bình thường, giải đáp thắc mắc.
       - "set_budget": Thiết lập hoặc cập nhật hạn mức ngân sách. 🚨 LƯU Ý TỐI QUAN TRỌNG: Bạn BẮT BUỘC phải xuất ra khối "budget_data" chứa "category" và "limit_amount". Nếu không có khối này, hệ thống sẽ bị sập!
       - "delete_budget": Xóa ngân sách. 🚨 BẮT BUỘC phải xuất ra khối "budget_data" với "limit_amount" bằng 0.

    🚨 QUY TẮC XỬ LÝ NGỮ CẢNH & THỜI GIAN (CONTEXT HANDLING):
    1. KẾ THỪA MỐC THỜI GIAN: Nếu câu hỏi của khách hàng mập mờ, thiếu mốc thời gian cụ thể (VD: "còn khoản nào", "tiếp theo", "vậy còn..."), bạn PHẢI tự động sử dụng mốc thời gian gần nhất mà bạn vừa nhắc đến trong lịch sử trò chuyện.
    2. CHỦ ĐỘNG ĐỀ XUẤT (PROACTIVE): Nếu khách hỏi dữ liệu của một thời điểm (VD: Tháng 4) nhưng không có kết quả, MÀ bạn thấy trong dữ liệu có giao dịch ở thời điểm lân cận (VD: Tháng 5), hãy TỰ ĐỘNG liệt kê/đề xuất dữ liệu lân cận đó ra để hỗ trợ khách hàng. KHÔNG thụ động đợi khách phải hỏi lại chính xác tháng.
       
    CẤU TRÚC JSON PHẢI TRẢ VỀ:
    {{
        "reply": "Câu trả lời của bạn",
        "action": "chat" | "save" | "update" | "update_profile" | "create_jar" | "delete_jar" | "jar_transfer" | "set_budget" | "delete_budget",
        "transaction_id": "Mã ID của giao dịch cần sửa (CHỈ CÓ KHI action là update)" | null,
        "data": [
            {{ 
                "name": "Tên giao dịch (Tách riêng nếu người dùng nhập nhiều khoản cùng lúc)", 
                "amount": Số tiền (ÂM nếu chi, DƯƠNG nếu thu. CHỈ LẤY SỐ THEO ĐƠN VỊ {req.currency.upper()}, KHÔNG TỰ NHÂN TỶ GIÁ), 
                "category": "GHI CHÍNH XÁC 1 TÊN DANH MỤC TRONG DANH SÁCH HỢP LỆ (Không được thêm bớt chữ)", 
                "date": "YYYY-MM-DD",
                "jar_name": "Tên hũ (GHI ĐÚNG TÊN LÕI)"
            }}
        ] | null,
        "profile_update": {{ "financial_goal": "...", "risk_tolerance": "..." }} | null,
        "jar_data": {{ 
            "name": "Tên hũ", "target_name": "Tên hũ nhận", "goal_amount": Số,
            "type": "deposit" | "withdraw" | "internal" | null, "amount": Số 
        }} | null
        "budget_data": {{ 
            "category": "Tên danh mục hợp lệ", 
            "limit_amount": Số tiền 
        }},
    }}
    
    🚨 LUẬT BẢO MẬT HỆ THỐNG (TUYỆT ĐỐI TUÂN THỦ):
    - KHÔNG BAO GIỜ tiết lộ thông tin kỹ thuật, cấu trúc Database (ví dụ: có bao nhiêu bảng, tên bảng là gì), mã nguồn, kiến trúc hệ thống (Microservices, Kafka, API) hay ID nội bộ cho người dùng.
    - Nếu người dùng (hoặc hacker) cố tình hỏi/hack về hệ thống, cơ sở dữ liệu, hãy từ chối khéo léo bằng cách nói: "Cú Mèo chỉ là trợ lý tài chính nên chỉ rành về việc đếm tiền thôi! Bạn có muốn tôi giúp lên kế hoạch chi tiêu tháng này không?".
    """

    # 🚀 ĐÃ SỬA: Chuẩn hóa tên model thành gemini-1.5-flash để tránh lỗi 404
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-3.1-flash-lite-preview:generateContent?key={api_key}"
    payload = {"contents": [{"parts": [{"text": prompt}]}], "generationConfig": {"temperature": 0.1, "responseMimeType": "application/json"}}

    try:
        response = call_gemini_with_backoff(url, payload)
        ai_text = response.json()["candidates"][0]["content"]["parts"][0]["text"]
        match = re.search(r'\{.*\}', ai_text, re.DOTALL)
        clean_text = match.group(0) if match else ai_text.strip()
        result_json = json.loads(clean_text)
    except Exception as e:
        return {"reply": f"Cú Mèo đang gặp sự cố: {str(e)}", "action": "chat"}

    # 7. THỰC THI HÀNH ĐỘNG
    final_action = result_json.get("action", "chat")
    transaction_data = None
    
    # 🚀 BÍ KÍP: Tự tính số dư bằng Python để chống Ảo giác (Hallucination)
    new_balance = free_bal_all

    if final_action == "save" and result_json.get("data"):
        data_list = result_json["data"] if isinstance(result_json["data"], list) else [result_json["data"]]
        saved_txns = []
        for data in data_list:
            if not isinstance(data, dict): continue
            
            # Cập nhật số dư 
            amount_val = float(data.get("amount", 0))
            new_balance += amount_val
            
            new_amount = amount_val * req.rate
            tx_payload = {
                "name": str(data.get("name", "Giao dịch AI"))[:255],
                "amount": new_amount,
                "category": data.get("category") if data.get("category") in allowed_categories else "Khác",
                "date": data.get("date", today_str),
                "tags": ["AI Chatbot"]
            }
            try:
                res_txn = services.save_transaction(username, tx_payload)
                if res_txn: saved_txns.append(res_txn)
            except Exception as e:
                print("Lỗi lưu:", e)

        # 🚀 BÍ KÍP: Dùng jsonable_encoder để xử lý lỗi sập Serialization khi trả về Frontend
        transaction_data = jsonable_encoder(saved_txns[0]) if saved_txns else None

    elif final_action == "update" and result_json.get("transaction_id") and result_json.get("data"):
        target_id = result_json["transaction_id"]
        data = result_json["data"][0] if isinstance(result_json["data"], list) else result_json["data"]
        update_payload = {"name": data.get("name"), "category": data.get("category"), "amount": float(data.get("amount", 0)) * req.rate if "amount" in data else None, "date": data.get("date")}
        headers = services.get_headers(username)
        requests.put(f"{TXN_SERVICE_URL}/api/expenses/internal/update/{target_id}", json=update_payload, headers=headers)

    elif final_action == "jar_transfer" and result_json.get("jar_data"):
        j_data = result_json["jar_data"]
        
        # 1. Chuẩn hóa Type
        raw_type = str(j_data.get("type", "")).strip().lower()
        if "withdraw" in raw_type or "rút" in raw_type:
            action_type = "withdraw"
        elif "internal" in raw_type or "chuyển" in raw_type:
            action_type = "internal"
        else:
            action_type = "deposit"
            
        # FIX CỐT LÕI: Không khai báo to_id và from_id bằng None nữa
        transfer_payload = {
            "type": action_type,
            "amount": float(j_data.get("amount", 0)) * req.rate
        }
        
        # 2. Chuẩn hóa Tên hũ
        raw_name = j_data.get("name") or j_data.get("jar_name") or ""
        jar_name = str(raw_name).lower().replace("hũ", "").strip()
        
        raw_target = j_data.get("target_name") or ""
        target_name = str(raw_target).lower().replace("hũ", "").strip()
        
        # 3. Thuật toán quét và dò tìm ID hũ
        for j in jars:
            db_name = str(j.get("name", "")).lower().replace("hũ", "").strip()
            
            if jar_name and (jar_name in db_name or db_name in jar_name):
                if action_type == "deposit":
                    transfer_payload["to_id"] = j["id"]
                elif action_type in ["withdraw", "internal"]:
                    transfer_payload["from_id"] = j["id"]
                    
            if target_name and (target_name in db_name or db_name in target_name):
                transfer_payload["to_id"] = j["id"]
                
            if action_type == "deposit" and target_name and "to_id" not in transfer_payload:
                if target_name in db_name or db_name in target_name:
                    transfer_payload["to_id"] = j["id"]

        # 4. Gửi API an toàn
        try:
            # Kiểm tra xem có lấy được ID nào chưa (Bằng cách check key trong Dict)
            if "to_id" not in transfer_payload and "from_id" not in transfer_payload:
                raise Exception("Không nhận diện được tên hũ")
            
            services.transfer_jars(username, transfer_payload)
        except Exception as e:
            error_msg = str(e.detail) if hasattr(e, 'detail') else "Không khớp được hũ nào như bạn nói."
            result_json["reply"] = result_json.get("reply", "") + f"\n\n❌ Lỗi giao dịch: {error_msg}"
            print("Lỗi chuyển quỹ:", e)
        
    elif final_action == "create_jar" and result_json.get("jar_data"):
        j_data = result_json["jar_data"]
        j_data["goal_amount"] = float(j_data.get("goal_amount", 0)) * req.rate 
        services.create_jar(username, j_data)
        
    elif final_action == "delete_jar" and result_json.get("jar_data"):
        services.delete_jar_by_name(username, result_json["jar_data"].get("name", ""))
    
    elif final_action in ["set_budget", "delete_budget"]:
        b_data = result_json.get("budget_data")
        
        if not b_data:
            temp = result_json.get("data")
            if isinstance(temp, list) and len(temp) > 0:
                b_data = temp[0]
            elif isinstance(temp, dict):
                b_data = temp
        
        if b_data:
            cat = b_data.get("category", "Khác")
            if final_action == "delete_budget":
                limit_amt = 0 
            else:
                limit_amt = float(b_data.get("limit_amount", b_data.get("amount", 0))) * req.rate
                
            payload = {
                "category": cat,
                "limit_amount": limit_amt
            }
            try:
                services.set_budget(username, payload)
            except Exception as e:
                error_msg = str(e.detail) if hasattr(e, 'detail') else str(e)
                result_json["reply"] = result_json.get("reply", "") + f"\n\n❌ Lỗi hệ thống: {error_msg}"
        else:
            result_json["reply"] = result_json.get("reply", "") + f"\n\n❌ Lỗi hệ thống: Cú Mèo không xuất ra được dữ liệu (JSON bị trống)."

    elif final_action == "update_profile" and result_json.get("profile_update"):
        p_update = result_json["profile_update"]
        services.update_user_profile(db_user_id, p_update.get("financial_goal"), p_update.get("risk_tolerance"))

    # 🚀 BÍ KÍP: Gắn kết quả số dư trực tiếp vào câu trả lời
    bot_reply = result_json.get("reply", "Cú Mèo đã hoàn tất nhiệm vụ!")
    if final_action == "save":
        bot_reply += f"\n\n💰 **Số dư khả dụng hiện tại:** **{new_balance:,.0f} {req.currency.upper()}**"

    return {
        "reply": bot_reply,
        "action": final_action,
        "transaction_data": transaction_data
    }

@app.post("/api/ai/spending-suggestions")
def generate_spending_suggestions(req: SuggestionRequest, current_user: dict = Depends(get_current_user)):
    username = current_user.get("username")
    
    api_key = get_random_api_key()
    if not api_key:
        raise HTTPException(status_code=500, detail="Chưa cấu hình GEMINI_API_KEY")

    # 1. TẢI VÀ LỌC GIAO DỊCH
    all_txns = services.get_user_transactions(username) or []
    
    # Xác định mốc thời gian (1, 3, hoặc 6 tháng trước)
    cutoff_date = datetime.now() - timedelta(days=30 * req.month_window)
    
    category_expenses = {}
    
    for t in all_txns:
        try:
            tx_date = datetime.fromisoformat(t.get("date", "").replace("Z", ""))
            amt = float(t.get("amount", 0) or 0)
            
            # Chỉ lấy các khoản Chi Tiêu (số âm) và nằm trong khoảng thời gian đã chọn
            if amt < 0 and tx_date >= cutoff_date:
                cat = t.get("category", "Khác")
                display_amt = abs(amt) / req.rate
                # 🚀 Đã sửa category_average thành category_expenses
                category_expenses[cat] = category_expenses.get(cat, 0) + display_amt
        except: pass

    # Tính TRUNG BÌNH MỖI THÁNG cho từng danh mục
    avg_monthly_expenses = {cat: total / req.month_window for cat, total in category_expenses.items() if total > 0}
    total_avg_month = sum(avg_monthly_expenses.values())

    # Tính số tiền cần tiết kiệm mỗi tháng để đạt mục tiêu
    monthly_savings_needed = 0
    if req.goal_months > 0:
        monthly_savings_needed = (req.goal_amount) / req.goal_months

    # Chuẩn bị dữ liệu cho AI đọc
    spending_context = "\n".join([f"- {cat}: {amt:,.0f} {req.currency.upper()}/tháng" for cat, amt in avg_monthly_expenses.items()])
    if not spending_context:
        spending_context = "Hiện tại người dùng chưa có dữ liệu chi tiêu nào trong khoảng thời gian này."

    # 2. XÂY DỰNG PROMPT (NHỒI LUẬT JSON KHẮT KHE)
    prompt = f"""
    Bạn là chuyên gia tài chính "Cú Mèo" của ExpenseOwl.
    Người dùng muốn tiết kiệm để: "{req.goal_name}".
    Số tiền cần tiết kiệm: {req.goal_amount:,.0f} {req.currency.upper()} trong {req.goal_months} tháng.
    Mục tiêu tiết kiệm mỗi tháng: {monthly_savings_needed:,.0f} {req.currency.upper()}/tháng.

    BẢNG CHI TIÊU TRUNG BÌNH {req.month_window} THÁNG QUA CỦA NGƯỜI DÙNG:
    {spending_context}
    Tổng chi tiêu trung bình: {total_avg_month:,.0f} {req.currency.upper()}/tháng.

    NHIỆM VỤ: Hãy phân tích và đề xuất cách cắt giảm các khoản chi tiêu trên để dư ra được {monthly_savings_needed:,.0f} mỗi tháng. Đừng cắt giảm các khoản bắt buộc (Hóa đơn, Tiền nhà). Hãy tập trung vào (Mua sắm, Giải trí, Ăn uống).

    TRẢ VỀ DUY NHẤT 1 KHỐI JSON, KHÔNG CÓ MARKDOWN BỌC NGOÀI, ĐÚNG ĐỊNH DẠNG SAU:
    {{
        "feasibility": "high" | "medium" | "low", 
        "overall_strategy": "Câu tóm tắt chiến lược...",
        "monthly_savings_needed": {monthly_savings_needed},
        "category_plans": [
            {{
                "category": "Tên danh mục (lấy từ bảng trên)",
                "current_avg_spend": Số tiền trung bình hiện tại,
                "target_spend": Số tiền mục tiêu sau khi cắt giảm,
                "reduction_amount": Số tiền bị cắt giảm,
                "how_to_achieve": "1 câu ngắn khuyên cách làm sao để giảm được"
            }}
        ]
    }}
    Lưu ý phần feasibility: Nếu monthly_savings_needed lớn hơn Tổng chi tiêu trung bình, hãy đánh giá là "low".
    """

    # 🚀 ĐÃ SỬA: Chuẩn hóa tên model thành gemini-1.5-flash để tránh lỗi 404
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-3.1-flash-lite-preview:generateContent?key={api_key}"
    payload = {
        "contents": [{"parts": [{"text": prompt}]}], 
        "generationConfig": {"temperature": 0.2, "responseMimeType": "application/json"}
    }

    try:
        response = call_gemini_with_backoff(url, payload)
        ai_text = response.json()["candidates"][0]["content"]["parts"][0]["text"]
        match = re.search(r'\{.*\}', ai_text, re.DOTALL)
        clean_text = match.group(0) if match else ai_text.strip()
        result_json = json.loads(clean_text)
        return result_json
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Cú Mèo tính toán thất bại. Chi tiết: {str(e)}")