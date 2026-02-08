# News Sentiment Trading Strategy & Backtesting Platform

A quantitative trading system that combines news sentiment analysis with correlation-based strategies to generate trading signals for technology stocks. The platform ingests historical news data, performs sentiment analysis, identifies optimal lag parameters, and backtests trading strategies with comprehensive risk metrics.

## 🎯 System Overview

```
📡 Polygon.io API (Massive News)
   │
   ▼
📰 News Ingestion (Batch Processing)
   ├── Yearly batches for large date ranges
   ├── Merge with existing data
   ├── Deduplication by article URL/ID
   ├── Output: data/news/all_news.parquet
   │
   ▼
🧠 Sentiment Analysis (VADER)
   ├── Score each article: compound, pos, neg, neu
   ├── Aggregate by ticker + day
   ├── Output: data/news/news_with_sentiment.parquet
   │
   ▼
🔬 Statistical Analysis
   ├── Lag Analysis: Test 200 configs per stock
   │   └── Find optimal lookback/lead times
   ├── Correlation Analysis: 1d/3d/5d horizons
   │   └── Identify inverse vs direct strategies
   ├── Output: data/analysis/*.json
   │
   ▼
📈 Signal Generation
   ├── Apply optimal lag configs per stock
   ├── Use sentiment thresholds + correlation filters
   ├── Generate BUY/SELL/HOLD signals
   ├── Output: data/trades/trading_signals.parquet
   │
   ▼
💼 Backtesting Engine
   ├── Realistic transaction costs ($1/trade)
   ├── Stop-loss & take-profit exits
   ├── Hold period constraints
   ├── 34 comprehensive metrics
   ├── Output: trades/*.json, trades/*.html
   │
   ▼
📊 Interactive Dashboard (Plotly Dash)
   ├── 6 Dynamic Tabs: Results, Equity, Heatmap, etc.
   ├── 3 Static Tabs: Lag Analysis, Correlation, Data
   └── Real-time parameter tuning & visualization
```

## 📂 Project Structure

```
data-ingestion/
├── app/
│   ├── experiment.py        # Plotly Dash dashboard (9 tabs)
│   ├── dashboard.html       # Static HTML export
│   └── main.py              # FastAPI service (legacy)
├── config/
│   └── stock_universe.py    # 6 configurable strategy parameters
├── scripts/
│   ├── 01_data_collection.py      # Historical price data (Polygon.io)
│   ├── 02_fetch_news.py           # Batch news fetching with merge logic
│   ├── 03_sentiment_analysis.py   # VADER sentiment scoring
│   ├── 04_lag_analysis.py         # Optimal lookback/lead optimization
│   ├── 05_correlation_summary.py  # Multi-horizon correlation analysis
│   ├── 06_strategy_signals.py     # Signal generation with filters
│   └── 07_backtest.py             # Backtesting with 34 metrics
├── data/
│   ├── news/                # all_news.parquet, news_with_sentiment.parquet
│   ├── analysis/            # lag_analysis.json, correlation_summary.json
│   ├── prices/              # {TICKER}_1d_prices.parquet (OHLCV)
│   └── trades/              # trading_signals.parquet, backtest results
├── ingestion/
│   ├── producer.py          # Kafka producer (for streaming mode)
│   ├── finlight_api.py      # Finlight API wrapper
│   └── stocks_api.py        # Stock price fetcher
├── docker-compose.yml       # Kafka, Postgres, DuckDB services
├── requirements.txt         # Python dependencies
└── README.md
```

## 🚀 Quick Start

### 1. Setup Environment
```bash
python3 -m venv .venv
source .venv/bin/activate  # or .venv\Scripts\activate on Windows
pip install -r requirements.txt
```

### 2. Configure API Keys
Add your Polygon.io API key to `config/stock_universe.py`:
```python
POLYGON_API_KEY = "your_api_key_here"
```

### 3. Run Data Pipeline
```bash
# Fetch historical prices (2024-01-01 to 2026-01-31)
python scripts/01_data_collection.py

# Fetch news articles in yearly batches (~6.5 min for 3 years × 10 stocks)
python scripts/02_fetch_news.py

# Score sentiment with VADER
python scripts/03_sentiment_analysis.py

# Optimize lag parameters (200 configs per stock)
python scripts/04_lag_analysis.py

# Compute multi-horizon correlations
python scripts/05_correlation_summary.py
```

### 4. Launch Dashboard
```bash
python app/experiment.py
# Open http://localhost:8050 in browser
# Adjust parameters → Click "Run Backtest" → Explore 9 tabs
```

## 🎛️ Configurable Parameters

All strategy parameters are centralized in `config/stock_universe.py`:

