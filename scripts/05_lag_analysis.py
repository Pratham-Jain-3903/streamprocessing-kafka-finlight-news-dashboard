"""
Lag Analysis: Find optimal lookback windows and lead times for each stock.

Tests various combinations of:
- Lookback windows (how far back to aggregate sentiment): 6h, 12h, 24h, 48h, 72h
- Lead times (future return period): 1d, 2d, 3d, 5d
"""

import pandas as pd
import numpy as np
from pathlib import Path
from scipy.stats import pearsonr
import json
import sys
sys.path.append(str(Path(__file__).parent.parent))

from config.stock_universe import TOP_10_TECH_STOCKS

# Configuration
LOOKBACK_WINDOWS = [6, 12, 24, 48, 72]  # hours
LEAD_TIMES = [1, 2, 3, 5]  # days
MIN_NEWS_COUNT = 3
MIN_OBSERVATIONS = 30

def load_data():
    """Load price and news data."""
    prices_dir = Path(__file__).parent.parent / 'data' / 'prices'
    news_path = Path(__file__).parent.parent / 'data' / 'news' / 'news_with_sentiment.parquet'
    
    # Load news with sentiment
    news_df = pd.read_parquet(news_path)
    news_df['published_utc'] = pd.to_datetime(news_df['published_utc'])
    
    # Load prices for all stocks
    price_data = {}
    for ticker in TOP_10_TECH_STOCKS:
        price_file = prices_dir / f"{ticker}_ohlcv.parquet"
        if price_file.exists():
            df = pd.read_parquet(price_file)
            df.index = pd.to_datetime(df.index).tz_localize('UTC')
            price_data[ticker] = df
    
    return news_df, price_data

def aggregate_sentiment(news_df, ticker, date, lookback_hours):
    """
    Aggregate sentiment for a stock within lookback window.
    
    Args:
        news_df: DataFrame with news articles
        ticker: Stock ticker
        date: Target date (timezone-aware)
        lookback_hours: Hours to look back
        
    Returns:
        (avg_sentiment, news_count) or (None, 0)
    """
    # Filter for this ticker
    ticker_news = news_df[news_df['ticker_queried'] == ticker].copy()
    
    # Define time window
    end_time = date
    start_time = date - pd.Timedelta(hours=lookback_hours)
    
    # Get articles in window
    window_news = ticker_news[
        (ticker_news['published_utc'] >= start_time) & 
        (ticker_news['published_utc'] < end_time)
    ]
    
    count = len(window_news)
    if count < MIN_NEWS_COUNT:
        return None, count
    
    avg_sentiment = window_news['sentiment'].mean()
    return avg_sentiment, count

def calculate_forward_return(price_df, date, lead_days):
    """
    Calculate forward return from date to lead_days later.
    
    Args:
        price_df: Price dataframe for a stock
        date: Starting date (timezone-aware)
        lead_days: Days forward to calculate return
        
    Returns:
        Forward return as decimal (0.05 = 5%) or None
    """
    try:
        # Get current price
        if date not in price_df.index:
            return None
        current_price = price_df.at[date, 'Close']
        
        # Get future price (lead_days later)
        future_dates = price_df.index[price_df.index > date]
        if len(future_dates) < lead_days:
            return None
        
        future_date = future_dates[lead_days - 1]
        future_price = price_df.at[future_date, 'Close']
        
        # Calculate return
        ret = (future_price - current_price) / current_price
        return ret
        
    except (KeyError, IndexError):
        return None

