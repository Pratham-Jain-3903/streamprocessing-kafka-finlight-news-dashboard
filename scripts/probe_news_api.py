#!/usr/bin/env python3
"""
Multi-provider news API probe script.

Supports:
- Finlight API (finlight.me)
- Massive API (massive.com / formerly Polygon.io)

Finds the earliest date with articles for a given ticker/query in a date range.
"""

from __future__ import annotations

import argparse
import json
import logging
import os
import sys
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional

# Add parent dir to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

import requests

LOGGER = logging.getLogger("news_probe")
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")


class FinlightProber:
    """Finlight API probe implementation."""

    def __init__(self, api_key: str):
        self.api_url = "https://api.finlight.me/v2/articles"
        self.api_key = api_key

    def probe_day(
        self, date: datetime, query: Optional[str] = None, sources: Optional[list[str]] = None, timeout: int = 10
    ) -> bool:
        """Return True if articles exist for the given date."""
        from_ts = date.strftime("%Y-%m-%dT00:00")
        to_ts = (date + timedelta(days=1)).strftime("%Y-%m-%dT00:00")
        payload = {"from": from_ts, "to": to_ts, "pageSize": 1, "page": 1}
        if query:
            payload["query"] = query
        if sources:
            payload["sources"] = sources

        headers = {"accept": "application/json", "Content-Type": "application/json", "X-API-KEY": self.api_key}
        try:
            resp = requests.post(self.api_url, json=payload, headers=headers, timeout=timeout)
            if resp.status_code != 200:
                LOGGER.warning("Non-200 response %s for %s: %s", resp.status_code, date.date(), resp.text[:200])
                return False
            data = resp.json()
            articles = data.get("articles", []) if isinstance(data, dict) else []
            return len(articles) > 0
        except Exception as e:
            LOGGER.warning("Request failed for %s: %s", date.date(), e)
            return False


class MassiveProber:
    """Massive API (formerly Polygon.io) probe implementation."""

    def __init__(self, api_key: str):
        self.api_url = "https://api.massive.com/v2/reference/news"
        self.api_key = api_key

    def probe_day(self, date: datetime, ticker: Optional[str] = None, timeout: int = 10, max_retries: int = 3) -> bool:
        """Return True if articles exist for the given date and ticker."""
        import time

        params = {
            "apiKey": self.api_key,
            "limit": 1,
            "order": "asc",
            "sort": "published_utc",
            "published_utc.gte": date.strftime("%Y-%m-%d"),
            "published_utc.lte": (date + timedelta(days=1)).strftime("%Y-%m-%d"),
        }
        if ticker:
            params["ticker"] = ticker.upper()

        headers = {"accept": "application/json"}

        for attempt in range(max_retries):
            try:
                resp = requests.get(self.api_url, params=params, headers=headers, timeout=timeout)
                if resp.status_code == 429:
                    # Rate limit hit; wait and retry
                    retry_after = int(resp.headers.get("Retry-After", 60))
                    LOGGER.warning("Rate limit (429) for %s; sleeping %ds...", date.date(), retry_after)
                    time.sleep(retry_after)
                    continue
                if resp.status_code != 200:
                    LOGGER.warning("Non-200 response %s for %s: %s", resp.status_code, date.date(), resp.text[:200])
                    return False
                data = resp.json()
                count = data.get("count", 0)
                results = data.get("results", [])
                return count > 0 and len(results) > 0
            except Exception as e:
                LOGGER.warning("Request failed for %s (attempt %d): %s", date.date(), attempt + 1, e)
                if attempt < max_retries - 1:
                    time.sleep(2 ** attempt)  # exponential backoff
        return False


