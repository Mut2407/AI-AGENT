import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
# ------------------------------------
os.environ["DATABASE_URL"] = "sqlite:///./test_user_service.db"
os.environ["JWT_SECRET_KEY"] = "super_secret_test_key_123"
# ------------------------------------
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from main import app
from database import Base, get_db

# Cấu hình Database ảo SQLite In-memory
SQLALCHEMY_DATABASE_URL = "sqlite:///./test_user_service.db"
engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False})
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Tạo các bảng ảo
Base.metadata.drop_all(bind=engine)
Base.metadata.create_all(bind=engine)

def override_get_db():
    try:
        db = TestingSessionLocal()
        yield db
    finally:
        db.close()

# Ghi đè dependency database của FastAPI
app.dependency_overrides[get_db] = override_get_db

@pytest.fixture(scope="session")
def client():
    with TestClient(app) as c:
        yield c

@pytest.fixture(scope="session")
def test_user_token(client):
    """Fixture tạo sẵn 1 user và trả về token để dùng cho các test cần đăng nhập"""
    user_data = {
        "username": "global_tester",
        "password": "securepassword123",
        "email": "global@example.com",
        "full_name": "Global Tester",
        "gender": "Nam",
        "dob": "2000-01-01"
    }
    # Tạo user
    client.post("/api/auth/register", json=user_data)
    # Đăng nhập lấy token
    response = client.post("/api/auth/login", data={"username": "global_tester", "password": "securepassword123"})
    # Bổ sung kiểm tra lỗi
    if response.status_code != 200:
        raise ValueError(f"Không thể lấy Token. Lỗi API: {response.text}")
    return response.json()["access_token"]

@pytest.fixture(scope="session", autouse=True)
def cleanup_test_db():
    """Fixture tự động chạy để dọn dẹp database ảo sau khi test xong"""
    yield
    db_file = "./test_user_service.db"
    if os.path.exists(db_file):
        # Đóng engine trước khi xóa 
        engine.dispose() 
        try:
            os.remove(db_file)
            print(f"\n[CLEANUP] Đã dọn dẹp và xóa file: {db_file}")
        except PermissionError:
            # Bỏ qua lỗi 
            print(f"\n[CLEANUP] Bỏ qua xóa file do Windows đang lock. File sẽ được làm sạch tự động ở lần chạy tới.")