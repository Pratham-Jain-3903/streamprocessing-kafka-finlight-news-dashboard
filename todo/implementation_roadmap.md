# Sentiment-Driven Trading System - Implementation Roadmap

**Project Goal:** Build end-to-end ML trading pipeline for DS portfolio  
**Status:** Phase 1 Complete (Data Collection) → Phase 2 In Progress (Optimization & Backtesting)  
**Last Updated:** 2026-02-06

---

## ✅ Phase 1: Data Collection & Initial Analysis (COMPLETE)

- [x] **Task 1.1:** Configure stock universe (Top 10 S&P 500 tech stocks)
  - Status: ✓ Complete
  - Output: `config/stock_universe.py`
  - Result: AAPL, MSFT, NVDA, GOOGL, AMZN, META, TSLA, AVGO, ORCL, AMD

- [x] **Task 1.2:** Build price data fetcher
  - Status: ✓ Complete
  - Output: `scripts/01_fetch_prices.py` + `data/prices/*.parquet`
  - Result: 15,280 price bars (10 stocks × 1,528 days, 2020-2026)

- [x] **Task 1.3:** Build news data fetcher
  - Status: ✓ Complete  
  - Output: `scripts/02_fetch_news.py` + `data/news/all_news.parquet`
  - Result: 10,000 articles from Massive API (2024-2025)
  - API: Massive/Polygon.io with 13s delays for rate limits

- [x] **Task 1.4:** Add VADER sentiment scoring
  - Status: ✓ Complete
  - Output: `scripts/03_add_sentiment.py` + `data/news/news_with_sentiment.parquet`
  - Result: Sentiment scores -1 to +1 (mean=0.433, 74.7% positive)

- [x] **Task 1.5:** Align sentiment with price returns
  - Status: ✓ Complete
  - Output: `scripts/04_correlation_analysis.py` + `data/analysis/sentiment_returns.parquet`
  - Result: 884 aligned observations (5.8% coverage)
  - Fixes: Timezone awareness, MultiIndex column flattening

- [x] **Task 1.6:** Calculate initial correlation
  - Status: ✓ Complete
  - Output: `data/analysis/correlation_summary.json`
  - Result: Overall +0.051 (weak positive), stock-specific patterns found

---

## 🔄 Phase 2: Lag Optimization & Signal Generation (IN PROGRESS)

- [🔄] **Task 2.1:** Lag analysis with parameter sweep
  - Status: 🔄 In Progress (bug fixed, re-running)
  - Script: `scripts/05_lag_analysis.py`
  - Output: `data/analysis/lag_analysis.json`
  - Configs Tested: 20 combinations per stock (5 lookback × 4 lead times)
  - Lookback Windows: 6h, 12h, 24h, 48h, 72h
  - Lead Times: 1d, 2d, 3d, 5d
  - Bug Fixed: Changed `best_corr = -999` → `best_corr = 0` (line 171)
  - Expected Results:
    - NVDA: 72h → 5d (Corr: -0.529, p=0.0016) ⭐⭐⭐
    - AAPL: 12h → 2d (Corr: -0.435, p=0.0050) ⭐⭐⭐
    - TSLA: 48h → 5d (Corr: +0.377, p=0.0059) ⭐⭐⭐
    - AMZN: 12h → 5d (Corr: -0.383, p=0.0161) ⭐⭐
    - GOOGL: 72h → 3d (Corr: +0.268, p=0.0440) ⭐⭐
    - META: 72h → 5d (Corr: -0.290, p=0.0275) ⭐⭐
    - MSFT: 24h → 1d (Corr: -0.291, p=0.0528) ⭐
    - **AVGO: WEAK (|0.05|, p>0.05) ❌ FILTER OUT**
    - **ORCL: WEAK (|0.08|, p>0.05) ❌ FILTER OUT**
    - AMD: WEAK (|0.09|, p>0.05) ❌ FILTER OUT

- [ ] **Task 2.2:** Filter weak correlations
  - Status: ⏳ Not Started (blocked by Task 2.1)
  - Script: Modify `scripts/06_strategy_signals.py`
  - Action: Add MIN_CORRELATION threshold (0.25)
  - Rationale: AVGO/ORCL/AMD have |corr| < 0.15, p-val > 0.05 → no predictive power
  - Expected: Skip signal generation for 3 stocks, focus on 7 strong signals

