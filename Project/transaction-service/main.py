from fastapi import FastAPI
from aiokafka import AIOKafkaProducer
import models, schemas, auth, uuid, json, os
from database import engine
from routers import router as expenses_router, recurring_router

models.Base.metadata.create_all(bind=engine)
app = FastAPI()

# Khởi tạo Kafka Producer
producer = None


@app.on_event("startup")
async def startup_event():
    global producer
    producer = AIOKafkaProducer(bootstrap_servers=os.getenv("KAFKA_BOOTSTRAP_SERVERS", "kafka:9092"))
    try:
        await producer.start()
    except Exception:
        # Nếu Kafka chưa sẵn sàng, khởi động service nhưng log lỗi.
        producer = None


@app.on_event("shutdown")
async def shutdown_event():
    global producer
    if producer:
        await producer.stop()


app.include_router(expenses_router)
app.include_router(recurring_router)

@app.get("/health")
async def health():
    return {"status": "ok"}