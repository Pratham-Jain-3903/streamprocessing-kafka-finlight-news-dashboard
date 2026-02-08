#!/usr/bin/env python3
"""Fetch historical OHLCV data for stock universe."""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import yfinance as yf
import pandas as pd
from config.stock_universe import TOP_10_TECH_STOCKS, HISTORICAL_START, BACKTEST_END

def fetch_and_save_prices():
    """Fetch price data and save to parquet."""
    output_dir = Path("data/prices")
    output_dir.mkdir(parents=True, exist_ok=True)
    
    print(f"Fetching prices for {len(TOP_10_TECH_STOCKS)} stocks from {HISTORICAL_START} to {BACKTEST_END}...")
    print("="*60)
    
    for ticker in TOP_10_TECH_STOCKS:
        print(f"  Downloading {ticker}...", end=" ", flush=True)
        try:
            df = yf.download(ticker, start=HISTORICAL_START, end=BACKTEST_END, progress=False)
            if len(df) > 0:
                # Flatten MultiIndex columns if present
                if isinstance(df.columns, pd.MultiIndex):
                    df.columns = [col[0] for col in df.columns]
                df['ticker'] = ticker
                output_file = output_dir / f"{ticker}_ohlcv.parquet"
                df.to_parquet(output_file)
                print(f"✓ {len(df)} rows")
            else:
                print(f"✗ No data returned")
        except Exception as e:
            print(f"✗ Error: {e}")
    
    print("="*60)
    print(f"✓ Done! Price data saved to data/prices/")

if __name__ == "__main__":
    fetch_and_save_prices()