- [ ] **Task 2.3:** Generate trading signals
  - Status: ⏳ Not Started (blocked by Task 2.2)
  - Script: `scripts/06_strategy_signals.py`
  - Output: `data/signals/trading_signals.parquet`
  - Logic:
    - Load optimal configs from lag_analysis.json
    - Apply sentiment threshold (±0.2)
    - **Flip signal direction for inverse correlations** (7/10 stocks)
    - Generate BUY/SELL/HOLD for each trading day
  - Expected: 500-1000 signals across 7 stocks

---

## 📊 Phase 3: Backtesting & Metrics (PENDING)

- [ ] **Task 3.1:** Run backtest simulation
  - Status: ⏳ Not Started (blocked by Task 2.3)
  - Script: `scripts/07_backtest.py`
  - Output: 
    - `trades/backtest_summary_YYYYMMDD_HHMMSS.json`
    - `trades/trade_log_YYYYMMDD_HHMMSS.csv`
    - `trades/daily_equity_YYYYMMDD_HHMMSS.csv`
  - Parameters:
    - Initial Capital: $100,000
    - Position Size: 10% per trade
    - Max Positions: 5 concurrent
    - Transaction Cost: 0.1%
    - Slippage: 0.05%
    - Stop Loss: -5%
    - Take Profit: +10%
    - Hold Period: 5 days
  - Expected: 50-150 trades over backtest period

- [ ] **Task 3.2:** Calculate 34 comprehensive metrics
  - Status: ⏳ Not Started (part of Task 3.1)
  - Metrics Categories:
    - **Period:** start_date, end_date, trading_days
    - **P&L:** total_return, total_return_pct, annual_return
    - **Trade Stats:** num_trades, num_wins, num_losses, win_rate
    - **Win/Loss:** avg_win, avg_loss, largest_win, largest_loss, profit_factor, expectancy
    - **Streaks:** max_win_streak, max_loss_streak
    - **Drawdown:** max_drawdown, max_drawdown_pct, DD_start, DD_end, DD_duration
    - **Risk:** daily_volatility, annual_volatility, Sharpe, Sortino, Calmar
    - **Trade Details:** avg_days_held
  - Target Benchmarks:
    - Total Return: > 0% (beat cash)
    - Sharpe Ratio: > 1.0 (acceptable given data limits)
    - Win Rate: > 45%
    - Max Drawdown: < 15%

---

## 📈 Phase 4: Visualization & Reporting (PENDING)

- [ ] **Task 4.1:** Create equity curve visualization
  - Status: ⏳ Not Started
  - Script: `scripts/08_visualize_equity.py`
  - Library: Plotly
  - Output: `trades/equity_curve_YYYYMMDD_HHMMSS.html` + `.png`
  - Features:
    - Daily equity line chart
    - Benchmark comparison (buy-and-hold S&P 500 or equal-weighted portfolio)
    - Trade entry/exit markers
    - Drawdown shading
  - Interactive: Hover tooltips, zoom, pan

- [ ] **Task 4.2:** Create drawdown chart
  - Status: ⏳ Not Started
  - Script: `scripts/09_visualize_drawdown.py`
  - Library: Plotly
  - Output: `trades/drawdown_chart_YYYYMMDD_HHMMSS.html` + `.png`
  - Features:
    - Underwater equity curve (% from peak)
    - Max drawdown annotation
    - Recovery periods highlighted
    - Duration labels

- [ ] **Task 4.3:** Create monthly returns heatmap
  - Status: ⏳ Not Started
  - Script: `scripts/10_visualize_heatmap.py`
  - Library: Plotly
  - Output: `trades/monthly_heatmap_YYYYMMDD_HHMMSS.html` + `.png`
  - Features:
    - Rows = years, Columns = months
    - Color scale: red (losses) → green (gains)
    - Annotations with exact %
    - Annual summary column

