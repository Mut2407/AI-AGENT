import json
import os
from kafka import KafkaProducer

# Lấy địa chỉ Kafka từ file docker-compose (biến môi trường KAFKA_BROKER)
KAFKA_BROKER = os.getenv("KAFKA_BROKER", "kafka:9092")

try:
    # Khởi tạo máy phát sóng Kafka
    producer = KafkaProducer(
        bootstrap_servers=[KAFKA_BROKER],
        value_serializer=lambda v: json.dumps(v).encode('utf-8'),
        api_version=(0, 10, 1) # Giúp tương thích tốt hơn với môi trường Docker
    )
    print("✅ Đã kết nối thành công tới Kafka Broker!")
except Exception as e:
    print(f"❌ Lỗi kết nối Kafka: {e}")
    producer = None

def send_transaction_event(event_type: str, data: dict):
    """
    Hàm này dùng để bắn tin nhắn lên topic 'transaction_events'
    """
    if producer is None:
        print("⚠️ Kafka Producer chưa sẵn sàng, bỏ qua gửi tin nhắn.")
        return

    payload = {
        "event_type": event_type,
        "data": data
    }
    
    try:
        # Bắn tin nhắn vào kênh "transaction_events"
        producer.send("transaction_events", value=payload)
        producer.flush() # Đảm bảo tin nhắn được đẩy đi ngay lập tức
        print(f"🚀 Bắn Kafka event [{event_type}] thành công!")
    except Exception as e:
        print(f"❌ Bắn Kafka thất bại: {e}")