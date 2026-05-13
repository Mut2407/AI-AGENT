import json
from kafka import KafkaProducer

# Khởi tạo Producer kết nối đến Kafka Container
producer = KafkaProducer(
    bootstrap_servers=['localhost:9092'],
    value_serializer=lambda v: json.dumps(v).encode('utf-8')
)

def send_transaction_event(event_type: str, data: dict):
    # event_type có thể là "TRANSACTION_CREATED" hoặc "TRANSACTION_DELETED"
    message = {"event": event_type, "data": data}
    producer.send('transaction-events', message)
    producer.flush()