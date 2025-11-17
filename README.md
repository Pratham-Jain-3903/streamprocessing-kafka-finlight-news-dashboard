# streamprocessing-kafka-finlight-news-dashboard

# repo structure
news-stream-pipeline/
├── ingestion/
│   ├── producer.py          # polls API → sends to Kafka
│   └── config.yaml
├── stream_processor/
│   ├── app.py               # Faust or Flink job
│   ├── transformations.py
│   └── requirements.txt
├── sinks/
│   ├── sink_to_duckdb.py
│   ├── sink_to_s3.py
│   └── schema.sql
├── docker-compose.yml       # kafka, zookeeper, redpanda-console, duckdb container
├── notebooks/
│   └── analytics.ipynb
└── README.md

# News Stream Processing Pipeline
This repository contains a complete pipeline for ingesting, processing, and visualizing news articles using Apache Kafka and stream processing frameworks. The pipeline fetches news articles from a public API, processes them in real-time, and stores them for analysis and visualization.

📡 News API
   │
   ▼
🧵 Ingestion Service (Python)
   ├── Fetches new articles every X seconds
   ├── Sends each article as JSON event to Kafka topic `news_raw`
   │
   ▼
🐃 Apache Kafka 
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


