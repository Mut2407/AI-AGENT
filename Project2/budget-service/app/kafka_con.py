import json
import time
from kafka import KafkaConsumer
from kafka.errors import NoBrokersAvailable
from sqlalchemy.orm import Session
from sqlalchemy import func 
from database import SessionLocal
import models
from decimal import Decimal
from datetime import datetime
import os


def start_kafka_consumer():
    print("📡 Đang kết nối tới Kafka Broker...", flush=True) # Ép nhả log
    consumer = None
    
    while consumer is None:
        try:
            consumer = KafkaConsumer(
                'transaction-events',
                bootstrap_servers=[os.getenv("KAFKA_BROKER", "kafka:9092")],
                auto_offset_reset='earliest',
                value_deserializer=lambda x: json.loads(x.decode('utf-8'))
            )
            print("✅ Đã kết nối thành công tới Kafka Broker!", flush=True)
        except NoBrokersAvailable:
            print("⏳ Kafka chưa sẵn sàng, đang thử lại sau 3 giây...", flush=True)
            time.sleep(3)
        except Exception as e:
            print(f"❌ Lỗi kết nối Kafka: {e}", flush=True)
            time.sleep(3)

    print("📡 Kafka Consumer đang lắng nghe giao dịch...", flush=True)

    for message in consumer:
        try:
            event = message.value
            event_type = event.get("event")
            data = event.get("data")
            
            db: Session = SessionLocal()
            try:
                amount = Decimal(str(data.get("amount", 0)))
                user_id = data.get("user_id")
                category = data.get("category", "")
                trans_date_str = data.get("transaction_date")

                if not trans_date_str:
                    trans_date = datetime.now().date()
                else:
                    trans_date = datetime.strptime(trans_date_str[:10], "%Y-%m-%d").date()

                # 1. TÌM NGÂN SÁCH 
                budget = None
                if category:
                    budget = db.query(models.Budget).filter(
                        models.Budget.user_id == user_id,
                        func.lower(models.Budget.category) == str(category).lower(),
                        models.Budget.start_date <= trans_date,
                        models.Budget.end_date >= trans_date
                    ).first()

                is_expense = (budget is not None) or (amount < 0)

                # ==========================================
                # XỬ LÝ GIAO DỊCH
                # ==========================================
                if event_type == "TRANSACTION_CREATED":
                    if is_expense:
                        if budget:
                            budget.spent_amount += abs(amount)
                        if data.get("jar_id"):
                            jar = db.query(models.Jar).filter(models.Jar.id == data["jar_id"]).first()
                            if jar: jar.balance -= abs(amount)
                    else:
                        user_jars = db.query(models.Jar).filter(models.Jar.user_id == user_id).all()
                        for jar in user_jars:
                            if jar.percent > 0: jar.balance += abs(amount) * (jar.percent / Decimal('100'))

                elif event_type == "TRANSACTION_DELETED":
                    if is_expense:
                        if budget:
                            budget.spent_amount -= abs(amount)
                            if budget.spent_amount < 0: budget.spent_amount = 0
                        if data.get("jar_id"):
                            jar = db.query(models.Jar).filter(models.Jar.id == data["jar_id"]).first()
                            if jar: jar.balance += abs(amount)
                    else:
                        user_jars = db.query(models.Jar).filter(models.Jar.user_id == user_id).all()
                        for jar in user_jars:
                            if jar.percent > 0:
                                jar.balance -= abs(amount) * (jar.percent / Decimal('100'))
                                if jar.balance < 0: jar.balance = 0

                db.commit()
                print(f"✅ Xử lý xong: {event_type} | Danh mục: {category} | Tiền: {amount}", flush=True)
            except Exception as e:
                print(f"❌ Lỗi Logic: {e}", flush=True)
                db.rollback()
            finally:
                db.close()
        except Exception as outer_e:
            print(f"❌ Bỏ qua event lỗi: {outer_e}", flush=True)

# Hàm này sẽ được gọi bằng một Thread riêng bên trong main.py khi bật Budget Service