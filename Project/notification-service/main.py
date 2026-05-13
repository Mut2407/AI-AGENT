import asyncio
import json
import os
from aiokafka import AIOKafkaConsumer

KAFKA_BOOTSTRAP_SERVERS = os.getenv("KAFKA_BOOTSTRAP_SERVERS", "kafka:9092")
TOPIC = "transaction_events"

async def consume():
    consumer = AIOKafkaConsumer(
        TOPIC,
        bootstrap_servers=KAFKA_BOOTSTRAP_SERVERS,
        group_id="notification_group"
    )
    await consumer.start()
    try:
        print(f"📡 Notification Service đang lắng nghe tại {TOPIC}...")
        async for msg in consumer:
            data = json.loads(msg.value.decode('utf-8'))
            print(f"🔔 THÔNG BÁO: User {data['user_id']} vừa chi {data['amount']:,} VND cho '{data['name']}'")
    finally:
        await consumer.stop()

if __name__ == "__main__":
    asyncio.run(consume())