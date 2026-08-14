import time
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

import pandas as pd
import pyotp
import requests
import streamlit as st
from SmartApi import SmartConnect
from SmartApi.smartExceptions import DataException

from pattern_engine import analyze, score, levels
from index_universe import INDEX_GROUPS, INDEX_ALIASES, STOCKS_BY_INDEX

IST = ZoneInfo("Asia/Kolkata")

st.set_page_config(page_title="JMC Index Breakout + Pattern Scanner", layout="wide")
st.title("JMC Index Breakout + Pattern Scanner")
st.caption("Index breakout/breakdown → component stocks → 5M / 1H / Daily patterns • table-only stock scanner")

# Angel One historical API is rate limited. Keep requests spaced out.
MIN_REQUEST_GAP = 0.55

def _throttle():
    last = st.session_state.get("last_api_request", 0.0)
    wait = MIN_REQUEST_GAP - (time.monotonic() - last)
    if wait > 0:
        time.sleep(wait)
    st.session_state.last_api_request = time.monotonic()


with st.sidebar:
    st.header("Angel One")
    key = st.text_input("API Key", type="password")
    client = st.text_input("Client Code")
    pin = st.text_input("PIN / Password", type="password")
    secret = st.text_input("TOTP Secret", type="password")

    if st.button("Connect", type="primary"):
        try:
            if not all([key, client, pin, secret]):
                st.error("Enter API Key, Client Code, PIN/Password and TOTP Secret.")
            else:
                api = SmartConnect(api_key=key)
                login = api.generateSession(client, pin, pyotp.TOTP(secret).now())
                if login and login.get("status"):
                    st.session_state.api = api
                    st.session_state.api_error = ""
                    st.success("Connected.")
                else:
                    st.error(str(login))
        except Exception as e:
            st.error(f"Login failed: {e}")

    max_stocks = st.slider("Stocks per broken index", 5, 25, 12)
    threshold = st.slider("Minimum score", 50, 95, 70, 5)
    if st.button("Clear connection"):
        st.session_state.pop("api", None)
        st.session_state.pop("last_api_request", None)
        st.rerun()

if "api" not in st.session_state:
    st.warning("Connect Angel One first.")
    st.stop()

api = st.session_state.api

@st.cache_data(ttl=3600, show_spinner=False)
def master():
    url = "https://margincalculator.angelone.in/OpenAPI_File/files/OpenAPIScripMaster.json"
    r = requests.get(url, timeout=30)
    r.raise_for_status()
    return pd.DataFrame(r.json())

try:
    m = master()
except Exception as e:
    st.error(f"Could not load Angel One scrip master: {e}")
    st.stop()


def token(q):
    """Resolve an NSE stock/index token from the Angel One scrip master."""
    q = str(q).upper().strip()
    x = m[m["exch_seg"].astype(str).str.upper().eq("NSE")].copy()
    for c in ("name", "symbol", "tradingsymbol"):
        if c not in x.columns:
            continue
        z = x[x[c].astype(str).str.upper().str.strip().eq(q)]
        if len(z):
            return str(z.iloc[0]["token"])
    for c in ("name", "symbol", "tradingsymbol"):
        if c not in x.columns:
            continue
        z = x[x[c].astype(str).str.upper().str.strip().str.contains(q, regex=False, na=False)]
        if len(z):
            return str(z.iloc[0]["token"])
    return None