- [ ] **Task 4.4:** Create trade distribution analysis
  - Status: ⏳ Not Started
  - Script: `scripts/11_visualize_trades.py`
  - Library: Plotly
  - Output: `trades/trade_analysis_YYYYMMDD_HHMMSS.html` + `.png`
  - Charts:
    - P&L histogram (distribution of returns)
    - Win/loss bar chart by ticker
    - Days held distribution
    - Exit reason pie chart

---

## 🎯 Phase 5: Master Report & Final Validation (PENDING)

- [ ] **Task 5.1:** Build master report script
  - Status: ⏳ Not Started
  - Script: `app/report.py`
  - Purpose: Single command to generate full report
  - Flow:
    1. Check data dependencies (prices, news, signals)
    2. Run backtest if not already run
    3. Generate all visualizations
    4. Compile HTML report with embedded charts
    5. Export PDF summary
  - Usage: `python3 app/report.py [--backtest-file trades/backtest_summary_*.json]`
  - Output: `reports/full_report_YYYYMMDD.html` + `.pdf`

- [ ] **Task 5.2:** Create executive summary
  - Status: ⏳ Not Started
  - Document: `reports/executive_summary.md`
  - Contents:
    - Project overview (1 paragraph)
    - Key findings (3-5 bullet points)
    - Performance metrics table
    - Best/worst trades highlight
    - Recommendations for improvement
    - Data science methodology notes

- [ ] **Task 5.3:** Final validation checklist
  - Status: ⏳ Not Started
  - Verify:
    - [ ] All data files present and non-empty
    - [ ] Backtest results make logical sense (no arithmetic errors)
    - [ ] Sharpe ratio matches manual calculation
    - [ ] Trade log sums to total P&L
    - [ ] Visualizations render correctly
    - [ ] No placeholder/TODO comments in code
    - [ ] README.md updated with usage instructions

