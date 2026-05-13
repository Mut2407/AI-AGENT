import json
from kafka import KafkaConsumer
from sqlalchemy.orm import Session
from database import SessionLocal
import models
from decimal import Decimal

def start_kafka_consumer():
    consumer = KafkaConsumer(
        'transaction-events', # Tên kênh lắng nghe
        bootstrap_servers=['localhost:9092'],
        auto_offset_reset='earliest',
        value_deserializer=lambda x: json.loads(x.decode('utf-8'))
    )

    for message in consumer:
        event = message.value
        event_type = event.get("event")
        data = event.get("data")
        
        db: Session = SessionLocal()
        try:
            if event_type == "TRANSACTION_CREATED":
                amount = data["amount"]
                user_id = data["user_id"]
                
                # 1. Nếu là chi tiêu -> Cập nhật Ngân sách
                if amount < 0:
                    category = data["category"]
                    # Tìm ngân sách khớp với user_id và category trong tháng này để cộng dồn
                    # ... logic query sqlalchemy ...
                    
                # 2. Nếu có jar_id -> Trừ tiền trong Hũ
                if amount < 0 and data.get("jar_id"):
                    jar = db.query(models.Jar).filter(models.Jar.id == data["jar_id"]).first()
                    if jar:
                        jar.balance -= Decimal(str(abs(amount)))
                        
                # 3. Nếu là thu nhập (amount > 0) -> Chia tiền vào các Hũ theo phần trăm
                elif amount > 0:
                    user_jars = db.query(models.Jar).filter(models.Jar.user_id == user_id).all()
                    for jar in user_jars:
                        if jar.percent > 0:
                            jar.balance += Decimal(str(amount)) * (jar.percent / Decimal('100'))
            
            db.commit()
        except Exception as e:
            print("Lỗi khi xử lý Kafka Event:", e)
            db.rollback()
        finally:
            db.close()

# Hàm này sẽ được gọi bằng một Thread riêng bên trong main.py khi bật Budget Service