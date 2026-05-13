import os
import requests
import json
from fastapi import FastAPI
from pydantic import BaseModel
from dotenv import load_dotenv
from fastapi.middleware.cors import CORSMiddleware

# Load biến môi trường
load_dotenv()
PORT = int(os.getenv("PORT", 8002))
EXPENSE_SERVICE_URL = os.getenv("EXPENSE_SERVICE_URL", "http://127.0.0.1:8001/api/v1")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

app = FastAPI(title="AI Agent Service (REST API Mode)", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Chấp nhận mọi nguồn gọi tới
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class ChatRequest(BaseModel):
    message: str

@app.post("/api/v1/chat")
def chat_with_agent(req: ChatRequest):
    """API Giao tiếp: Web App -> AI Agent -> Expense Service"""
    
    # 1. Gọi thẳng vào máy chủ Google Gemini bằng REST API
    # Dòng mới đã thêm chữ "-latest"
    gemini_url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash-lite:generateContent?key={GEMINI_API_KEY}"
    
    # Dạy AI cách bóc tách dữ liệu và chỉ trả về JSON
    prompt = f"""
    Bạn là một trợ lý tài chính. Người dùng vừa nhắn: "{req.message}"
    Hãy trích xuất thông tin chi tiêu và trả về DUY NHẤT một chuỗi JSON chuẩn (không giải thích thêm), gồm 3 trường:
    - "amount": số tiền (kiểu số)
    - "category": phân loại bằng tiếng Anh (ví dụ: Food, Transport, Utilities, Entertainment, Shopping)
    - "description": ghi chú (chuỗi)
    Nếu câu nói không chứa thông tin tiêu tiền, trả về {{"error": "not_found"}}
    """
    
    payload = {"contents": [{"parts": [{"text": prompt}]}]}
    
    try:
        # Gửi dữ liệu cho Gemini
        ai_response = requests.post(gemini_url, json=payload)
        ai_data = ai_response.json()
        
        # IN RA MÀN HÌNH ĐỂ DEBUG XEM GOOGLE NÓI GÌ
        print(f"====> RAW DỮ LIỆU TỪ GOOGLE: {ai_data}")
        
        # Bắt lỗi nếu API Key sai hoặc Google từ chối
        if "error" in ai_data:
            error_msg = ai_data["error"].get("message", "Lỗi không xác định")
            return {"reply": f"Lỗi từ Google Gemini: {error_msg}"}
            
        # Lấy câu trả lời của AI
        text_result = ai_data['candidates'][0]['content']['parts'][0]['text']
        
        # Làm sạch chuỗi JSON (đề phòng AI bọc trong thẻ markdown ```json )
        clean_json = text_result.replace('```json', '').replace('```', '').strip()
        expense_info = json.loads(clean_json)
        
        # Kiểm tra xem AI có tìm thấy khoản chi nào không
        if "error" in expense_info:
             return {"reply": "Xin lỗi, tôi không thấy thông tin chi tiêu nào trong câu của bạn."}
             
        print(f"---> [AI ĐÃ PHÂN TÍCH]: {expense_info}")
             
        # 2. AI TỰ ĐỘNG GỌI TOOL: Gửi sang cổng 8001
        db_response = requests.post(f"{EXPENSE_SERVICE_URL}/expenses", json=expense_info)
        
        if db_response.status_code == 200:
             return {"reply": f"Dạ vâng, em đã ghi nhận khoản chi {expense_info['amount']:,.0f}đ vào danh mục {expense_info['category']} rồi ạ!"}
        else:
             return {"reply": f"Có lỗi khi lưu vào Database: {db_response.text}"}
             
    except Exception as e:
        return {"reply": f"Lỗi code Python: {str(e)}"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=PORT, reload=True)