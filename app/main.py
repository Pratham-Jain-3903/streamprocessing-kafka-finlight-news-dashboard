from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse
from pydantic import BaseModel
import os
import json
from kafka import KafkaConsumer, KafkaAdminClient
from kafka.errors import KafkaError
from typing import List, Any

KAFKA_BOOTSTRAP = os.getenv('KAFKA_BOOTSTRAP_SERVERS', 'localhost:9092')

app = FastAPI(title="Mercury Dashboard API")

class MessageOut(BaseModel):
    topic: str
    partition: int
    offset: int
    key: Any = None
    value: Any

@app.get("/health")
async def health():
    return {"status": "ok"}

@app.get("/topics", response_model=List[str])
async def list_topics():
    """Return list of topics from the Kafka broker."""
    try:
        admin = KafkaAdminClient(bootstrap_servers=KAFKA_BOOTSTRAP, request_timeout_ms=2000)
        topics = admin.list_topics()
        admin.close()
        return sorted([t for t in topics if not t.startswith('__')])
    except KafkaError as e:
        raise HTTPException(status_code=503, detail=f"Kafka error: {e}")

@app.get("/topics/{topic}/messages", response_model=List[MessageOut])
async def tail_topic(topic: str, limit: int = 10):
    """Fetch the latest `limit` messages from a topic. This is a simple, non-efficient method suitable for small dev topics."""
    try:
        consumer = KafkaConsumer(bootstrap_servers=KAFKA_BOOTSTRAP,
                                 auto_offset_reset='latest',
                                 enable_auto_commit=False,
                                 consumer_timeout_ms=2000,
                                 value_deserializer=lambda x: try_json(x))
        partitions = consumer.partitions_for_topic(topic)
        if partitions is None:
            raise HTTPException(status_code=404, detail=f"Topic '{topic}' not found")

        # seek to end, then read backwards by offsets per partition
        tp_list = []
        for p in partitions:
            tp_list.append((topic, p))

        msgs = []
        # simple approach: read newest messages by creating a consumer and poll
        consumer.subscribe([topic])
        raw = consumer.poll(timeout_ms=2000, max_records=limit*10)
        for tp, records in raw.items():
            for r in records:
                msgs.append(MessageOut(topic=r.topic, partition=r.partition, offset=r.offset, key=try_json(r.key), value=r.value))
                if len(msgs) >= limit:
                    break
            if len(msgs) >= limit:
                break
        consumer.close()
        # return last N messages
        return msgs[-limit:]
    except KafkaError as e:
        raise HTTPException(status_code=503, detail=f"Kafka error: {e}")

# helper

def try_json(b):
    if b is None:
        return None
    try:
        return json.loads(b.decode('utf-8'))
    except Exception:
        try:
            return b.decode('utf-8')
        except Exception:
            return str(b)


@app.get("/dashboard", response_class=HTMLResponse)
async def dashboard():
    path = os.path.join(os.path.dirname(__file__), "dashboard.html")
    try:
        with open(path, "r", encoding="utf-8") as f:
            return HTMLResponse(content=f.read(), status_code=200)
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="dashboard.html not found")
