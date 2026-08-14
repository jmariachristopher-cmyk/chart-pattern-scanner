
import numpy as np
import pandas as pd

def _pivots(df, left=3, right=3):
    hi = df["high"].to_numpy(dtype=float)
    lo = df["low"].to_numpy(dtype=float)
    ph, pl = [], []
    for i in range(left, len(df)-right):
        if hi[i] >= np.max(hi[i-left:i+right+1]):
            ph.append(i)
        if lo[i] <= np.min(lo[i-left:i+right+1]):
            pl.append(i)
    return ph, pl

def _candle_patterns(df):
    if len(df) < 3:
        return []
    a, b, c = df.iloc[-1], df.iloc[-2], df.iloc[-3]
    out = []
    ar = max(float(a["high"]-a["low"]), 1e-9)
    ab = abs(float(a["close"]-a["open"]))
    if a["close"] > a["open"] and b["close"] < b["open"] and a["open"] <= b["close"] and a["close"] >= b["open"]:
        out.append("Bullish Engulfing")
    if a["close"] < a["open"] and b["close"] > b["open"] and a["open"] >= b["close"] and a["close"] <= b["open"]:
        out.append("Bearish Engulfing")
    if ab/ar <= 0.10:
        out.append("Doji")
    cb = abs(float(c["close"]-c["open"]))
    bb = abs(float(b["close"]-b["open"]))
    if c["close"] < c["open"] and bb <= cb*0.5 and a["close"] > a["open"] and a["close"] > (c["open"]+c["close"])/2:
        out.append("Morning Star")
    if c["close"] > c["open"] and bb <= cb*0.5 and a["close"] < a["open"] and a["close"] < (c["open"]+c["close"])/2:
        out.append("Evening Star")
    return out

def _double_top(df, tolerance=0.012, min_sep=5):
    ph, pl = _pivots(df)
    if len(ph) < 2: return False
    p1, p2 = ph[-2], ph[-1]
    if p2-p1 < min_sep: return False
    h1, h2 = float(df["high"].iloc[p1]), float(df["high"].iloc[p2])
    if abs(h1-h2)/max((h1+h2)/2,1e-9) > tolerance: return False
    valleys = [i for i in pl if p1 < i < p2]
    if not valleys: return False
    neck = min(float(df["low"].iloc[i]) for i in valleys)
    if (min(h1,h2)-neck)/min(h1,h2) < 0.01: return False
    return float(df["close"].iloc[-1]) < neck

def _double_bottom(df, tolerance=0.012, min_sep=5):
    ph, pl = _pivots(df)
    if len(pl) < 2: return False
    p1, p2 = pl[-2], pl[-1]
    if p2-p1 < min_sep: return False
    l1, l2 = float(df["low"].iloc[p1]), float(df["low"].iloc[p2])
    if abs(l1-l2)/max((l1+l2)/2,1e-9) > tolerance: return False
    peaks = [i for i in ph if p1 < i < p2]
    if not peaks: return False
    neck = max(float(df["high"].iloc[i]) for i in peaks)
    if (neck-max(l1,l2))/neck < 0.01: return False
    return float(df["close"].iloc[-1]) > neck

def _head_shoulders(df, inverse=False, tolerance=0.025):
    ph, pl = _pivots(df)
    pts = pl if inverse else ph
    if len(pts) < 3: return False
    a,b,c = pts[-3],pts[-2],pts[-1]
    if inverse:
        x,y,z = float(df["low"].iloc[a]),float(df["low"].iloc[b]),float(df["low"].iloc[c])
        if not (y < x and y < z): return False
        if abs(x-z)/max((x+z)/2,1e-9) > tolerance: return False
        mids=[i for i in ph if a<i<c]
        if len(mids)<2:return False
        neck=max(float(df["high"].iloc[i]) for i in mids[-2:])
        return float(df["close"].iloc[-1]) > neck
    x,y,z = float(df["high"].iloc[a]),float(df["high"].iloc[b]),float(df["high"].iloc[c])
    if not (y > x and y > z): return False
    if abs(x-z)/max((x+z)/2,1e-9) > tolerance: return False
    mids=[i for i in pl if a<i<c]
    if len(mids)<2:return False
    neck=min(float(df["low"].iloc[i]) for i in mids[-2:])
    return float(df["close"].iloc[-1]) < neck

def analyze_ohlc(df):
    if df is None or len(df) < 40:
        return {"patterns":[],"direction":"NEUTRAL","score":0,"levels":{}}
    d = df.copy()
    d.columns = [str(c).lower() for c in d.columns]
    required={"open","high","low","close"}
    if not required.issubset(d.columns):
        raise ValueError("OHLC data must contain open, high, low, close columns")
    d=d.dropna(subset=["open","high","low","close"]).reset_index(drop=True)
    patterns=_candle_patterns(d)
    if _double_top(d): patterns.append("Double Top")
    if _double_bottom(d): patterns.append("Double Bottom")
    if _head_shoulders(d): patterns.append("Head & Shoulders")
    if _head_shoulders(d, True): patterns.append("Inverse Head & Shoulders")

    ph,pl=_pivots(d)
    if len(ph)>=2 and len(pl)>=2:
        higher_high=float(d["high"].iloc[ph[-1]])>float(d["high"].iloc[ph[-2]])
        lower_high=not higher_high
        higher_low=float(d["low"].iloc[pl[-1]])>float(d["low"].iloc[pl[-2]])
        lower_low=not higher_low
        if higher_high and higher_low: patterns.append("Rising Structure")
        if lower_high and lower_low: patterns.append("Falling Structure")
        if abs(float(d["high"].iloc[ph[-1]])-float(d["high"].iloc[ph[-2]]))/max(float(d["high"].iloc[ph[-2]]),1e-9)<0.01 and higher_low:
            patterns.append("Ascending Triangle")
        if abs(float(d["low"].iloc[pl[-1]])-float(d["low"].iloc[pl[-2]]))/max(float(d["low"].iloc[pl[-2]]),1e-9)<0.01 and lower_low:
            patterns.append("Descending Triangle")
    patterns=list(dict.fromkeys(patterns))

    bullish={"Bullish Engulfing","Morning Star","Double Bottom","Inverse Head & Shoulders","Ascending Triangle","Rising Structure"}
    bearish={"Bearish Engulfing","Evening Star","Double Top","Head & Shoulders","Descending Triangle","Falling Structure"}
    b=sum(x in bullish for x in patterns); s=sum(x in bearish for x in patterns)
    direction="BULLISH" if b>s else "BEARISH" if s>b else "NEUTRAL"
    score=min(100,50+15*max(b,s)+10*max(0,len(patterns)-1))
    tr=np.maximum(d["high"]-d["low"],np.maximum(abs(d["high"]-d["close"].shift()),abs(d["low"]-d["close"].shift())))
    atr=float(tr.rolling(14).mean().iloc[-1])
    entry=float(d["close"].iloc[-1])
    if direction=="BULLISH":
        sl=entry-atr; t1=entry+1.5*atr; t2=entry+2.5*atr
    elif direction=="BEARISH":
        sl=entry+atr; t1=entry-1.5*atr; t2=entry-2.5*atr
    else:
        sl=t1=t2=float("nan")
    return {"patterns":patterns,"direction":direction,"score":int(score),
            "levels":{"entry":entry,"sl":sl,"t1":t1,"t2":t2}}
