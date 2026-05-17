from fastapi import FastAPI
from routers import router as budget_router # Chỉ import router của budget thôi
from database import engine, Base
import models
import threading
from kafka_con import start_kafka_consumer
from prometheus_fastapi_instrumentator import Instrumentator
# 🚀 Thợ xây móng nhà Budget
Base.metadata.create_all(bind=engine)

app = FastAPI(title="Budget Service")
Instrumentator().instrument(app).expose(app)
@app.on_event("startup")
def startup_event():
    print("📡 Kafka Consumer đang lắng nghe giao dịch...")
    kafka_thread = threading.Thread(target=start_kafka_consumer, daemon=True)
    kafka_thread.start()

# Chỉ nối 1 phòng duy nhất
app.include_router(budget_router)