def find_first_date(
    prober, start_date: datetime, end_date: datetime, query_or_ticker: Optional[str] = None, sources: Optional[list[str]] = None
) -> Optional[datetime]:
    """Find earliest date with articles using exponential forward + binary search."""
    LOGGER.info("Starting probe from %s to %s", start_date.date(), end_date.date())

    # Quick check start date
    if isinstance(prober, FinlightProber):
        has_data = prober.probe_day(start_date, query_or_ticker, sources)
    else:
        has_data = prober.probe_day(start_date, query_or_ticker)

    if has_data:
        LOGGER.info("Data exists on start date %s", start_date.date())
        return start_date

    # Exponential forward search
    step_days = 1
    prev_no = start_date
    current = start_date + timedelta(days=step_days)

    while current <= end_date:
        LOGGER.info("Probing %s (step %d days)", current.date(), step_days)
        if isinstance(prober, FinlightProber):
            has_data = prober.probe_day(current, query_or_ticker, sources)
        else:
            has_data = prober.probe_day(current, query_or_ticker)

        if has_data:
            LOGGER.info("Found articles at %s; binary-searching earliest day", current.date())
            # Binary search between prev_no and current
            low = prev_no
            high = current
            while (high - low).days > 1:
                mid = low + (high - low) // 2
                LOGGER.info("Binary probe mid=%s", mid.date())
                if isinstance(prober, FinlightProber):
                    mid_has_data = prober.probe_day(mid, query_or_ticker, sources)
                else:
                    mid_has_data = prober.probe_day(mid, query_or_ticker)

                if mid_has_data:
                    high = mid
                else:
                    low = mid
            return high

        prev_no = current
        step_days = min(step_days * 2, 30)
        current = current + timedelta(days=step_days)

    LOGGER.info("No articles found in range %s - %s", start_date.date(), end_date.date())
    return None


def save_result(out_path: str, result: dict) -> None:
    """Save probe result to JSON file."""
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    with open(out_path, "w") as f:
        json.dump(result, f, indent=2, default=str)


def main() -> None:
    parser = argparse.ArgumentParser(description="Find earliest date with news articles for a ticker/query")
    parser.add_argument("--provider", choices=["finlight", "massive"], default="massive", help="API provider to use")
    parser.add_argument("--start", default="2020-01-01", help="start date (YYYY-MM-DD)")
    parser.add_argument("--end", default="2026-01-01", help="end date (YYYY-MM-DD)")
    parser.add_argument("--ticker", help="ticker symbol (e.g., 'AAPL', 'AMX') - for Massive")
    parser.add_argument("--query", help="query string (e.g., 'ticker:AAPL') - for Finlight")
    parser.add_argument(
        "--sources", help="comma-separated sources (e.g., 'finance.yahoo.com' or '*') - Finlight only"
    )
    parser.add_argument("--out", default="logs/news_probe_result.json", help="output JSON file")
    args = parser.parse_args()

    start_date = datetime.strptime(args.start, "%Y-%m-%d")
    end_date = datetime.strptime(args.end, "%Y-%m-%d")

    # Initialize prober
    if args.provider == "finlight":
        api_key = os.getenv("FINLIGHT_API_KEY", "sk_621d88dfcc31a1d3efa89a2873d394563f53bfd6fe1c7aec2ffd22e45d7b1d44")
        prober = FinlightProber(api_key)
        query_or_ticker = args.query
        sources = None
        if args.sources:
            sources = ["*"] if args.sources.strip() == "*" else [s.strip() for s in args.sources.split(",") if s.strip()]
        LOGGER.info("Using Finlight API with query=%s sources=%s", query_or_ticker, sources)
    else:  # massive
        api_key = os.getenv("MASSIVE_API_KEY", "rsoLbE3CQLL2pVXvbEpsjeqMBYtSFTp0")
        prober = MassiveProber(api_key)
        query_or_ticker = args.ticker
        sources = None
        LOGGER.info("Using Massive API with ticker=%s", query_or_ticker)

    # Run probe
    first = find_first_date(prober, start_date, end_date, query_or_ticker, sources)

    # Save result
    result = {
        "provider": args.provider,
        "start_query": args.start,
        "end_query": args.end,
        "ticker": args.ticker,
        "query": args.query,
        "sources": sources,
        "first_date_with_articles": str(first.date()) if first else None,
    }
    save_result(args.out, result)
    if first:
        LOGGER.info("Earliest date with articles: %s", first.date())
    else:
        LOGGER.info("No articles found in range")


if __name__ == "__main__":
    main()
