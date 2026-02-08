"""
Module for ingesting stock data from an external API.
to be integrated with existing state management code (producer.py)
the api responses are grouped into eight categories: 
    (1) Core Time Series Stock Data APIs, 
    (2) US Options Data APIs, 
    (3) Alpha Intelligence™, 
    (4) Fundamental Data, 
    (5) Physical and Crypto Currencies (e.g., Bitcoin), 
    (6) Commodities, 
    (7) Economic Indicators, and 
    (8) Technical Indicators
It supports over 200,000 stock tickers across 20+ global exchanges, offering comprehensive OHLCV (Open, High, Low, Close, Volume) data with low latency. With more than two decades of historical coverage, the API is well-suited for building tools such as fintech LLM agents, trading algorithms, and financial charting applications.
"""
