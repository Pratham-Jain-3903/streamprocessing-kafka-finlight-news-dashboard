#!/usr/bin/env python3
"""
Probe Finlight API to find the earliest date with available articles in a range.

Strategy:
 - Start at `start_date` and probe one-day windows.
 - If no data, advance forward by an exponentially increasing step (1,2,4,8... days)
   until we find a day with data or exceed `end_date`.
 - Once a day with data is found, binary-search between the last known-empty
   day and the found day to locate the earliest day containing articles.

Saves result to `logs/finlight_first_date.json` and prints findings.
"""

from __future__ import annotations

import argparse
import json
import logging
import os
from datetime import datetime, timedelta
from typing import Optional

import requests


LOGGER = logging.getLogger("finlight_probe")
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")


API_URL = os.getenv("FINLIGHT_API_URL", "https://api.finlight.me/v2/articles")
API_KEY = os.getenv("FINLIGHT_API_KEY", "sk_621d88dfcc31a1d3efa89a2873d394563f53bfd6fe1c7aec2ffd22e45d7b1d44")


def probe_day(date: datetime, query: Optional[str] = None, sources: Optional[list[str]] = None, timeout: int = 10) -> bool:
    """Return True if any articles exist for the given calendar date (UTC).

    Uses a 1-day window from `date` 00:00 to `date` 23:59.
    If `query` or `sources` are provided they will be included in the POST body.
    """
    from_ts = date.strftime("%Y-%m-%dT00:00")
    to_ts = (date + timedelta(days=1)).strftime("%Y-%m-%dT00:00")
    payload = {
        "from": from_ts,
        "to": to_ts,
        "pageSize": 1,
        "page": 1,
    }
    if query:
        payload["query"] = query
    if sources:
        payload["sources"] = sources

    headers = {
        "accept": "application/json",
        "Content-Type": "application/json",
        "X-API-KEY": API_KEY,
    }
    try:
        resp = requests.post(API_URL, json=payload, headers=headers, timeout=timeout)
        if resp.status_code != 200:
            LOGGER.warning("Non-200 response %s for %s (q=%s): %s", resp.status_code, date.date(), query, resp.text[:200])
            return False
        data = resp.json()
        articles = data.get("articles", []) if isinstance(data, dict) else []
        return len(articles) > 0
    except Exception as e:
        LOGGER.warning("Request failed for %s (q=%s): %s", date.date(), query, e)
        return False


def probe_with_combinations(date: datetime, queries: list[str], sources: list[str], timeout: int = 10) -> Optional[dict]:
    """Try combinations of queries and sources for a single date.

    Returns a dict with the successful combination or None.
    """
    from time import sleep

    # try no-query first (generic)
    try:
        if probe_day(date, None, None, timeout=timeout):
            return {"query": None, "source": None}
    except Exception:
        pass

    # iterate queries and sources
    for q in queries:
        for s in sources:
            try:
                if probe_day(date, q, [s], timeout=timeout):
                    return {"query": q, "source": s}
            except Exception:
                pass
            sleep(0.3)
    return None


def find_first_date(start_date: datetime, end_date: datetime) -> Optional[datetime]:
    # quick check
    LOGGER.info("Starting probe from %s to %s", start_date.date(), end_date.date())
    if probe_day(start_date):
        LOGGER.info("Data exists on start date %s", start_date.date())
        return start_date

    # Exponential forward search to find a date with data
    step_days = 1
    prev_no = start_date
    current = start_date + timedelta(days=step_days)

    while current <= end_date:
        LOGGER.info("Probing %s (step %d days)", current.date(), step_days)
        if probe_day(current):
            LOGGER.info("Found articles at %s; binary-searching earliest day", current.date())
            # binary search between prev_no (no data) and current (has data)
            low = prev_no
            high = current
            while (high - low).days > 1:
                mid = low + (high - low) // 2
                LOGGER.info("Binary probe mid=%s", mid.date())
                if probe_day(mid):
                    high = mid
                else:
                    low = mid
            return high

        # advance forward exponentially
        prev_no = current
        step_days = min(step_days * 2, 30)
        current = current + timedelta(days=step_days)

    LOGGER.info("No articles found in range %s - %s", start_date.date(), end_date.date())
    return None


def save_result(out_path: str, result: dict) -> None:
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    with open(out_path, "w") as f:
        json.dump(result, f, indent=2, default=str)


def main() -> None:
    parser = argparse.ArgumentParser(description="Find earliest date with Finlight articles in a range")
    parser.add_argument("--start", default="2020-01-01", help="start date (YYYY-MM-DD)")
    parser.add_argument("--end", default="2026-01-01", help="end date (YYYY-MM-DD)")
    parser.add_argument("--out", default="logs/finlight_first_date.json", help="output JSON file")
    parser.add_argument("--query", default=None, help="optional query string (e.g. 'ticker:NVDA')")
    parser.add_argument("--sources", default=None, help="optional comma-separated sources (e.g. 'finance.yahoo.com,cointelegraph.com' or '*' for all)")
    args = parser.parse_args()

    start_date = datetime.strptime(args.start, "%Y-%m-%d")
    end_date = datetime.strptime(args.end, "%Y-%m-%d")

    # If a single query/sources is provided, use it when probing days.
    sources: Optional[list[str]] = None
    if args.sources:
        if args.sources.strip() == "*":
            sources = ["*"]
        else:
            sources = [s.strip() for s in args.sources.split(",") if s.strip()]

    # Exponential forward + binary search: find earliest date with articles in [start_date, end_date]
    if args.query:
        LOGGER.info("Probing with query=%s sources=%s", args.query, sources)
        if probe_day(start_date, args.query, sources):
            first = start_date
        else:
            # Exponential forward search to find any date with data
            step_days = 1
            prev_no = start_date
            current = start_date + timedelta(days=step_days)
            first = None
            while current <= end_date:
                LOGGER.info("Probing %s (step %d days) with query=%s", current.date(), step_days, args.query)
                if probe_day(current, args.query, sources):
                    LOGGER.info("Found articles at %s; binary-searching earliest day", current.date())
                    # Binary search between prev_no (no data) and current (has data)
                    low = prev_no
                    high = current
                    while (high - low).days > 1:
                        mid = low + (high - low) // 2
                        LOGGER.info("Binary probe mid=%s (q=%s)", mid.date(), args.query)
                        if probe_day(mid, args.query, sources):
                            high = mid
                        else:
                            low = mid
                    first = high
                    break
                prev_no = current
                step_days = min(step_days * 2, 30)
                current = current + timedelta(days=step_days)
    else:
        first = find_first_date(start_date, end_date)
    result = {
        "start_query": args.start,
        "end_query": args.end,
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
