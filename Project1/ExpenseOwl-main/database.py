import os
import urllib.parse  # <--- THÊM DÒNG NÀY ĐỂ MÃ HÓA MẬT KHẨU
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from dotenv import load_dotenv

load_dotenv(override=True)

DB_USER = os.getenv("DB_USER", "postgres").strip()
# Lấy mật khẩu và MÃ HÓA nó để ký tự @ không làm hỏng chuỗi URL
raw_password = os.getenv("DB_PASSWORD", "123").strip()
DB_PASSWORD = urllib.parse.quote_plus(raw_password)

DB_HOST = os.getenv("DB_HOST", "127.0.0.1").strip()
DB_PORT = os.getenv("DB_PORT", "5433").strip()
DB_NAME = os.getenv("DB_NAME", "expense_db").strip()

# Chuỗi kết nối
SQLALCHEMY_DATABASE_URL = f"postgresql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"

print(f"====> CHUỖI KẾT NỐI ĐÃ MÃ HÓA: {SQLALCHEMY_DATABASE_URL}")

engine = create_engine(SQLALCHEMY_DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()