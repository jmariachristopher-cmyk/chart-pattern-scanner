import json
import requests
import pandas as pd
import streamlit as st
from datetime import datetime, timedelta

try:
    import pyotp
    from SmartApi import SmartConnect
except Exception as e:
    pyotp = None
    SmartConnect = None
    IMPORT_ERROR = e
else:
    IMPORT_ERROR = None

MASTER_URL = "https://margincalculator.angelone.in/OpenAPI_File/files/OpenAPIScripMaster.json"

@st.cache_data(ttl=3600, show_spinner=False)
def load_master():
    r = requests.get(MASTER_URL, timeout=30)
    r.raise_for_status()
    data = r.json()
    return pd.DataFrame(data)

class AngelClient:
    def __init__(self, api_key, client_code, pin, totp_secret):
        if IMPORT_ERROR:
            raise RuntimeError(f"SmartAPI import failed: {IMPORT_ERROR}")
        if not all([api_key, client_code, pin, totp_secret]):
            raise ValueError("Angel One credentials are missing.")
        self.api_key = api_key.strip()
        self.client_code = client_code.strip()
        self.pin = pin.strip()
        self.totp_secret = totp_secret.strip().replace(" ", "")
        self.api = None

    def login(self):
        self.api = SmartConnect(api_key=self.api_key)
        if pyotp is None:
            raise RuntimeError("pyotp is not installed")
        totp = pyotp.TOTP(self.totp_secret).now()
        result = self.api.generateSession(self.client_code, self.pin, totp)
        if not result or result.get("status") is not True:
            raise RuntimeError(str(result))
        return result

    def candles(self, exchange, token, interval, start, end):
        if self.api is None:
            self.login()
        params = {
            "exchange": exchange,
            "symboltoken": str(token),
            "interval": interval,
            "fromdate": start.strftime("%Y-%m-%d %H:%M"),
            "todate": end.strftime("%Y-%m-%d %H:%M"),
        }
        result = self.api.getCandleData(params)
        if not result or result.get("status") is not True:
            raise RuntimeError(str(result))
        rows = result.get("data") or []
        if not rows:
            return pd.DataFrame(columns=["datetime","open","high","low","close","volume"])
        df = pd.DataFrame(rows, columns=["datetime","open","high","low","close","volume"])
        for c in ["open","high","low","close","volume"]:
            df[c] = pd.to_numeric(df[c], errors="coerce")
        df["datetime"] = pd.to_datetime(df["datetime"], errors="coerce")
        return df.dropna(subset=["open","high","low","close"]).sort_values("datetime").reset_index(drop=True)


def credentials_from_secrets():
    s = st.secrets
    return (
        s.get("ANGEL_API_KEY", ""),
        s.get("ANGEL_CLIENT_CODE", ""),
        s.get("ANGEL_PIN", ""),
        s.get("ANGEL_TOTP_SECRET", ""),
    )


def find_indices(master):
    m = master.copy()
    for c in ["token","symbol","name","exch_seg","instrumenttype"]:
        if c not in m.columns:
            m[c] = ""
    x = m[(m["exch_seg"].str.upper() == "NSE") & (m["instrumenttype"].astype(str).str.upper().isin(["AMXIDX","INDEX"]))].copy()
    x["display"] = x["symbol"].replace("", pd.NA).fillna(x["name"])
    x = x[x["display"].astype(str).str.len() > 0]
    return x[["display","name","symbol","token","exch_seg"]].drop_duplicates("token").sort_values("display")


def find_equities_all(master):
    """Return the full NSE cash-equity universe from Angel One master."""
    m = master.copy()
    for c in ["token", "symbol", "name", "exch_seg"]:
        if c not in m.columns:
            m[c] = ""
    x = m[(m["exch_seg"].astype(str).str.upper() == "NSE") &
          (m["symbol"].astype(str).str.upper().str.endswith("-EQ"))].copy()
    x["base"] = x["symbol"].astype(str).str.replace("-EQ", "", regex=False).str.upper()
    x["token"] = x["token"].astype(str)
    return x[["base", "symbol", "token", "name", "exch_seg"]].drop_duplicates("base")


def find_equities(master, symbols):
    """Backward-compatible helper for callers that still pass a symbol list."""
    x = find_equities_all(master)
    wanted = {s.strip().upper().replace("-EQ", "") for s in symbols if s.strip()}
    return x[x["base"].isin(wanted)].copy()
