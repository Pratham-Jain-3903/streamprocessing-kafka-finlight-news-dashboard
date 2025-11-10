# streamprocessing-kafka-finlight-news-dashboard

📡 News API
   │
   ▼
🧵 Ingestion Service (Python)
   ├── Fetches new articles every X seconds
   ├── Sends each article as JSON event to Kafka topic `news_raw`
   │
   ▼
🐃 Apache Kafka / 🐼 Redpanda
   ├── Topics: news_raw, news_clean, news_enriched
   │
   ▼
🔥 Stream Processor
   ├── Option A: Apache Flink / Spark Structured Streaming
   ├── Option B: Faust / Kafka Streams (Python)
   ├── Cleans data, deduplicates, adds derived fields
   │
   ▼
🪣 Sink / Data Lake
   ├── Writes Parquet to S3 / MinIO
   ├── Or loads to Postgres / DuckDB for analytics
   │
   ▼
📊 Dashboard Layer
   ├── Superset / Grafana / Streamlit
   └── Displays live counts, trends, top sources
