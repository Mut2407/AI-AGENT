from fastapi import FastAPI
from routers import router, recurring_router
from prometheus_fastapi_instrumentator import Instrumentator
# Thêm 2 dòng import này vào
from database import engine, Base
import models 

# 🚀 GỌI THỢ XÂY: Câu lệnh này sẽ tự động quét file models.py và tạo các bảng còn thiếu
Base.metadata.create_all(bind=engine)

# Dòng này chính là "cô chủ nhà" mà Uvicorn đang tìm kiếm!
app = FastAPI(title="Transaction Service")
Instrumentator().instrument(app).expose(app)
# Bắt đầu mở cửa nối các phòng vào sảnh chính
app.include_router(router)
app.include_router(recurring_router)