| Parameter | Default | Range | Description |
|-----------|---------|-------|-------------|
| `SENTIMENT_THRESHOLD` | 0.2 | 0.0-0.5 | Minimum avg sentiment to trigger signal |
| `MIN_NEWS_COUNT` | 3 | 1-10 | Minimum articles required per day |
| `HOLD_PERIOD_HOURS` | 240 (10d) | 24-240 | Maximum position duration |
| `STOP_LOSS_PCT` | 0.02 (2%) | 0.01-0.10 | Exit if loss exceeds threshold |
| `TAKE_PROFIT_PCT` | 0.05 (5%) | 0.02-0.20 | Exit if profit exceeds threshold |
| `LOOKBACK_HOURS` | 24 | N/A | Pre-optimized per stock (see lag analysis) |

**Note:** Change parameters in config file OR via dashboard sliders. Dashboard "Run Backtest" button re-runs scripts 06 & 07 with selected values.

## 📊 Dashboard Features

### Dynamic Tabs (Parameter-Dependent)
1. **📋 Performance Metrics** — 34 comprehensive metrics (Sharpe, Sortino, Calmar, max drawdown, win rate, expectancy)
2. **📈 Equity Curve** — Initial $100K → Final equity visualization with drawdown shading
3. **🔥 Heatmap** — Daily returns color-coded by performance
4. **📉 Drawdown** — Peak-to-trough analysis over time
5. **📊 Trade Distribution** — Daily P&L histogram with win/loss breakdown
6. **📋 Trade Log** — Full trade history with entry/exit prices, P&L, hold days

### Static Tabs (Research Foundation)
7. **🔬 Lag Analysis** — 200 tested configs per stock, optimal lookback/lead times, correlation strengths
8. **📊 Correlation** — Sentiment-return relationships at 1d/3d/5d horizons
9. **💾 Data Summary** — 10,000 articles, date coverage, sentiment distribution, analysis status

## 🧪 Key Findings

### Lag Analysis Results
- **NVDA:** -0.529 correlation (strongest inverse), 72h lookback, 1d lead
- **AAPL:** -0.435 correlation (inverse), 48h lookback, 1d lead
- **TSLA:** +0.377 correlation (direct), 72h lookback, 1d lead
- **GOOGL:** +0.268 correlation (direct), 24h lookback, 1d lead

### Backtest Performance (Default Params)
- **Period:** 2024-01-02 to 2026-01-30 (522 trading days)
- **Total Trades:** 64 (30 wins, 34 losses)
- **Win Rate:** 46.9%
- **Total Return:** -1.14% (-$1,143.01)
- **Sharpe Ratio:** -0.08
- **Max Drawdown:** -7.72%

## 🔧 Technical Stack

- **Language:** Python 3.13
- **Data Ingestion:** Polygon.io API (5 req/min rate limit)
- **Sentiment Analysis:** VADER (vaderSentiment library)
- **Dashboard:** Plotly Dash with interactive callbacks
- **Data Storage:** Parquet (news, prices, signals), JSON (analysis results)
- **Statistical Analysis:** Pandas, NumPy, SciPy
- **Visualization:** Plotly Express, Matplotlib

## 📝 Pipeline Execution Order

**Full Pipeline (First Run):**
```bash
01_data_collection → 02_fetch_news → 03_sentiment_analysis → 
04_lag_analysis → 05_correlation_summary → 
06_strategy_signals → 07_backtest
```

**Parameter Tuning (Dashboard):**
```bash
# Dashboard "Run Backtest" button runs:
06_strategy_signals → 07_backtest
# Then refreshes visualizations automatically
```

**Adding New Data:**
```bash
02_fetch_news → 03_sentiment_analysis → [Dashboard "Run Backtest"]
```

## 🎓 Strategy Logic

1. **News Collection:** Fetch articles for 10 FAANG stocks (AAPL, MSFT, GOOGL, AMZN, TSLA, NVDA, META, NFLX, AVGO, ORCL)
2. **Sentiment Scoring:** VADER compound scores (-1.0 to +1.0)
3. **Aggregation:** Average sentiment per ticker per day (requires MIN_NEWS_COUNT articles)
4. **Lag Application:** Use stock-specific optimal lookback windows
5. **Signal Generation:**
   - BUY: Sentiment > threshold, positive correlation exists
   - SELL: Sentiment > threshold, negative correlation exists (inverse strategy)
   - HOLD: Sentiment below threshold or insufficient news
6. **Exits:** Stop-loss, take-profit, or hold period expiration
7. **Metrics:** 34-metric evaluation including risk-adjusted returns

## 📚 Additional Resources

- **Lag Analysis:** `data/analysis/lag_analysis.json` (200 configs tested)
- **Correlations:** `data/analysis/correlation_summary.json` (884 observations)
- **Trade Logs:** `data/trades/trade_log.csv` (all trades with timestamps)
- **Dashboard Export:** `app/dashboard.html` (static snapshot)


