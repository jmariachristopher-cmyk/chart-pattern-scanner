import streamlit as st
import pandas as pd
from pattern_engine import analyze_ohlc
st.set_page_config(page_title="JMC Strict Pattern Scanner",layout="wide")
st.title("JMC Index Breakout + Strict Pattern Scanner")
st.caption("Confirmed-candle / strict structural pattern detection. No chart images.")
st.sidebar.header("Settings")
score=st.sidebar.slider("Minimum score",50,100,70,5)
st.button("RUN SCANNER",type="primary",use_container_width=True)
st.subheader("INDEX BREAKOUT / BREAKDOWN")
st.dataframe(pd.DataFrame(columns=["Index","Signal","Move %"]),use_container_width=True,hide_index=True)
st.subheader("STOCK PATTERN SCANNER")
st.dataframe(pd.DataFrame(columns=["Index","Index Signal","Stock","5M Pattern","5M Dir","1H Pattern","1H Dir","Daily Pattern","Daily Dir","Score","Entry","SL","T1","T2"]),use_container_width=True,hide_index=True)
st.info("Connect the existing Angel One OHLC loader to this engine. A Double Top/Bottom is not reported until its neckline is confirmed.")