def _completed_only(d, interval):
    """Remove the currently-forming candle to keep signals non-repainting."""
    if d is None or d.empty or "datetime" not in d.columns:
        return d
    x=d.copy()
    ts=pd.to_datetime(x["datetime"], errors="coerce")
    now=datetime.now(IST)
    if interval=="FIVE_MINUTE":
        cutoff=now.replace(second=0, microsecond=0)
        cutoff=cutoff.replace(minute=(cutoff.minute//5)*5)
    elif interval=="ONE_HOUR":
        cutoff=now.replace(minute=0, second=0, microsecond=0)
    elif interval=="ONE_DAY":
        cutoff=now.replace(hour=0, minute=0, second=0, microsecond=0)
    else:
        return x
    # Angel One timestamps can be timezone-naive; compare as naive wall-clock.
    tnaive=ts.dt.tz_localize(None) if getattr(ts.dt, "tz", None) is not None else ts
    cnaive=cutoff.replace(tzinfo=None)
    return x[tnaive < cnaive].reset_index(drop=True)


def candles(t, interval, days):
    """Safe Angel One historical request. Never let a bad response crash Streamlit."""
    if not t:
        return pd.DataFrame()

    now = datetime.now(IST)
    start = now - timedelta(days=days)
    params = {
        "exchange": "NSE",
        "symboltoken": str(t),
        "interval": interval,
        "fromdate": start.strftime("%Y-%m-%d %H:%M"),
        "todate": now.strftime("%Y-%m-%d %H:%M"),
    }

    last_error = None
    for attempt in range(3):
        try:
            _throttle()
            r = api.getCandleData(params)
            if not isinstance(r, dict):
                raise RuntimeError(f"Unexpected Angel One response: {type(r).__name__}")
            if not r.get("status"):
                raise RuntimeError(r.get("message") or r.get("errorcode") or "Angel One returned status=False")
            data = r.get("data") or []
            if not data:
                return pd.DataFrame()
            d = pd.DataFrame(data, columns=["datetime", "open", "high", "low", "close", "volume"])
            for c in ["open", "high", "low", "close", "volume"]:
                d[c] = pd.to_numeric(d[c], errors="coerce")
            d["datetime"] = pd.to_datetime(d["datetime"], errors="coerce")
            d=d.dropna().reset_index(drop=True)
            return _completed_only(d, interval)
        except DataException as e:
            last_error = str(e)
            # The SDK raises DataException when the server returns HTML/non-JSON.
            # Retry after a short pause; this commonly occurs during API bursts/gateway errors.
            time.sleep(1.0 * (attempt + 1))
        except Exception as e:
            last_error = str(e)
            time.sleep(0.6 * (attempt + 1))

    st.session_state.api_error = last_error or "Unknown historical-data error"
    return pd.DataFrame()


def idx_signal(d):
    """Strict, close-confirmed index breakout/breakdown using range + ATR + volume."""
    if len(d) < 30:
        return "NO DATA"
    p=d.tail(21).iloc[:-1]
    c=d.iloc[-1]
    tr=pd.concat([(d.high-d.low),(d.high-d.close.shift(1)).abs(),(d.low-d.close.shift(1)).abs()],axis=1).max(axis=1)
    atr=float(tr.rolling(14).mean().iloc[-1] or 0)
    vavg=float(d.volume.tail(21).iloc[:-1].mean() or 0)
    if atr<=0:
        return "INSIDE"
    volume_ok=(c.volume>=vavg*1.05) if vavg>0 else True
    if c.close > p.high.max()+0.10*atr and volume_ok:
        return "BREAKOUT"
    if c.close < p.low.min()-0.10*atr and volume_ok:
        return "BREAKDOWN"
    return "INSIDE"


st.subheader("1. NSE Index Breakout / Breakdown")
idxs = []
progress = st.progress(0)
index_items = [(group, name) for group, names in INDEX_GROUPS.items() for name in names]
for i, (group, name) in enumerate(index_items):
    progress.progress((i + 1) / max(len(index_items), 1))
    t = token(INDEX_ALIASES.get(name, name))
    if not t:
        idxs.append([group, name, "TOKEN NOT FOUND"])
        continue
    d = candles(t, "FIVE_MINUTE", 3)
    idxs.append([group, name, idx_signal(d) if not d.empty else "NO DATA"])
progress.empty()

idf = pd.DataFrame(idxs, columns=["Segment", "Index", "Signal"])
st.dataframe(idf, use_container_width=True, hide_index=True)

if st.session_state.get("api_error"):
    st.warning("Some Angel One historical-data requests failed and were retried. Last API message: " + st.session_state.api_error)

broken = idf[idf.Signal.isin(["BREAKOUT", "BREAKDOWN"])]
st.subheader("2. Stocks From Broken Indices")

pairs = []
for _, row in broken.iterrows():
    for stock in STOCKS_BY_INDEX.get(row["Index"], [])[:max_stocks]:
        pairs.append((row["Index"], row["Signal"], stock))
pairs = list(dict.fromkeys(pairs))

rows = []
bar = st.progress(0)
for i, (idx, sig, stock) in enumerate(pairs):
    bar.progress((i + 1) / max(len(pairs), 1))
    t = token(stock)
    if not t:
        continue
    try:
        d5 = candles(t, "FIVE_MINUTE", 5)
        d1 = candles(t, "ONE_HOUR", 35)
        dd = candles(t, "ONE_DAY", 250)
        if d5.empty or d1.empty or dd.empty:
            continue
        a5, a1, ad = analyze(d5), analyze(d1), analyze(dd)
        sc = score(sig, a5, a1, ad)
        e, sl, t1, t2 = levels(d5, a5)
        target="BULLISH" if sig=="BREAKOUT" else "BEARISH"
        rows.append([idx, sig, stock, target, a5["pattern"], a1["pattern"], ad["pattern"], a5["direction"], a1["direction"], ad["direction"], sc, e, sl, t1, t2])
    except Exception as e:
        # One bad symbol must not stop the whole scanner.
        continue
bar.empty()

r = pd.DataFrame(rows, columns=["Index", "Index Signal", "Stock", "Setup", "5M Pattern", "1H Pattern", "Daily Pattern", "5M Dir", "1H Dir", "Daily Dir", "Score", "Entry", "SL", "T1", "T2"])

if r.empty:
    st.info("No component stock data returned for the currently broken indices.")
    st.stop()

r = r.sort_values("Score", ascending=False)
st.subheader("🔥 High-Confluence Stock Setups")

# Table-only stock scanner: pattern names are shown as text; no charts are rendered.
shown = r[(r.Score >= threshold) & (r["5M Dir"] == r["Setup"])].head(50).copy()
if shown.empty:
    st.info("No stocks meet the selected minimum score.")
else:
    st.dataframe(
        shown,
        use_container_width=True,
        hide_index=True,
        column_config={
            "Score": st.column_config.NumberColumn("Score", format="%d"),
            "Entry": st.column_config.NumberColumn("Entry", format="%.2f"),
            "SL": st.column_config.NumberColumn("SL", format="%.2f"),
            "T1": st.column_config.NumberColumn("T1", format="%.2f"),
            "T2": st.column_config.NumberColumn("T2", format="%.2f"),
        },
    )

st.caption("Stock results are table-only: no chart is displayed. Patterns are evaluated on the last completed candle for each timeframe. A stock is shown only when its 5M direction agrees with the broken-index direction and its confluence score clears the selected threshold.")