- [ ] **Task 5.4:** GitHub repository preparation
  - Status: ⏳ Not Started
  - Actions:
    - [ ] Write comprehensive README.md
    - [ ] Add requirements.txt with pinned versions
    - [ ] Create .gitignore (exclude data/*, .venv/, credentials)
    - [ ] Add LICENSE file (MIT suggested)
    - [ ] Write docs/SETUP.md (environment setup)
    - [ ] Write docs/USAGE.md (script execution order)
    - [ ] Add sample outputs in docs/examples/
    - [ ] Tag release v1.0.0

---

## 📦 Deliverables Checklist

### Code Artifacts
- [x] `config/stock_universe.py` - Central configuration
- [x] `scripts/01_fetch_prices.py` - Price data collection
- [x] `scripts/02_fetch_news.py` - News data collection
- [x] `scripts/03_add_sentiment.py` - VADER sentiment scoring
- [x] `scripts/04_correlation_analysis.py` - Initial correlation
- [🔄] `scripts/05_lag_analysis.py` - Parameter optimization (running)
- [ ] `scripts/06_strategy_signals.py` - Signal generation (needs weak filter)
- [ ] `scripts/07_backtest.py` - Backtest simulation
- [ ] `scripts/08_visualize_equity.py` - Equity curve chart
- [ ] `scripts/09_visualize_drawdown.py` - Drawdown chart
- [ ] `scripts/10_visualize_heatmap.py` - Monthly returns heatmap
- [ ] `scripts/11_visualize_trades.py` - Trade distribution analysis
- [ ] `app/report.py` - Master report generator

### Data Artifacts
- [x] `data/prices/*.parquet` (10 files, 15,280 bars)
- [x] `data/news/all_news.parquet` (10,000 articles)
- [x] `data/news/news_with_sentiment.parquet` (with VADER scores)
- [x] `data/analysis/sentiment_returns.parquet` (884 observations)
- [x] `data/analysis/correlation_summary.json`
- [🔄] `data/analysis/lag_analysis.json` (generating)
- [ ] `data/signals/trading_signals.parquet`
- [ ] `trades/backtest_summary_*.json`
- [ ] `trades/trade_log_*.csv`
- [ ] `trades/daily_equity_*.csv`

### Visualization Artifacts
- [ ] `trades/equity_curve_*.html` + `.png`
- [ ] `trades/drawdown_chart_*.html` + `.png`
- [ ] `trades/monthly_heatmap_*.html` + `.png`
- [ ] `trades/trade_analysis_*.html` + `.png`
- [ ] `reports/full_report_*.html` + `.pdf`

### Documentation Artifacts
- [ ] `README.md` - Project overview
- [ ] `docs/SETUP.md` - Environment setup
- [ ] `docs/USAGE.md` - Script execution guide
- [ ] `docs/METHODOLOGY.md` - Data science approach
- [ ] `reports/executive_summary.md` - Key findings
- [x] `todo/implementation_roadmap.md` - This file

---

## 🚨 Known Issues & Risks

### Issue 1: Weak News Coverage (5.8%)
- **Problem:** Only 884/15,280 days (5.8%) have ≥3 articles
- **Impact:** Limited backtest data, high variance in metrics
- **Mitigation:** Document limitation, consider reducing MIN_NEWS_COUNT to 2
- **Status:** Accepted risk, will document in final report

### Issue 2: Positive Sentiment Bias (74.7%)
- **Problem:** VADER scores 74.7% of articles as positive
- **Root Cause:** VADER not optimized for financial news (trained on social media)
- **Impact:** May miss negative sentiment signals
- **Mitigation:** Note for future improvement (switch to FinBERT)
- **Status:** Accepted risk, contrarian strategy may benefit

### Issue 3: Inverse Correlations Dominate (7/10 stocks)
- **Problem:** Most stocks show negative correlation (sentiment ↑ → returns ↓)
- **Interpretation:** Contrarian indicator (positive news = overbought?)
- **Impact:** Strategy must flip signals for inverse correlations
- **Mitigation:** Implemented in signal generator (correlation sign check)
- **Status:** ✓ Resolved

### Issue 4: AVGO/ORCL/AMD Weak Signals
- **Problem:** Correlation < 0.15, p-value > 0.05 (not significant)
- **Impact:** Would generate noisy signals, hurt win rate
- **Mitigation:** Filter out before signal generation (Task 2.2)
- **Status:** ⏳ Planned

### Issue 5: Massive API Rate Limits
- **Problem:** Free tier limited to ~5 req/min (429 errors)
- **Impact:** 10,000 articles took 35+ minutes to fetch
- **Mitigation:** Used time.sleep(13) between calls
- **Status:** ✓ Resolved

---

## 🎓 Data Science Methodology Notes

### Feature Engineering
- **Temporal Aggregation:** 6h-72h lookback windows for sentiment
- **Forward-Looking Labels:** 1d-5d future returns
- **Minimum Data Quality:** 3+ articles per day, 30+ observations for correlation

### Model Selection
- **Approach:** Correlation-based threshold strategy (non-ML baseline)
- **Rationale:** Establish baseline before complex models (LSTM, Transformer)
- **Future Enhancement:** Gradient boosting, LSTM seq2seq, Transformer attention

### Validation Strategy
- **Walk-Forward:** Backtest on 2024-2026 data
- **No Look-Ahead Bias:** Sentiment aggregated only from past news
- **Transaction Costs:** 0.1% + 0.05% slippage (realistic)

### Evaluation Metrics
- **Risk-Adjusted:** Sharpe, Sortino, Calmar ratios
- **Robustness:** Streaks, profit factor, expectancy
- **Transparency:** Per-trade log for reproducibility

---

## 📅 Timeline Estimate

- **Phase 1 (Data Collection):** ✓ Complete (5 hours actual)
- **Phase 2 (Optimization):** 🔄 In Progress (1 hour estimated)
- **Phase 3 (Backtesting):** ⏳ Pending (30 minutes estimated)
- **Phase 4 (Visualization):** ⏳ Pending (2 hours estimated)
- **Phase 5 (Reporting):** ⏳ Pending (1 hour estimated)

**Total:** ~9.5 hours | **Completed:** ~5.5 hours (58%) | **Remaining:** ~4 hours

---

## 🔗 Dependencies

```
pandas>=2.0.0
numpy>=1.24.0
yfinance>=0.2.28
vaderSentiment>=3.3.2
scipy>=1.11.0
pyarrow>=13.0.0
plotly>=5.17.0
kaleido>=0.2.1  # For static image export
requests>=2.31.0
```

---

**End of Roadmap** | Last Updated: 2026-02-06 | Status: Phase 2 In Progress
