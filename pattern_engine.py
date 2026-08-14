import numpy as np
import pandas as pd

BULLISH = {
    'Bullish Engulfing', 'Morning Star', 'Double Bottom',
    'Inverse Head & Shoulders', 'Ascending Triangle', 'Falling Wedge',
    'Bull Flag', 'Bull Pennant', 'Cup & Handle'
}
BEARISH = {
    'Bearish Engulfing', 'Evening Star', 'Double Top',
    'Head & Shoulders', 'Descending Triangle', 'Rising Wedge',
    'Bear Flag', 'Bear Pennant'
}


def _clean(d):
    if d is None or len(d) == 0:
        return pd.DataFrame()
    x = d.copy()
    cols = ['open', 'high', 'low', 'close', 'volume']
    for c in cols:
        if c in x:
            x[c] = pd.to_numeric(x[c], errors='coerce')
    return x.dropna(subset=['open', 'high', 'low', 'close']).reset_index(drop=True)


def body(c):
    return abs(float(c.close) - float(c.open))


def rng(c):
    return max(float(c.high) - float(c.low), 1e-9)


def bull(c):
    return float(c.close) > float(c.open)


def bear(c):
    return float(c.close) < float(c.open)


def _atr(x, n=14):
    h, l, c = x.high, x.low, x.close
    tr = pd.concat([(h-l), (h-c.shift(1)).abs(), (l-c.shift(1)).abs()], axis=1).max(axis=1)
    return tr.rolling(n).mean().iloc[-1] if len(tr) >= n else tr.mean()


def _pivots(x, left=2, right=2):
    h = x.high.to_numpy(float)
    l = x.low.to_numpy(float)
    hs, ls = [], []
    for i in range(left, len(x)-right):
        if h[i] >= np.max(h[i-left:i+right+1]):
            hs.append(i)
        if l[i] <= np.min(l[i-left:i+right+1]):
            ls.append(i)
    return hs, ls


def candle_patterns(d):
    x = _clean(d)
    p = []
    if len(x) >= 2:
        a, b = x.iloc[-2], x.iloc[-1]
        if bear(a) and bull(b) and b.open <= a.close and b.close >= a.open and body(b) >= body(a)*0.9:
            p.append('Bullish Engulfing')
        if bull(a) and bear(b) and b.open >= a.close and b.close <= a.open and body(b) >= body(a)*0.9:
            p.append('Bearish Engulfing')
    if len(x) >= 3:
        a, b, c = x.iloc[-3], x.iloc[-2], x.iloc[-1]
        if bear(a) and body(b) <= rng(b)*0.35 and bull(c) and c.close > (a.open+a.close)/2:
            p.append('Morning Star')
        if bull(a) and body(b) <= rng(b)*0.35 and bear(c) and c.close < (a.open+a.close)/2:
            p.append('Evening Star')
    if len(x):
        c = x.iloc[-1]
        if body(c) <= rng(c)*0.12:
            p.append('Doji')
    return p


def _double_top(x, hs):
    if len(hs) < 2:
        return False
    a, b = hs[-2], hs[-1]
    h1, h2 = x.high.iloc[a], x.high.iloc[b]
    if abs(h1-h2)/max(h1,h2) > 0.012:
        return False
    valley = x.low.iloc[a:b+1].min()
    return x.close.iloc[-1] < valley * 0.998


def _double_bottom(x, ls):
    if len(ls) < 2:
        return False
    a, b = ls[-2], ls[-1]
    l1, l2 = x.low.iloc[a], x.low.iloc[b]
    if abs(l1-l2)/max(l1,l2) > 0.012:
        return False
    peak = x.high.iloc[a:b+1].max()
    return x.close.iloc[-1] > peak * 1.002


def _head_shoulders(x, hs):
    if len(hs) < 3:
        return False
    a,b,c = hs[-3:]
    ha,hb,hc = x.high.iloc[a],x.high.iloc[b],x.high.iloc[c]
    shoulder_tol = 0.035
    if hb <= ha*1.015 or hb <= hc*1.015:
        return False
    if abs(ha-hc)/max(ha,hc) > shoulder_tol:
        return False
    n1 = x.low.iloc[a:b+1].min(); n2 = x.low.iloc[b:c+1].min(); neckline=(n1+n2)/2
    return x.close.iloc[-1] < neckline*0.998


def _inverse_hs(x, ls):
    if len(ls) < 3:
        return False
    a,b,c = ls[-3:]
    la,lb,lc = x.low.iloc[a],x.low.iloc[b],x.low.iloc[c]
    if lb >= la*0.985 or lb >= lc*0.985:
        return False
    if abs(la-lc)/max(la,lc) > 0.035:
        return False
    n1=x.high.iloc[a:b+1].max(); n2=x.high.iloc[b:c+1].max(); neckline=(n1+n2)/2
    return x.close.iloc[-1] > neckline*1.002


def _trendline_stats(x, n=25):
    z=x.tail(n).reset_index(drop=True)
    t=np.arange(len(z), dtype=float)
    hs=np.polyfit(t, z.high.to_numpy(float), 1)[0]
    ls=np.polyfit(t, z.low.to_numpy(float), 1)[0]
    scale=max(float(z.close.iloc[-1]),1e-9)
    return hs/scale, ls/scale, z


