# JMC Index Breakout + Pattern Scanner v2 FIXED

Fixes:
- Historical-data errors no longer crash the app.
- Angel One candle requests are throttled to respect the documented historical API rate limit.
- Automatic retries for transient/non-JSON server responses.
- Chart panels safely handle missing candle data.
- Added websocket-client dependency required by SmartAPI.

Deploy `app.py`, `pattern_engine.py`, `index_universe.py`, and `requirements.txt`.
