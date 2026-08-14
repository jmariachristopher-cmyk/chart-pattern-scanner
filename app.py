
import streamlit as st
import pandas as pd
from pattern_engine import analyze_ohlc

st.set_page_config(page_title="JMC Strict Pattern Scanner", layout="wide")
st.title("JMC Index Breakout + Strict Pattern Scanner")
st.caption("Confirmed-candle structural scanner • 5M Intraday • 1H Positional • Daily Positional")

st.sidebar.header("Scanner Settings")
min_score = st.sidebar.slider("Minimum score", 50, 100, 70, 5)

tabs = st.tabs(["Live Scanner", "Test Pattern Engine"])

with tabs[0]:
    st.subheader("INDEX BREAKOUT / BREAKDOWN")
    st.info("Live Angel One connection is the next layer. This UI is intentionally table-only; no chart is shown.")
    st.dataframe(pd.DataFrame(columns=["Index","Signal","Previous Close","LTP","Change %","Strength"]),
                 use_container_width=True, hide_index=True)

    st.subheader("STOCK FILTER — 5 MIN")
    st.dataframe(pd.DataFrame(columns=[
        "Index","Index Signal","Stock","5M Pattern","5M Dir","Score","Entry","SL","T1","T2"
    ]), use_container_width=True, hide_index=True)

    st.subheader("POSITIONAL — 1 HOUR + DAILY")
    st.dataframe(pd.DataFrame(columns=[
        "Stock","1H Pattern","1H Dir","Daily Pattern","Daily Dir","Score","Entry","SL","T1","T2"
    ]), use_container_width=True, hide_index=True)

with tabs[1]:
    st.write("Upload an OHLC CSV to verify the pattern engine before connecting live data.")
    file = st.file_uploader("CSV with Open, High, Low, Close", type=["csv"])
    if file:
        try:
            df = pd.read_csv(file)
            result = analyze_ohlc(df)
            st.write("Patterns:", ", ".join(result["patterns"]) or "None")
            st.write("Direction:", result["direction"])
            st.write("Score:", result["score"])
            st.json(result["levels"])
        except Exception as e:
            st.error(f"Pattern engine error: {e}")
