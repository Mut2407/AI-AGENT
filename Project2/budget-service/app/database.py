from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
import os

# Lấy đường dẫn Database từ Docker Compose (file .env)
SQLALCHEMY_DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://admin:secret@postgres_db:5432/expenseowl_budget_db")

# Khởi tạo động cơ kết nối
engine = create_engine(SQLALCHEMY_DATABASE_URL)

# Tạo xưởng đúc Session
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# 🚀 ĐÂY CHÍNH LÀ CÁI "BASE" MÀ MODELS.PY ĐANG TÌM KIẾM NÀY!
Base = declarative_base()

# Hàm tạo phiên làm việc với Database (Dùng cho Dependency Injection trong FastAPI)
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()