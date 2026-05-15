import json
from kafka import KafkaConsumer
from sqlalchemy.orm import Session
from database import SessionLocal
import models
from decimal import Decimal
from datetime import datetime
import os


def start_kafka_consumer():
    consumer = KafkaConsumer(
        'transaction-events', # Tên kênh lắng nghe
        bootstrap_servers=[os.getenv("KAFKA_BROKER", "kafka:9092")],
        auto_offset_reset='earliest',
        value_deserializer=lambda x: json.loads(x.decode('utf-8'))
    )

    print("📡 Kafka Consumer đang lắng nghe giao dịch...")

    for message in consumer:
        event = message.value
        event_type = event.get("event")
        data = event.get("data")
        
        db: Session = SessionLocal()
        try:
            amount = Decimal(str(data["amount"]))
            user_id = data["user_id"]
            category = data.get("category")
            trans_date_str = data.get("transaction_date")
            # ==========================================
            # TRƯỜNG HỢP 1: TẠO MỚI GIAO DỊCH
            # ==========================================
            if event_type == "TRANSACTION_CREATED":
                # 1. Nếu là chi tiêu -> Cập nhật Ngân sách
                if amount < 0:
                    if category and trans_date_str:
                        trans_date = datetime.strptime(trans_date_str[:10], "%Y-%m-%d").date()
                        budget = db.query(models.Budget).filter(
                            models.Budget.user_id == user_id,
                            models.Budget.category == category,
                            models.Budget.start_date <= trans_date,
                            models.Budget.end_date >= trans_date
                        ).first()
                        
                        if budget:
                            budget.spent_amount += abs(amount)
                    
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

            # ==========================================
            # TRƯỜNG HỢP 2: XÓA GIAO DỊCH (HOÀN TÁC)
            # ==========================================
            elif event_type == "TRANSACTION_DELETED":
                if amount < 0:
                    # Giảm chi tiêu trong Ngân sách
                    if category and trans_date_str:
                        trans_date = datetime.strptime(trans_date_str[:10], "%Y-%m-%d").date()
                        budget = db.query(models.Budget).filter(
                            models.Budget.user_id == user_id,
                            models.Budget.category == category,
                            models.Budget.start_date <= trans_date,
                            models.Budget.end_date >= trans_date
                        ).first()
                        
                        if budget:
                            budget.spent_amount -= abs(amount)
                            # Tránh trường hợp trừ lố về số âm
                            if budget.spent_amount < 0: 
                                budget.spent_amount = 0
            
            db.commit()
        except Exception as e:
            print("Lỗi khi xử lý Kafka Event:", e)
            db.rollback()
        finally:
            db.close()

# Hàm này sẽ được gọi bằng một Thread riêng bên trong main.py khi bật Budget Service