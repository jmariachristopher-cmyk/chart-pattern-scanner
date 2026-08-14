# JMC Angel One Live Index Breakout + Pattern Scanner

This version pulls historical OHLC candles directly from Angel One SmartAPI. It does not place orders.

## Streamlit Cloud Secrets

Add these under **Settings → Secrets**:

```toml
ANGEL_API_KEY = "YOUR_API_KEY"
ANGEL_CLIENT_CODE = "YOUR_CLIENT_CODE"
ANGEL_PIN = "YOUR_PIN"
ANGEL_TOTP_SECRET = "YOUR_TOTP_SECRET"
```

Then deploy `app.py`.

## What it does
1. Logs into Angel One with TOTP.
2. Downloads the Angel One instrument master and resolves index/stock symbol tokens.
3. Scans NSE indices for confirmed close breakout/breakdown against a configurable prior-bar range.
4. Only after an index breakout/breakdown, scans the selected NSE-EQ stocks.
5. Shows 5-minute candlestick/structural patterns plus 1-hour and Daily patterns.
6. Produces entry/SL/T1/T2 levels from ATR for inspection only.

No order execution is included in this version.
