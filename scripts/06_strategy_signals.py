"""
Strategy Signal Generator: Create BUY/SELL/HOLD signals based on lag analysis.

Uses optimal configurations from lag analysis to generate trading signals.
"""

import pandas as pd
import numpy as np
from pathlib import Path
import json
import sys
sys.path.append(str(Path(__file__).parent.parent))

from config.stock_universe import (
    TOP_10_TECH_STOCKS,
    SENTIMENT_THRESHOLD,
    MIN_NEWS_COUNT,
    STOP_LOSS_PCT,
    TAKE_PROFIT_PCT,
    HOLD_PERIOD_HOURS
)

# Convert config values to script format
STOP_LOSS = -STOP_LOSS_PCT  # Convert to negative
TAKE_PROFIT = TAKE_PROFIT_PCT
HOLD_PERIOD_DAYS = HOLD_PERIOD_HOURS / 24  # Convert hours to days
MIN_CORRELATION_THRESHOLD = 0.25  # Filter out weak correlations (fixed)

def load_lag_results():
    """Load optimal configurations from lag analysis."""
    analysis_path = Path(__file__).parent.parent / 'data' / 'analysis' / 'lag_analysis.json'
    with open(analysis_path, 'r') as f:
        return json.load(f)

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
    """Aggregate sentiment for a stock within lookback window."""
    ticker_news = news_df[news_df['ticker_queried'] == ticker].copy()
    
    end_time = date
    start_time = date - pd.Timedelta(hours=lookback_hours)
    
    window_news = ticker_news[
        (ticker_news['published_utc'] >= start_time) & 
        (ticker_news['published_utc'] < end_time)
    ]
    
    count = len(window_news)
    if count < MIN_NEWS_COUNT:
        return None, count
    
    avg_sentiment = window_news['sentiment'].mean()
    return avg_sentiment, count

def generate_signals(news_df, price_data, lag_results):
    """
    Generate trading signals for all stocks.
    
    Returns:
        DataFrame with columns: date, ticker, signal, sentiment, news_count, 
                               close_price, lookback_hours, lead_days
    """
    all_signals = []
    
    for ticker in TOP_10_TECH_STOCKS:
        print(f"Generating signals for {ticker}...")
        
        # Get optimal configuration
        best_config = lag_results[ticker]['best_config']
        if not best_config:
            print(f"  No optimal config found for {ticker}, skipping")
            continue
        
        # Filter weak correlations
        correlation = abs(best_config['correlation'])
        if correlation < MIN_CORRELATION_THRESHOLD:
            print(f"  Weak correlation ({correlation:.3f} < {MIN_CORRELATION_THRESHOLD}), skipping {ticker}")
            continue
        
        lookback_hours = best_config['lookback_hours']
        lead_days = best_config['lead_days']
        
        price_df = price_data[ticker]
        
        # Generate signals for each trading day
        for date in price_df.index:
            # Calculate sentiment
            sentiment, news_count = aggregate_sentiment(
                news_df, ticker, date, lookback_hours
            )
            
            if sentiment is None:
                continue
            
            # Generate signal (flip for inverse correlations)
            is_inverse = best_config['correlation'] < 0
            
            if is_inverse:
                # Inverse correlation: high sentiment → sell, low sentiment → buy
                if sentiment > SENTIMENT_THRESHOLD:
                    signal = 'SELL'
                elif sentiment < -SENTIMENT_THRESHOLD:
                    signal = 'BUY'
                else:
                    signal = 'HOLD'
            else:
                # Positive correlation: high sentiment → buy, low sentiment → sell
                if sentiment > SENTIMENT_THRESHOLD:
                    signal = 'BUY'
                elif sentiment < -SENTIMENT_THRESHOLD:
                    signal = 'SELL'
                else:
                    signal = 'HOLD'
            
            # Get price
            close_price = price_df.at[date, 'Close']
            
            all_signals.append({
                'date': date,
                'ticker': ticker,
                'signal': signal,
                'sentiment': sentiment,
                'news_count': news_count,
                'close_price': close_price,
                'lookback_hours': lookback_hours,
                'lead_days': lead_days,
                'correlation': best_config['correlation'],
                'signal_type': 'inverse' if is_inverse else 'direct'
            })
    
    signals_df = pd.DataFrame(all_signals)
    return signals_df

def run_signal_generation():
    """Main function to generate all trading signals."""
    print("Loading lag analysis results...")
    lag_results = load_lag_results()
    
    print("\nLoading price and news data...")
    news_df, price_data = load_data()
    
    print("\nGenerating trading signals...")
    signals_df = generate_signals(news_df, price_data, lag_results)
    
    # Save signals
    output_dir = Path(__file__).parent.parent / 'data' / 'signals'
    output_dir.mkdir(parents=True, exist_ok=True)
    
    output_path = output_dir / 'trading_signals.parquet'
    signals_df.to_parquet(output_path, index=False)
    
    print(f"\nSignals saved to {output_path}")
    
    # Print summary statistics
    print("\n" + "="*60)
    print("SIGNAL SUMMARY")
    print("="*60)
    print(f"Total signals generated: {len(signals_df)}")
    print(f"Stocks included: {signals_df['ticker'].nunique()}")
    print(f"Stocks filtered (weak correlation): {len(TOP_10_TECH_STOCKS) - signals_df['ticker'].nunique()}")
    print(f"\nSignal distribution:")
    print(signals_df['signal'].value_counts())
    
    print(f"\nSignal type distribution:")
    print(signals_df['signal_type'].value_counts())
    
    print(f"\nSignals by ticker:")
    for ticker in TOP_10_TECH_STOCKS:
        ticker_signals = signals_df[signals_df['ticker'] == ticker]
        if len(ticker_signals) > 0:
            buy_pct = (ticker_signals['signal'] == 'BUY').sum() / len(ticker_signals) * 100
            print(f"  {ticker:6s}: {len(ticker_signals):4d} signals "
                  f"({buy_pct:.1f}% BUY)")
    
    print(f"\nAverage sentiment: {signals_df['sentiment'].mean():.3f}")
    print(f"Average news count: {signals_df['news_count'].mean():.1f}")
    
    return signals_df

if __name__ == '__main__':
    signals_df = run_signal_generation()