def analyze_lag_combination(news_df, price_data, ticker, lookback_hours, lead_days):
    """
    Test a specific combination of lookback window and lead time.
    
    Returns:
        Dict with correlation, p-value, observations, mean_return, mean_sentiment
    """
    price_df = price_data[ticker]
    results = []
    
    # For each trading day, calculate sentiment and forward return
    for date in price_df.index:
        # Aggregate sentiment with lookback
        sentiment, news_count = aggregate_sentiment(news_df, ticker, date, lookback_hours)
        if sentiment is None:
            continue
        
        # Calculate forward return
        forward_return = calculate_forward_return(price_df, date, lead_days)
        if forward_return is None:
            continue
        
        results.append({
            'date': date,
            'sentiment': sentiment,
            'news_count': news_count,
            'forward_return': forward_return
        })
    
    # Calculate correlation if we have enough observations
    if len(results) < MIN_OBSERVATIONS:
        return {
            'correlation': None,
            'p_value': None,
            'observations': len(results),
            'mean_return': None,
            'mean_sentiment': None
        }
    
    df = pd.DataFrame(results)
    corr, p_value = pearsonr(df['sentiment'], df['forward_return'])
    
    return {
        'correlation': corr,
        'p_value': p_value,
        'observations': len(results),
        'mean_return': df['forward_return'].mean(),
        'mean_sentiment': df['sentiment'].mean()
    }

def run_lag_analysis():
    """Run full lag analysis for all stocks and parameter combinations."""
    print("Loading data...")
    news_df, price_data = load_data()
    
    results = {}
    
    for ticker in TOP_10_TECH_STOCKS:
        print(f"\n{'='*60}")
        print(f"Analyzing {ticker}")
        print(f"{'='*60}")
        
        ticker_results = {}
        best_corr = 0
        best_config = None
        
        for lookback_hours in LOOKBACK_WINDOWS:
            for lead_days in LEAD_TIMES:
                config_key = f"{lookback_hours}h_{lead_days}d"
                
                result = analyze_lag_combination(
                    news_df, price_data, ticker, 
                    lookback_hours, lead_days
                )
                
                ticker_results[config_key] = result
                
                # Track best configuration
                if result['correlation'] is not None:
                    if abs(result['correlation']) > abs(best_corr):
                        best_corr = result['correlation']
                        best_config = {
                            'lookback_hours': lookback_hours,
                            'lead_days': lead_days,
                            'correlation': result['correlation'],
                            'p_value': result['p_value'],
                            'observations': result['observations']
                        }
                    
                    # Print result
                    print(f"  {config_key:10s} | Corr: {result['correlation']:+.3f} | "
                          f"p-val: {result['p_value']:.4f} | "
                          f"Obs: {result['observations']:3d}")
        
        results[ticker] = {
            'all_configs': ticker_results,
            'best_config': best_config
        }
        
        if best_config:
            print(f"\n  BEST: {best_config['lookback_hours']}h lookback, "
                  f"{best_config['lead_days']}d lead | "
                  f"Corr: {best_config['correlation']:+.3f} | "
                  f"p-val: {best_config['p_value']:.4f}")
    
    # Save results
    output_dir = Path(__file__).parent.parent / 'data' / 'analysis'
    output_dir.mkdir(parents=True, exist_ok=True)
    
    output_path = output_dir / 'lag_analysis.json'
    with open(output_path, 'w') as f:
        # Convert results to JSON-serializable format
        json_results = {}
        for ticker, data in results.items():
            json_results[ticker] = {
                'best_config': data['best_config'],
                'all_configs': data['all_configs']
            }
        json.dump(json_results, f, indent=2)
    
    print(f"\n\nResults saved to {output_path}")
    
    # Print summary
    print("\n" + "="*60)
    print("SUMMARY: Best Configuration per Stock")
    print("="*60)
    for ticker in TOP_10_TECH_STOCKS:
        best = results[ticker]['best_config']
        if best:
            print(f"{ticker:6s} | {best['lookback_hours']:2d}h lookback, "
                  f"{best['lead_days']}d lead | "
                  f"Corr: {best['correlation']:+.3f} | "
                  f"Obs: {best['observations']:3d}")
        else:
            print(f"{ticker:6s} | No sufficient data")
    
    return results

if __name__ == '__main__':
    results = run_lag_analysis()
