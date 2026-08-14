# JMC Index Breakout + Pattern Scanner v1

Separate analysis-only Streamlit app.

Flow: NSE index 5-minute breakout/breakdown -> component stocks -> 5M/1H/Daily candlestick + chart patterns -> confluence score -> entry/SL/T1/T2 reference levels -> chart.

Run locally:

python -m venv .venv
.venv\\Scripts\\Activate.ps1
pip install -r requirements.txt
streamlit run app.py

No orders are placed.

The index-to-stock universe is a practical editable mapping. For production, it should be refreshed from official index constituent data because membership changes. Pattern detection is rule-based/heuristic and is not a guarantee of future returns.
