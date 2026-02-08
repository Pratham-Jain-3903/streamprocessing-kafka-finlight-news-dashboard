#!/usr/bin/env python3
"""Calculate correlation between sentiment and price returns."""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import pandas as pd
import numpy as np
from config.stock_universe import TOP_10_TECH_STOCKS, LOOKBACK_HOURS, MIN_NEWS_COUNT

def load_data():
    """Load prices and news."""
    prices = {}
    print("Loading price data...")
    for ticker in TOP_10_TECH_STOCKS:
        file = Path(f"data/prices/{ticker}_ohlcv.parquet")
        if file.exists():
            df = pd.read_parquet(file)
            df.index = pd.to_datetime(df.index).tz_localize('UTC')  # Make timezone-aware
            prices[ticker] = df
            print(f"  {ticker}: {len(df)} rows")
        else:
            print(f"  {ticker}: ✗ Not found")
    
    print("\nLoading news data...")
    news_file = Path("data/news/news_with_sentiment.parquet")
    if not news_file.exists():
        print(f"✗ Error: {news_file} not found. Run 03_add_sentiment.py first.")
        sys.exit(1)
    
    news = pd.read_parquet(news_file)
    news['published_utc'] = pd.to_datetime(news['published_utc'])
    print(f"  Total articles: {len(news)}")
    
    return prices, news

def calculate_returns(prices_dict):
    """Add forward returns to price data."""
    for ticker, df in prices_dict.items():
        df['return_1d'] = df['Close'].pct_change(1).shift(-1)
        df['return_3d'] = df['Close'].pct_change(3).shift(-3)
        df['return_5d'] = df['Close'].pct_change(5).shift(-5)
    return prices_dict

def aggregate_sentiment_for_date(news_df, ticker, date, lookback_hours=24):
    """Get average sentiment for ticker around a date."""
    start_time = date - pd.Timedelta(hours=lookback_hours)
    end_time = date + pd.Timedelta(days=1)
    
    mask = (
        (news_df['ticker_queried'] == ticker) &
        (news_df['published_utc'] >= start_time) &
        (news_df['published_utc'] < end_time)
    )
    
    articles = news_df[mask]
    
    if len(articles) == 0:
        return None, 0
    
    return articles['sentiment'].mean(), len(articles)

def run_correlation_analysis():
    """Main correlation analysis."""
    prices, news = load_data()
    prices = calculate_returns(prices)
    
    print("\n" + "="*60)
    print("Aligning sentiment with price returns...")
    print("="*60)
    
    results = []
    
    for ticker in prices.keys():
        print(f"  {ticker}...", end=" ", flush=True)
        price_df = prices[ticker]
        ticker_count = 0
        
        for date in price_df.index:
            sentiment, count = aggregate_sentiment_for_date(
                news, ticker, date, LOOKBACK_HOURS
            )
            
            try:
                return_1d = price_df.at[date, 'return_1d']
                
                if sentiment is not None and count >= MIN_NEWS_COUNT and pd.notna(return_1d):
                    results.append({
                        'ticker': ticker,
                        'date': date,
                        'sentiment': float(sentiment),
                        'news_count': int(count),
                        'return_1d': float(return_1d),
                        'return_3d': float(price_df.at[date, 'return_3d']) if pd.notna(price_df.at[date, 'return_3d']) else None,
                        'return_5d': float(price_df.at[date, 'return_5d']) if pd.notna(price_df.at[date, 'return_5d']) else None,
                        'close': float(price_df.at[date, 'Close']),
                        'volume': float(price_df.at[date, 'Volume'])
                    })
                    ticker_count += 1
            except (KeyError, ValueError):
                pass
        
        print(f"{ticker_count} observations")
    
    # Create results dataframe
    results_df = pd.DataFrame(results)
    
    # Save
    output_dir = Path("data/analysis")
    output_dir.mkdir(parents=True, exist_ok=True)
    output_file = output_dir / "sentiment_returns.parquet"
    results_df.to_parquet(output_file)
    
    # Print correlations
    print("\n" + "="*60)
    print("CORRELATION ANALYSIS: Sentiment vs Returns")
    print("="*60)
    print(f"{'Ticker':<8} {'1-Day':<10} {'3-Day':<10} {'5-Day':<10} {'Obs':<8}")
    print("-"*60)
    
    for ticker in TOP_10_TECH_STOCKS:
        ticker_data = results_df[results_df['ticker'] == ticker]
        if len(ticker_data) > 0:
            corr_1d = ticker_data['sentiment'].corr(ticker_data['return_1d'])
            corr_3d = ticker_data['sentiment'].corr(ticker_data['return_3d'])
            corr_5d = ticker_data['sentiment'].corr(ticker_data['return_5d'])
            print(f"{ticker:<8} {corr_1d:+.3f}      {corr_3d:+.3f}      {corr_5d:+.3f}      {len(ticker_data):<8}")
    
    print("-"*60)
    overall_1d = results_df['sentiment'].corr(results_df['return_1d'])
    overall_3d = results_df['sentiment'].corr(results_df['return_3d'])
    overall_5d = results_df['sentiment'].corr(results_df['return_5d'])
    print(f"{'OVERALL':<8} {overall_1d:+.3f}      {overall_3d:+.3f}      {overall_5d:+.3f}      {len(results_df):<8}")
    print("="*60)
    
    # Save summary
    summary = {
        'overall_correlation_1d': overall_1d,
        'overall_correlation_3d': overall_3d,
        'overall_correlation_5d': overall_5d,
        'total_observations': len(results_df),
        'date_range': [str(results_df['date'].min()), str(results_df['date'].max())],
    }
    
    import json
    with open(output_dir / "correlation_summary.json", 'w') as f:
        json.dump(summary, f, indent=2)
    
    print(f"\n✓ Results saved to {output_file}")
    print(f"✓ Summary saved to {output_dir / 'correlation_summary.json'}")
    
    return results_df

if __name__ == "__main__":
    df = run_correlation_analysis()
