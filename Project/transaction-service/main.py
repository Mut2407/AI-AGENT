from fastapi import FastAPI, Depends, HTTPException
from sqlalchemy.orm import Session
from aiokafka import AIOKafkaProducer # Import mới
import models, schemas, auth, uuid, json, os
from database import engine, get_db

models.Base.metadata.create_all(bind=engine)
app = FastAPI()

# Khởi tạo Kafka Producer
producer = None

@app.on_event("startup")
async def startup_event():
    global producer
    producer = AIOKafkaProducer(bootstrap_servers=os.getenv("KAFKA_BOOTSTRAP_SERVERS", "kafka:9092"))
    await producer.start()

@app.on_event("shutdown")
async def shutdown_event():
    await producer.stop()

@app.post("/api/expenses", response_model=schemas.TransactionResponse)
async def create_transaction(transaction: schemas.TransactionCreate, db: Session = Depends(get_db), current_user_id: int = Depends(auth.get_current_user_id)):
    new_txn = models.Transaction(
        id=str(uuid.uuid4()),
        **transaction.model_dump(),
        user_id=current_user_id
    )
    db.add(new_txn)
    db.commit()
    db.refresh(new_txn)

    # 🚀 Gửi sự kiện sang Kafka
    event = {"user_id": current_user_id, "amount": new_txn.amount, "name": new_txn.name}
    await producer.send_and_wait("transaction_events", json.dumps(event).encode('utf-8'))

    return new_txn