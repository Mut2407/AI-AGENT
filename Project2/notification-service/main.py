import json
from kafka import KafkaConsumer
# Giả định em có hàm send_email sử dụng thư viện smtplib
# from email_sender import send_email

def start_listening():
    consumer = KafkaConsumer(
        'transaction-events',
        bootstrap_servers=['kafka:9092'],
        value_deserializer=lambda x: json.loads(x.decode('utf-8'))
    )
    print("Notification Service đang lắng nghe sự kiện...")
    for message in consumer:
        event = message.value
        event_type = event.get("event")
        data = event.get("data")
        
        if event_type == "BUDGET_EXCEEDED":
            # Logic gửi email cảnh báo người dùng khi tiêu lố ngân sách
            print(f"Gửi email cảnh báo: Ngân sách {data['category']} đã vượt mức!")
            # send_email(to=data['email'], subject="Cảnh báo", body="Bạn đã vượt ngân sách...")

if __name__ == "__main__":
    start_listening()