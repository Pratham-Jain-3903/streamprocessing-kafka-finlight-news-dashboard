"""Stock universe and configuration for sentiment trading strategy."""

# Top 10 S&P 500 Tech Stocks by Market Cap
TOP_10_TECH_STOCKS = [
    "AAPL",   # Apple Inc.
    "MSFT",   # Microsoft Corporation
    "NVDA",   # NVIDIA Corporation
    "GOOGL",  # Alphabet Inc.
    "AMZN",   # Amazon.com Inc.
    "META",   # Meta Platforms Inc.
    "TSLA",   # Tesla Inc.
    "AVGO",   # Broadcom Inc.
    "ORCL",   # Oracle Corporation
    "AMD",    # Advanced Micro Devices
]

# Date ranges
HISTORICAL_START = "2020-01-01"
BACKTEST_START = "2024-01-01"
BACKTEST_END = "2026-01-31"

# Strategy parameters (to be optimized)
SENTIMENT_THRESHOLD = 0.4
LOOKBACK_HOURS = 24
MIN_NEWS_COUNT = 7
HOLD_PERIOD_HOURS = 2400
STOP_LOSS_PCT = 0.05
TAKE_PROFIT_PCT = 0.2

# Target metrics
TARGET_SHARPE = 1.5              # Target Sharpe ratio > 1.5
TARGET_MAX_DRAWDOWN = 0.15       # Max drawdown < 15%
TARGET_ALPHA = 0.05              # Alpha > 5% annualized
TARGET_WIN_RATE = 0.55           # Win rate > 55%
