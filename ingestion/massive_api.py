#!/usr/bin/env python3
"""
Massive API (formerly Polygon.io) adapter for stock news ingestion.

API Documentation: https://massive.com/docs/rest/stocks/news
Endpoint: https://api.massive.com/v2/reference/news
"""

from __future__ import annotations

import logging
import os
from datetime import datetime, timedelta
from typing import Optional

import requests

LOGGER = logging.getLogger(__name__)

# Configuration from environment
API_BASE_URL = os.getenv("MASSIVE_API_URL", "https://api.massive.com/v2/reference/news")
API_KEY = os.getenv("MASSIVE_API_KEY", "rsoLbE3CQLL2pVXvbEpsjeqMBYtSFTp0")


def fetch_news(
    ticker: Optional[str] = None,
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    limit: int = 100,
    order: str = "asc",
    timeout: int = 30,
) -> dict:
    """Fetch news articles from Massive API.

    Args:
        ticker: Stock ticker symbol (e.g., 'AAPL', 'AMX')
        start_date: Start date for articles (inclusive)
        end_date: End date for articles (inclusive)
        limit: Max number of results per page (default 100, max 1000)
        order: Sort order ('asc' or 'desc')
        timeout: Request timeout in seconds

    Returns:
        API response dict with 'results', 'status', 'count', etc.

    Example response:
        {
            "status": "OK",
            "count": 2,
            "results": [
                {
                    "id": "...",
                    "publisher": {...},
                    "title": "...",
                    "author": "...",
                    "published_utc": "2024-01-15T10:30:00Z",
                    "article_url": "...",
                    "tickers": ["AAPL"],
                    "description": "...",
                    "keywords": [...]
                }
            ]
        }
    """
    params = {
        "apiKey": API_KEY,
        "limit": limit,
        "order": order,
        "sort": "published_utc",
    }

    if ticker:
        params["ticker"] = ticker.upper()

    if start_date:
        # Massive API expects ISO 8601 format: YYYY-MM-DDTHH:MM:SS.sssZ or YYYY-MM-DD
        params["published_utc.gte"] = start_date.strftime("%Y-%m-%d")

    if end_date:
        params["published_utc.lte"] = end_date.strftime("%Y-%m-%d")

    headers = {"accept": "application/json"}

    try:
        resp = requests.get(API_BASE_URL, params=params, headers=headers, timeout=timeout)
        resp.raise_for_status()
        return resp.json()
    except requests.exceptions.RequestException as e:
        LOGGER.error("Massive API request failed: %s", e)
        raise


def probe_articles(
    ticker: Optional[str] = None,
    date: Optional[datetime] = None,
    timeout: int = 10,
) -> bool:
    """Check if articles exist for a given ticker and date.

    Args:
        ticker: Stock ticker symbol
        date: Single calendar date to probe
        timeout: Request timeout in seconds

    Returns:
        True if articles exist, False otherwise
    """
    try:
        start = date if date else datetime.utcnow() - timedelta(days=1)
        end = start + timedelta(days=1)
        result = fetch_news(ticker=ticker, start_date=start, end_date=end, limit=1, timeout=timeout)
        count = result.get("count", 0)
        results = result.get("results", [])
        return count > 0 and len(results) > 0
    except Exception as e:
        LOGGER.warning("Probe failed for ticker=%s date=%s: %s", ticker, date, e)
        return False


def normalize_article(raw: dict) -> dict:
    """Normalize a Massive API article to internal schema.

    Args:
        raw: Raw article dict from Massive API

    Returns:
        Normalized dict with standard fields:
            {
                "id": str,
                "title": str,
                "summary": str,
                "url": str,
                "source": str,
                "published_at": ISO timestamp,
                "tickers": [str],
                "author": str,
                "keywords": [str]
            }
    """
    return {
        "id": raw.get("id"),
        "title": raw.get("title", ""),
        "summary": raw.get("description", ""),
        "url": raw.get("article_url", ""),
        "source": raw.get("publisher", {}).get("name", "massive.com"),
        "published_at": raw.get("published_utc"),
        "tickers": raw.get("tickers", []),
        "author": raw.get("author", ""),
        "keywords": raw.get("keywords", []),
    }


if __name__ == "__main__":
    # Quick test
    logging.basicConfig(level=logging.INFO)
    print("Testing Massive API with ticker=AAPL, last 7 days...")
    end = datetime.utcnow()
    start = end - timedelta(days=7)
    result = fetch_news(ticker="AAPL", start_date=start, end_date=end, limit=5)
    print(f"Status: {result.get('status')}, Count: {result.get('count')}")
    for article in result.get("results", [])[:3]:
        print(f"  - {article.get('title')} ({article.get('published_utc')})")
