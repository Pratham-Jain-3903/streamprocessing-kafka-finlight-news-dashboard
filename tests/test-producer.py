import os
import time
import json
import logging
from datetime import datetime, timedelta

import requests
from kafka import KafkaProducer
from dotenv import load_dotenv

load_dotenv()

# --- Configuration ---
api_key = os.getenv(
    "FINLIGHT_API_KEY",
    "sk_621d88dfcc31a1d3efa89a2873d394563f53bfd6fe1c7aec2ffd22e45d7b1d44",
)
FINLIGHT_API_KEY = api_key
FINLIGHT_API_URL = "https://api.finlight.me/v2/articles"  # from docs :contentReference[oaicite:0]{index=0}

KAFKA_BOOTSTRAP = os.getenv("KAFKA_BOOTSTRAP", "localhost:9092")
RAW_NEWS_TOPIC = os.getenv("RAW_NEWS_TOPIC", "news_raw")

POLL_INTERVAL_SECONDS = int(
    os.getenv("POLL_INTERVAL_SECONDS", "300")
)  # e.g. poll every 5 minutes
PAGE_SIZE = int(os.getenv("PAGE_SIZE", "50"))

# State persistence (very simple file-based for demo)
STATE_FILE = os.getenv("STATE_FILE", "poller_state.json")


# --- Setup logging ---
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


# --- Kafka Producer Setup ---
producer = KafkaProducer(
    bootstrap_servers=KAFKA_BOOTSTRAP,
    value_serializer=lambda v: json.dumps(v).encode("utf-8"),
    key_serializer=lambda k: k.encode("utf-8"),
    retries=5,
)


# --- State Handling ---
def load_state():
    """
    Load the last poll time and seen article IDs
    """
    if not os.path.exists(STATE_FILE):
        return {"last_poll": None, "seen_ids": []}
    with open(STATE_FILE, "r") as f:
        return json.load(f)


def save_state(state):
    with open(STATE_FILE, "w") as f:
        json.dump(state, f)


# --- Polling / Fetching Logic ---
def fetch_articles(from_time: str | None = None):
    """
    Call Finlight API with pagination to fetch new articles since `from_time`
    """
    all_articles = []
    page = 1

    while True:
        body = {
            "query": os.getenv("FINLIGHT_QUERY", ""),  # your theme-based query
            "from": from_time,
            "pageSize": PAGE_SIZE,
            "page": page,
            "orderBy": "publishDate",
            "order": "ASC",
            "language": "en",
        }

        headers = {
            "X-API-KEY": FINLIGHT_API_KEY,
            "Content-Type": "application/json",
        }

        resp = requests.post(FINLIGHT_API_URL, headers=headers, json=body)
        if resp.status_code != 200:
            logger.error("Finlight API error: %s %s", resp.status_code, resp.text)
            break

        data = resp.json()
        articles = data.get("articles", [])
        if not articles:
            break

        all_articles.extend(articles)
        logger.info("Fetched %d articles on page %d", len(articles), page)

        # If fewer articles than pageSize, no more pages
        if len(articles) < PAGE_SIZE:
            break

        page += 1
        time.sleep(1)  # polite rate-limiting for paging

    return all_articles


# --- Normalization Logic ---
def normalize_article(raw):
    """
    Convert raw article from Finlight to a normalized internal format
    """
    return {
        "id": raw.get("link"),  # fallback if no ID
        "title": raw.get("title"),
        "summary": raw.get("summary"),
        "publish_date": raw.get("publishDate"),
        "source": raw.get("link"),
        "sentiment": raw.get("link"),
        "created_at": raw.get("createdAt"),
    }


# --- Main Poller Loop ---
def run_poller():
    state = load_state()
    last_poll = state.get("last_poll")
    seen_ids = set(state.get("seen_ids", []))

    if last_poll:
        from_time = last_poll
    else:
        # If no last poll time, go a default window back, e.g. 1 day
        from_time = (datetime.utcnow() - timedelta(days=1)).isoformat() + "Z"

    logger.info("Starting poller. From time: %s", from_time)

    articles = fetch_articles(from_time)

    max_poll_time = last_poll  # to update

    for raw in articles:
        norm = normalize_article(raw)
        art_id = norm["id"]
        if art_id in seen_ids:
            logger.debug("Skipping seen article: %s", art_id)
            continue

        # Send to Kafka
        try:
            producer.send(RAW_NEWS_TOPIC, key=art_id, value=norm)
            producer.flush()
            logger.info("Published article to Kafka: %s", art_id)
        except Exception as e:
            logger.error("Error sending to Kafka: %s", e)
            # optionally buffer / retry logic

        seen_ids.add(art_id)

        pub = raw.get("publishDate")
        if pub:
            # track newest publish date seen
            if (max_poll_time is None) or (pub > max_poll_time):
                max_poll_time = pub

    # Update state
    state["seen_ids"] = list(seen_ids)
    if max_poll_time:
        state["last_poll"] = max_poll_time
    save_state(state)
    logger.info(
        "Poll run complete. Saved state: last_poll = %s, total_seen = %d",
        state["last_poll"],
        len(seen_ids),
    )


if __name__ == "__main__":
    while True:
        try:
            run_poller()
        except Exception as e:
            logger.exception("Poller crashed: %s", e)
        time.sleep(POLL_INTERVAL_SECONDS)
