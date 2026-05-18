import sys
import os
from unittest.mock import patch

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
os.environ["DATABASE_URL"] = "sqlite:///./test_transaction_service.db"
os.environ["JWT_SECRET_KEY"] = "super_secret_test_key_123"

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from main import app
from database import Base, get_db
import auth

# 1. Cấu hình DB ảo
engine = create_engine(os.environ["DATABASE_URL"], connect_args={"check_same_thread": False})
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base.metadata.drop_all(bind=engine)
Base.metadata.create_all(bind=engine)

def override_get_db():
    try:
        db = TestingSessionLocal()
        yield db
    finally:
        db.close()

# 2. Giả mạo (Mock) Hàm xác thực Token của User
# Trả về luôn 1 user ảo để không cần phải gọi sang user-service
def override_get_current_user():
    return {"id": 1, "username": "global_tester"}

app.dependency_overrides[get_db] = override_get_db
app.dependency_overrides[auth.get_current_user] = override_get_current_user

@pytest.fixture(scope="session")
def client():
    with TestClient(app) as c:
        yield c

# 3. Giả mạo Kafka Producer để lúc tạo giao dịch không bị lỗi sập mạng
@pytest.fixture(autouse=True)
def mock_kafka_producer():
    # Tự động chặn hàm gửi message đi Kafka trong toàn bộ quá trình test
    with patch("kafka_pro.send_transaction_event") as mock_send:
        yield mock_send