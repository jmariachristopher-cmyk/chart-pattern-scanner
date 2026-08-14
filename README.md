# JMC Angel One Live Index Breakout → Stock Pattern Scanner

This version uses Angel One SmartAPI historical OHLC data and automatically loads the NSE cash-equity universe from the Angel One instrument master.

## Important
- No manual `Stocks to scan (comma separated)` field.
- All NSE-EQ symbols are loaded automatically.
- The scanner first checks all available NSE index instruments for breakout/breakdown.
- Only after an index breaks out/breaks down does it scan stocks.
- Stocks are first checked on 5-minute candles; 1-hour and Daily pattern checks are performed only for 5M candidates that pass the score/direction filter.
- No order execution is included.

## Streamlit Secrets

```toml
ANGEL_API_KEY = "..."
ANGEL_CLIENT_CODE = "..."
ANGEL_PIN = "..."
ANGEL_TOTP_SECRET = "..."
```

Never commit real credentials to GitHub.
