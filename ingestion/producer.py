"""
   Fetches new articles every X seconds
   Sends each article as JSON event to Kafka topic `news_raw`
"""


import logging
from finlight_api import NewsFetcher
import requests
import time
import os
from kafka import KafkaProducer
import json
from logger import logger
from datetime import datetime, timedelta
from dotenv import load_dotenv
from zoneinfo import ZoneInfo

load_dotenv()

#-----SAVE TO logs/producer.log -----
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class TopicConfig:
   KAFKA_BOOTSTRAP = os.getenv("KAFKA_BOOTSTRAP", "localhost:9092")
   def __init__(self, topic_name, key_word: str = "", timezone: str = "UTC"):
      self.topic_name = topic_name
      self.key_word = key_word
      self.sources = []
      self.exclude_sources = []
      self.countries = []
      self.language = "en"
      self.timezone = timezone  # default timezone


class NewsPublisher:

   _state_files_dir = "states"
   class _AllSourcesDescriptor:
       def __get__(self, instance, owner):
            if not hasattr(owner, "_cached_all_sources"):
               try:
                   # prefer instance.topic.language if available, otherwise default to "en"
                  lang = "en"
                  if instance is not None and getattr(instance, "topic", None):
                     lang = getattr(instance.topic, "language", "en")
                  owner._cached_all_sources = owner._get_all_news_sources(language=lang)
               except Exception as e:
                  logger.warning(f"Unable to fetch news sources: {e}")
                  owner._cached_all_sources = []
            return owner._cached_all_sources

   _all_sources = _AllSourcesDescriptor()
    
   def __init__(self, topic : TopicConfig):

      self.producer = KafkaProducer(
            bootstrap_servers=topic.KAFKA_BOOTSTRAP,
            value_serializer=lambda v: json.dumps(v).encode('utf-8'),
            key_serializer=lambda k: k.encode('utf-8'),
            retries=5
        )
      self.topic = topic
      self.state_file = f"{self._state_files_dir}/{topic.topic_name}_state.json"
      
      # ensure state dir exists
      os.makedirs(self._state_files_dir, exist_ok=True)

      # load state if present, else initialize new state
      if os.path.exists(self.state_file):      
         self.article_ids_published = set()
         self.load_state()
      else:
         self.last_published_at = None
         self.articles_count = 0
         self.article_ids_published = set()
         # persist an initial empty state so subsequent runs can load it
         try:
            with open(self.state_file, "w") as f:
               json.dump({
               "last_published_at": self.last_published_at,
               "articles_count": self.articles_count,
               "article_ids_published": []
               }, f)
         except Exception as e:
            logger.warning(f"Unable to create initial state file {self.state_file}: {e}")

   def load_last_published_at(self):
      """
      Load last published at timestamp from state file
      """
      if not os.path.exists(self.state_file):
         return None
      try:
         with open(self.state_file, "r") as f:
            state = json.load(f)
            return state.get("last_published_at", None)
      except Exception as e:
         logger.warning(f"Unable to load state file {self.state_file}: {e}")
         return None
      
   def load_state(self):
      """
      Load entire state from state file
      """
      if not os.path.exists(self.state_file):
         return
      try:
         with open(self.state_file, "r") as f:
            state = json.load(f)
            self.last_published_at = state.get("last_published_at", None)
            self.articles_count = state.get("articles_count", 0)
            self.article_ids_published = set(state.get("article_ids_published", []))
      except Exception as e:
         logger.warning(f"Unable to load state file {self.state_file}: {e}")

   @classmethod
   def _get_all_news_sources(cls, language="en") -> list:
      """
      Fetch all news sources from Finlight API
      resp structire:   
           {
                    "domain": "abcnews.go.com",
                    "isDefaultSource": true
                },
      return list of source domains
      """
      list_sources =  [source.get('domain') for source in NewsFetcher.fetch_news_sources_get(language=language)]
      return list_sources

   def fetch_news(self, from_date=None, to_date=None, page_count=1):
      if from_date is None and self.last_published_at is not None:
         # determine timezone from topic (fallback to publisher default)
         tz_name = getattr(self.topic, "timezone", "UTC")
         tz_map = {"IST": "Asia/Kolkata", "UTC": "UTC"}
         tz_zone = ZoneInfo(tz_map.get(tz_name, tz_name))

         if from_date is None and self.last_published_at is not None:
            from_date = self.last_published_at
         else:
            from_date = (datetime.now(tz_zone) - timedelta(days=1)).strftime("%Y-%m-%dT%H:%M")

         if to_date is None:
            to_date = datetime.now(tz_zone).strftime("%Y-%m-%dT%H:%M")


      for source in self.topic.exclude_sources:
         if source not in self._all_sources:
            logger.warning(f"Excluding source {source} which is not in available sources list")
            self.topic.exclude_sources.remove(source)

      for source in self.topic.sources:
         if source not in self._all_sources:
            logger.warning(f"Source {source} is not in available sources list")

      news_articles = NewsFetcher.fetch_news_post(
            query=self.topic.key_word,
            sources=self.topic.sources,
            countries=self.topic.countries,
            language=self.topic.language,
            exclude_sources=self.topic.exclude_sources,
            from_date= from_date,
            to_date= to_date,
            page_count=page_count
        )
      # give each article a unique ID if not present
      for article in news_articles:
         if "id" not in article or not article["id"]:
            article["id"] = article.get("link", f"no-id-{hash(article.get('title',''))}")
      return news_articles
   
   def publish_articles(self, articles: list):
      for article in articles:
         try:
            self.producer.send(self.topic.topic_name, key=article.get("id", ""), value=article)
            self.article_ids_published.add(article.get("id", ""))
            self.articles_count += 1
         except Exception as e:
            logger.error(f"Failed to publish article {article.get('id', '')}: {e}")
      self.producer.flush()
      logger.info(f"Published {self.articles_count} articles to topic {self.topic.topic_name}")

   def stateful_publish(self, from_date=None, to_date=None, page_count=1):
      articles = self.fetch_news(from_date=from_date, to_date=to_date, page_count=page_count)
      # check if it has been published already
      articles = [article for article in articles if article.get("id", "") not in self.article_ids_published]
      if articles:
         self.publish_articles(articles)
         # update last published at
         latest_pub = max(article.get("publishDate", "") for article in articles)
         if latest_pub:
            self.last_published_at = latest_pub
            # save state
            self.save_state()
      else:
         logger.info("No new articles fetched.")

   def save_state(self):
      state = {
         "last_published_at": self.last_published_at,
         "articles_count": self.articles_count,
         "article_ids_published": list(self.article_ids_published)
      }
      try:
         with open(self.state_file, "w") as f:
            json.dump(state, f)
         logger.info(f"Saved state to {self.state_file}")
      except Exception as e:
         logger.error(f"Failed to save state to {self.state_file}: {e}")


if __name__ == "__main__":
   # testing topic config for nvidia news
   nvidia = TopicConfig("nvidia-news")
   nvidia.sources = ["www.yahoo.com", "abcnews.go.com"]
   nvidia.countries = ["IN", "US"]
   nvidia.key_word = "nvidia"
   nvidia.language = "en"
   nvidia.timezone = "Asia/Kolkata"
   nvidia.exclude_sources = ["www.aljazeera.com"]

   # lenskart news
   lenskart = TopicConfig("lenskart-news")
   # lenskart.sources = ["www.yahoo.com", "abcnews.go.com", "cute_pink_glasses_girl.com"]
   lenskart.countries = ["IN", "US"]
   lenskart.key_word = "lenskart"
   lenskart.language = "en"
   lenskart.timezone = "Asia/Kolkata"
   lenskart.exclude_sources = ["www.aljazeera.com"]

   publisher = NewsPublisher(lenskart)
   publisher.stateful_publish()



