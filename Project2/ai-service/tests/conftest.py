# Đường dẫn: ai-service/tests/conftest.py

import sys
import os
from unittest.mock import MagicMock, patch
import types

# 1. Định vị thư mục gốc ai-service/ và cấu hình sys.path
ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

# 2. Tạo module ảo trên RAM để tránh lỗi sập Import chéo từ auth.py
mock_models = types.ModuleType("models")
mock_models.User = MagicMock()
sys.modules["models"] = mock_models

mock_database = types.ModuleType("database")
def mock_get_db():
    db = MagicMock()
    yield db
mock_database.get_db = mock_get_db
sys.modules["database"] = mock_database

# 3. Thiết lập các biến môi trường giả lập cho hệ thống AI
os.environ["GEMINI_API_KEY"] = "fake_gemini_key_for_testing_12345"
os.environ["JWT_SECRET_KEY"] = "expenseowl_super_secret_key_123"
os.environ["USER_SERVICE_URL"] = "http://user-service:8000"
os.environ["TXN_SERVICE_URL"] = "http://transaction-service:8000"

import pytest
from fastapi.testclient import TestClient

# 4. Nạp ứng dụng an toàn
from main import app
import auth

# Ghi đè hàm bảo mật xác thực Token để tránh lỗi 401
def override_get_current_user():
    return {"id": "1", "username": "ai_tester", "token": "mock_token"}

app.dependency_overrides[auth.get_current_user] = override_get_current_user

# 🔥 TUYỆT CHIÊU MOCK TOÀN DIỆN: Ghi đè hàm get_db của FastAPI App nếu có dùng
try:
    from database import get_db
    app.dependency_overrides[get_db] = mock_get_db
except:
    pass

@pytest.fixture(scope="session")
def client():
    with TestClient(app) as c:
        yield c

@pytest.fixture(autouse=True)
def mock_gemini_and_network():
    """Fixture tự động chặn toàn bộ các lệnh gọi ra bên ngoài (Gemini và HTTPX/Requests)"""
    mock_response = MagicMock()
    mock_response.text = '{"name": "Cà phê máy", "amount": 50000, "category": "Ăn uống", "date": "2026-05-18", "type": "expense"}'
    
    # Giả lập kết quả trả về của httpx / requests khi code của bạn gọi sang các service khác
    mock_net_res = MagicMock()
    mock_net_res.status_code = 200
    mock_net_res.json.return_value = {"status": "success", "username": "ai_tester"}
    
    with patch("google.genai.Client") as mock_client, \
         patch("httpx.post", return_value=mock_net_res), \
         patch("httpx.get", return_value=mock_net_res), \
         patch("requests.post", return_value=mock_net_res), \
         patch("requests.get", return_value=mock_net_res):
         
        mock_instance = MagicMock()
        mock_instance.models.generate_content.return_value = mock_response
        mock_client.return_value = mock_instance
        yield mock_instance