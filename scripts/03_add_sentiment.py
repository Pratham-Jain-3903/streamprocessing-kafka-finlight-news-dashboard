#!/usr/bin/env python3
"""Add VADER sentiment scores to news data."""

import pandas as pd
from pathlib import Path
from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer

def add_sentiment():
    """Calculate and add sentiment scores."""
    analyzer = SentimentIntensityAnalyzer()
    
    input_file = Path("data/news/all_news.parquet")
    output_file = Path("data/news/news_with_sentiment.parquet")
    
    if not input_file.exists():
        print(f"✗ Error: {input_file} not found. Run 02_fetch_news.py first.")
        return
    
    print("Loading news data...")
    df = pd.read_parquet(input_file)
    
    print(f"Calculating sentiment for {len(df)} articles...")
    
    # Combine title + description
    df['text'] = (df['title'].fillna('') + ' ' + df['description'].fillna('')).str.strip()
    
    # Calculate VADER sentiment (compound score: -1 to +1)
    df['sentiment'] = df['text'].apply(lambda x: analyzer.polarity_scores(x)['compound'] if x else 0.0)
    
    # Save
    df.to_parquet(output_file)
    
    print("="*60)
    print("✓ Sentiment scoring complete!")
    print("="*60)
    print(f"  Range: [{df['sentiment'].min():.3f}, {df['sentiment'].max():.3f}]")
    print(f"  Mean:  {df['sentiment'].mean():.3f}")
    print(f"  Std:   {df['sentiment'].std():.3f}")
    print()
    print(f"  Positive (>0.05):  {(df['sentiment'] > 0.05).sum():5d} ({(df['sentiment'] > 0.05).sum()/len(df)*100:5.1f}%)")
    print(f"  Neutral  (±0.05):  {((df['sentiment'] >= -0.05) & (df['sentiment'] <= 0.05)).sum():5d} ({((df['sentiment'] >= -0.05) & (df['sentiment'] <= 0.05)).sum()/len(df)*100:5.1f}%)")
    print(f"  Negative (<-0.05): {(df['sentiment'] < -0.05).sum():5d} ({(df['sentiment'] < -0.05).sum()/len(df)*100:5.1f}%)")
    print("="*60)
    print(f"Saved to: {output_file}")

if __name__ == "__main__":
    add_sentiment()
