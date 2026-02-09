# News API Integration

This directory contains adapters and probe scripts for fetching financial news from multiple providers.

## Supported APIs

### 1. Finlight API
- **Endpoint**: `https://api.finlight.me/v2/articles`
- **Documentation**: https://api.finlight.me/docs
- **Method**: POST with JSON body
- **Key features**: Query-based filtering, source filtering, good rate limits

### 2. Massive API (formerly Polygon.io)
- **Endpoint**: `https://api.massive.com/v2/reference/news`
- **Documentation**: https://massive.com/docs/rest/stocks/news
- **Method**: GET with query params
- **Key features**: Ticker-based filtering, structured metadata
- **Limitation**: Free tier has very strict rate limits (~5 req/min)

## Files

```
ingestion/
├── finlight_api.py      # (existing) Finlight API adapter
├── massive_api.py       # NEW: Massive API adapter
scripts/
├── finlight_find_first_article.py   # Finlight-only probe script
├── probe_news_api.py                # NEW: Multi-provider probe script
docs/
├── massive_api_evaluation.txt       # Massive API evaluation & comparison
```

## Quick Start

### Test Massive API
```bash
# Fetch last 7 days of AAPL news
python3 ingestion/massive_api.py

# Find earliest article for ticker AMX (2020-2026)
python3 scripts/probe_news_api.py \
  --provider massive \
  --ticker AMX \
  --start 2020-01-01 \
  --end 2026-01-01 \
  --out logs/massive_amx_earliest.json
```

### Test Finlight API
```bash
# Find earliest article for ticker:NVDA (2020-2026)
python3 scripts/finlight_find_first_article.py \
  --start 2020-01-01 \
  --end 2026-01-01 \
  --query "ticker:NVDA" \
  --sources "*" \
  --out logs/finlight_nvda_earliest.json

# Or use the unified probe script
python3 scripts/probe_news_api.py \
  --provider finlight \
  --query "ticker:NVDA" \
  --sources "*" \
  --start 2020-01-01 \
  --end 2026-01-01 \
  --out logs/finlight_nvda_earliest.json
```

## Configuration

Set API keys via environment variables:

```bash
export FINLIGHT_API_KEY="sk_..."
export MASSIVE_API_KEY="..."
```

Or configure in `.env`:

```env
FINLIGHT_API_KEY=sk_621d88dfcc31a1d3efa89a2873d394563f53bfd6fe1c7aec2ffd22e45d7b1d44
MASSIVE_API_KEY=rsoLbE3CQLL2pVXvbEpsjeqMBYtSFTp0
```

## Probe Strategy

Both probe scripts use **exponential forward search + binary search**:

1. Start at `start_date`
2. If no data, jump forward exponentially (1, 2, 4, 8, ..., 30 days)
3. When a date with data is found, binary-search backward to find the earliest date
4. Output: JSON file with earliest date found

**Efficiency**: ~10-15 API calls to search a 6-year range (vs. 2190+ for linear search)

## Rate Limits & Best Practices

### Finlight API
- ✓ High/no rate limits observed on free tier
- ✓ Good for high-volume probing
- ⚠️ No official rate limit documentation; monitor for 429 responses

### Massive API (Free Tier)
- ⚠️ **Very strict**: ~5 requests/min
- 💡 Add 12-15s delay between requests to avoid 429 errors
- 💰 Consider Starter tier ($49/mo, 100 req/min) for production

## Next Steps

1. **Probe historical coverage** for your target tickers (e.g., AMX, AAPL, NVDA) on both APIs
2. **Compare results**: article counts, date ranges, quality
3. **Choose provider** based on:
   - Historical coverage needs (2020-2026 for backtest)
   - Rate limits / budget
   - Data quality and source diversity
4. **Implement producer** to fetch and publish articles to Kafka

See `docs/massive_api_evaluation.txt` for detailed comparison and recommendations.
