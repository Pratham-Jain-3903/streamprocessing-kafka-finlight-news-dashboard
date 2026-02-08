#!/usr/bin/env python3
"""Fetch historical news for all tickers in yearly batches."""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from ingestion.massive_api import fetch_news
from config.stock_universe import TOP_10_TECH_STOCKS, BACKTEST_START, BACKTEST_END
from datetime import datetime, timedelta
import pandas as pd
import json
import time

def get_existing_date_range(output_dir):
    """Check existing news data date range."""
    all_news_file = output_dir / "all_news.parquet"
    if all_news_file.exists():
        df = pd.read_parquet(all_news_file)
        return df['published_utc'].min(), df['published_utc'].max()
    return None, None

def create_yearly_batches(start_date, end_date):
    """Split date range into yearly batches."""
    batches = []
    current = start_date
    
    while current < end_date:
        # End of current year or overall end_date, whichever is earlier
        year_end = datetime(current.year, 12, 31)
        batch_end = min(year_end, end_date)
        
        batches.append((current, batch_end))
        
        # Move to next year
        current = datetime(current.year + 1, 1, 1)
        if current > end_date:
            break
    
    return batches

def fetch_batch_news(ticker, start, end, output_dir):
    """Fetch news for a single ticker within date range."""
    try:
        result = fetch_news(ticker=ticker, start_date=start, end_date=end, limit=1000)
        articles = result.get("results", [])
        
        for article in articles:
            article['ticker_queried'] = ticker
        
        return articles
    except Exception as e:
        print(f"\n  ✗ Error fetching {ticker}: {e}")
        return []

def fetch_all_news():
    """Fetch news for all tickers in yearly batches."""
    output_dir = Path("data/news")
    output_dir.mkdir(parents=True, exist_ok=True)
    
    start = datetime.strptime(BACKTEST_START, "%Y-%m-%d")
    end = datetime.strptime(BACKTEST_END, "%Y-%m-%d")
    
    # Check existing data
    existing_start, existing_end = get_existing_date_range(output_dir)
    if existing_start:
        print(f"📂 Existing news data: {existing_start} to {existing_end}")
        print(f"📅 Requested range: {BACKTEST_START} to {BACKTEST_END}")
        
        # Load existing data
        existing_df = pd.read_parquet(output_dir / "all_news.parquet")
        print(f"✓ Loaded {len(existing_df):,} existing articles")
    else:
        print(f"📅 No existing data found. Fetching full range: {BACKTEST_START} to {BACKTEST_END}")
        existing_df = pd.DataFrame()
    
    # Create yearly batches
    batches = create_yearly_batches(start, end)
    
    print(f"\n📊 Fetching news in {len(batches)} yearly batch(es):")
    for i, (batch_start, batch_end) in enumerate(batches, 1):
        print(f"  Batch {i}: {batch_start.strftime('%Y-%m-%d')} to {batch_end.strftime('%Y-%m-%d')}")
    
    print("\n" + "="*70)
    print(f"⏱️  Estimated time: ~{len(batches) * len(TOP_10_TECH_STOCKS) * 13 / 60:.1f} minutes (rate limit: 5 req/min)")
    print("="*70 + "\n")
    
    all_new_articles = []
    
    for batch_num, (batch_start, batch_end) in enumerate(batches, 1):
        print(f"📦 Batch {batch_num}/{len(batches)}: {batch_start.year}")
        print("-" * 70)
        
        for ticker_num, ticker in enumerate(TOP_10_TECH_STOCKS, 1):
            print(f"  [{ticker_num:2d}/{len(TOP_10_TECH_STOCKS)}] {ticker:6s} ", end="", flush=True)
            
            articles = fetch_batch_news(ticker, batch_start, batch_end, output_dir)
            all_new_articles.extend(articles)
            
            print(f"✓ {len(articles):4d} articles")
            
            # Rate limit: 5 requests per minute = 12 seconds between calls
            if ticker_num < len(TOP_10_TECH_STOCKS) or batch_num < len(batches):
                time.sleep(13)
        
        print()
    
    # Combine with existing data
    if all_new_articles:
        new_df = pd.DataFrame(all_new_articles)
        
        if not existing_df.empty:
            # Merge and deduplicate
            combined_df = pd.concat([existing_df, new_df], ignore_index=True)
            
            # Deduplicate by article URL or ID
            if 'article_url' in combined_df.columns:
                combined_df = combined_df.drop_duplicates(subset=['article_url'], keep='last')
            elif 'id' in combined_df.columns:
                combined_df = combined_df.drop_duplicates(subset=['id'], keep='last')
            
            print(f"📊 Merge stats:")
            print(f"  Existing: {len(existing_df):,}")
            print(f"  New: {len(new_df):,}")
            print(f"  Combined (after dedup): {len(combined_df):,}")
        else:
            combined_df = new_df
        
        # Save combined file
        combined_df = combined_df.sort_values('published_utc')
        combined_df.to_parquet(output_dir / "all_news.parquet")
        
        print("\n" + "="*70)
        print(f"✅ SUCCESS: {len(combined_df):,} total articles saved")
        print(f"📅 Date range: {combined_df['published_utc'].min()} to {combined_df['published_utc'].max()}")
        print(f"📁 Location: {output_dir / 'all_news.parquet'}")
        print("="*70)
        
        # Save individual ticker files for convenience
        print("\n💾 Saving per-ticker files...")
        for ticker in combined_df['ticker_queried'].unique():
            ticker_df = combined_df[combined_df['ticker_queried'] == ticker]
            ticker_df.to_parquet(output_dir / f"{ticker}_news.parquet")
        print(f"✓ Saved {len(combined_df['ticker_queried'].unique())} ticker files")
        
    else:
        print("\n⚠️  No new articles fetched")

if __name__ == "__main__":
    fetch_all_news()
