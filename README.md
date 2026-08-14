# JMC Index Breakout + Pattern Scanner v4

## What this version does
- Scans NSE indices across Broad, Major, Sectoral and Thematic groups.
- Uses the **last completed 5-minute candle** for index breakout/breakdown confirmation.
- Requires a range break plus ATR and volume confirmation to reduce false index signals.
- When an index breaks out/breaks down, scans its mapped component stocks.
- Shows stocks in a **table only** — no chart is embedded in the scanner.
- For every selected stock, shows:
  - Index / Index Signal
  - Setup direction
  - 5M Pattern
  - 1H Pattern
  - Daily Pattern
  - 5M / 1H / Daily Direction
  - Confluence Score
  - Entry / SL / T1 / T2
- Detects candle patterns including Bullish/Bearish Engulfing, Morning Star, Evening Star and Doji.
- Detects confirmed/structured chart patterns including Head & Shoulders, Inverse Head & Shoulders, Double Top/Bottom, Triangles, Wedges, Flags/Pennants and Cup & Handle where the data supports confirmation.
- A stock is displayed only when its 5M direction agrees with the broken-index direction and its score clears the selected threshold.
- Historical-data failures are retried and isolated so one bad symbol does not stop the scanner.

## Important
No scanner can be guaranteed 100% accurate. This version is intentionally more selective and uses completed candles and multi-timeframe confluence to reduce false positives rather than claiming certainty.

## Deploy
Upload all files in this folder to Streamlit Cloud and use `app.py` as the main file.
