import os
import requests
from dotenv import load_dotenv

# Đọc API Key từ file .env
load_dotenv()
api_key = os.getenv("GEMINI_API_KEY")

print(f"[*] Đang kiểm tra API Key: {api_key[:8]}... (đã ẩn phần đuôi)")

# Gọi API ListModels của Google
url = f"https://generativelanguage.googleapis.com/v1beta/models?key={api_key}"
response = requests.get(url)

if response.status_code == 200:
    data = response.json()
    print("\n==== DANH SÁCH CÁC MODEL BẠN ĐƯỢC PHÉP SỬ DỤNG ====")
    for model in data.get('models', []):
        # Chỉ lấy những model hỗ trợ tính năng chat (generateContent)
        if 'generateContent' in model.get('supportedGenerationMethods', []):
            # Cắt bỏ chữ 'models/' ở đầu để lấy đúng tên
            clean_name = model['name'].replace('models/', '')
            print(f" -> Tên chính xác: {clean_name}")
else:
    print(f"\n[!] LỖI TỪ GOOGLE: {response.text}")