def _triangles_and_wedges(x):
    if len(x) < 30:
        return []
    sh, sl, z = _trendline_stats(x, 30)
    p=[]
    close=float(z.close.iloc[-1]); atr=float(_atr(z) or 0)
    if atr <= 0: return p
    hi=z.high.max(); lo=z.low.min()
    range_now=max(z.high.tail(10).max()-z.low.tail(10).min(), atr)
    resistance_touch=(z.high.tail(12).max()-z.high.tail(12).min())/max(z.high.tail(12).mean(),1e-9) < 0.008
    support_touch=(z.low.tail(12).max()-z.low.tail(12).min())/max(z.low.tail(12).mean(),1e-9) < 0.008
    converging = abs(sh-sl) > 0.00015 and sh*sl < 0
    if resistance_touch and sl > 0.00025 and close > z.high.tail(12).max()+0.10*atr:
        p.append('Ascending Triangle')
    if support_touch and sh < -0.00025 and close < z.low.tail(12).min()-0.10*atr:
        p.append('Descending Triangle')
    if converging and sh < -0.00015 and sl > 0.00015:
        if close > z.high.tail(10).max()+0.10*atr: p.append('Bull Pennant')
        elif close < z.low.tail(10).min()-0.10*atr: p.append('Bear Pennant')
        else: p.append('Symmetrical Triangle')
    if sh > 0.00015 and sl > 0.00015 and abs(sh-sl) < 0.0012 and close < z.low.tail(10).min()-0.10*atr:
        p.append('Rising Wedge')
    if sh < -0.00015 and sl < -0.00015 and abs(sh-sl) < 0.0012 and close > z.high.tail(10).max()+0.10*atr:
        p.append('Falling Wedge')
    return p


def _flags(x):
    if len(x) < 35:
        return []
    z=x.tail(35).reset_index(drop=True)
    atr=float(_atr(z) or 0)
    if atr <= 0: return []
    impulse=z.iloc[:15]
    cons=z.iloc[15:30]
    last=z.iloc[-1]
    impulse_ret=impulse.close.iloc[-1]/impulse.close.iloc[0]-1
    cons_range=(cons.high.max()-cons.low.min())/max(cons.close.mean(),1e-9)
    p=[]
    if impulse_ret > 0.025 and cons_range < 0.045 and last.close > cons.high.max()+0.10*atr:
        p.append('Bull Flag')
    if impulse_ret < -0.025 and cons_range < 0.045 and last.close < cons.low.min()-0.10*atr:
        p.append('Bear Flag')
    return p


def _cup_handle(x):
    if len(x) < 60:
        return False
    z=x.tail(80).reset_index(drop=True)
    mid=len(z)//2
    left=z.close.iloc[:mid].max(); right=z.close.iloc[mid:].max(); bottom=z.close.iloc[mid-12:mid+12].min()
    rim=(left+right)/2
    if rim <= 0 or bottom >= rim*0.92 or abs(left-right)/rim > 0.06:
        return False
    handle=z.close.tail(10)
    return handle.max() < rim*1.01 and z.close.iloc[-1] > handle.iloc[:-1].max() if len(handle)>1 else False


def chart_patterns(d):
    x=_clean(d)
    if len(x)<30: return []
    hs,ls=_pivots(x)
    p=[]
    if _head_shoulders(x,hs): p.append('Head & Shoulders')
    if _inverse_hs(x,ls): p.append('Inverse Head & Shoulders')
    if _double_top(x,hs): p.append('Double Top')
    if _double_bottom(x,ls): p.append('Double Bottom')
    p.extend(_triangles_and_wedges(x))
    p.extend(_flags(x))
    if _cup_handle(x): p.append('Cup & Handle')
    return list(dict.fromkeys(p))


def analyze(d):
    x=_clean(d)
    if x.empty:
        return {'pattern':'NO DATA','direction':'NEUTRAL','patterns':[],'quality':0}
    p=list(dict.fromkeys(candle_patterns(x)+chart_patterns(x)))
    b=sum(v in BULLISH for v in p); r=sum(v in BEARISH for v in p)
    direction='BULLISH' if b>r else 'BEARISH' if r>b else 'NEUTRAL'
    quality=min(100, 45 + 15*min(2, max(b,r)) + (10 if len(p)>=2 else 0) + (10 if direction!='NEUTRAL' else 0))
    return {'pattern':' + '.join(p) if p else 'None','direction':direction,'patterns':p,'quality':quality}


def score(index_signal,a5,a1,ad):
    target='BULLISH' if index_signal=='BREAKOUT' else 'BEARISH'
    s=0
    if a5['direction']==target: s+=30
    if a1['direction']==target: s+=25
    if ad['direction']==target: s+=25
    if a5['patterns']: s+=5
    if a1['patterns']: s+=5
    if ad['patterns']: s+=5
    # Extra points only for multi-timeframe agreement; this keeps the score selective.
    dirs=[a5['direction'],a1['direction'],ad['direction']]
    if dirs.count(target)>=2: s+=5
    return min(100,s)


def levels(d,a):
    x=_clean(d)
    if x.empty: return (np.nan,np.nan,np.nan,np.nan)
    c=x.iloc[-1]
    atr=float(_atr(x) or 0)
    swing_hi=float(x.tail(6).high.max()); swing_lo=float(x.tail(6).low.min())
    if a['direction']=='BULLISH':
        e=max(float(c.high), swing_hi)
        sl=min(swing_lo, e-max(atr, e*0.005))
        risk=max(e-sl, e*0.005)
        return e,sl,e+risk,e+2*risk
    if a['direction']=='BEARISH':
        e=min(float(c.low), swing_lo)
        sl=max(swing_hi, e+max(atr,e*0.005))
        risk=max(sl-e,e*0.005)
        return e,sl,e-risk,e-2*risk
    e=float(c.close)
    return e,np.nan,np.nan,np.nan
