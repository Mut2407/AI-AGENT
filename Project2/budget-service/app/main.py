from fastapi import FastAPI
from routers import router as budget_router # Chỉ import router của budget thôi
from database import engine, Base
import models

# 🚀 Thợ xây móng nhà Budget
Base.metadata.create_all(bind=engine)

app = FastAPI(title="Budget Service")

# Chỉ nối 1 phòng duy nhất
app.include_router(budget_router)