from kafka import KafkaConsumer
import json

consumer = KafkaConsumer(
    'news_raw',
    bootstrap_servers=['localhost:9092'],
    auto_offset_reset='latest',
    enable_auto_commit=True,
    value_deserializer=lambda x: json.loads(x.decode('utf-8'))
)

print("Listening for news...")

for msg in consumer:
    print(msg.value)
