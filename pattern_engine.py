import numpy as np
import pandas as pd


def _pivots(df, left=3, right=3):
    hi=df['high'].to_numpy(float); lo=df['low'].to_numpy(float); ph=[]; pl=[]
    for i in range(left, len(df)-right):
        if hi[i] >= np.max(hi[i-left:i+right+1]): ph.append(i)
        if lo[i] <= np.min(lo[i-left:i+right+1]): pl.append(i)
    return ph,pl


def _candle_patterns(df):
    if len(df)<3:return []
    a,b,c=df.iloc[-1],df.iloc[-2],df.iloc[-3]; out=[]
    ar=max(float(a.high-a.low),1e-9); body=abs(float(a.close-a.open))
    if a.close>b.close and a.close>a.open and b.close<b.open and a.open<=b.close and a.close>=b.open: out.append('Bullish Engulfing')
    if a.close<a.open and b.close>b.open and a.open>=b.close and a.close<=b.open: out.append('Bearish Engulfing')
    if body/ar<=0.10: out.append('Doji')
    cb=abs(float(c.close-c.open)); bb=abs(float(b.close-b.open))
    if c.close<c.open and bb<=cb*0.5 and a.close>a.open and a.close>(c.open+c.close)/2: out.append('Morning Star')
    if c.close>c.open and bb<=cb*0.5 and a.close<a.open and a.close<(c.open+c.close)/2: out.append('Evening Star')
    return out


def _double_top(df, tolerance=.008, min_sep=8):
    ph,pl=_pivots(df)
    if len(ph)<2:return False
    p1,p2=ph[-2:]; h1,h2=float(df.high.iloc[p1]),float(df.high.iloc[p2])
    if p2-p1<min_sep or abs(h1-h2)/max((h1+h2)/2,1e-9)>tolerance:return False
    valleys=[i for i in pl if p1<i<p2]
    if not valleys:return False
    neck=min(float(df.low.iloc[i]) for i in valleys)
    return (min(h1,h2)-neck)/min(h1,h2)>=.02 and float(df.close.iloc[-1])<neck


def _double_bottom(df,tolerance=.008,min_sep=8):
    ph,pl=_pivots(df)
    if len(pl)<2:return False
    p1,p2=pl[-2:]; l1,l2=float(df.low.iloc[p1]),float(df.low.iloc[p2])
    if p2-p1<min_sep or abs(l1-l2)/max((l1+l2)/2,1e-9)>tolerance:return False
    peaks=[i for i in ph if p1<i<p2]
    if not peaks:return False
    neck=max(float(df.high.iloc[i]) for i in peaks)
    return (neck-max(l1,l2))/neck>=.02 and float(df.close.iloc[-1])>neck


def _hs(df,inverse=False,tolerance=.02):
    ph,pl=_pivots(df); pts=pl if inverse else ph
    if len(pts)<3:return False
    a,b,c=pts[-3:]
    if inverse:
        x,y,z=map(lambda i:float(df.low.iloc[i]),(a,b,c))
        if not(y<x and y<z) or abs(x-z)/max((x+z)/2,1e-9)>tolerance:return False
        mids=[i for i in ph if a<i<c]
        if len(mids)<2:return False
        neck=max(float(df.high.iloc[i]) for i in mids[-2:]); return float(df.close.iloc[-1])>neck
    x,y,z=map(lambda i:float(df.high.iloc[i]),(a,b,c))
    if not(y>x and y>z) or abs(x-z)/max((x+z)/2,1e-9)>tolerance:return False
    mids=[i for i in pl if a<i<c]
    if len(mids)<2:return False
    neck=min(float(df.low.iloc[i]) for i in mids[-2:]); return float(df.close.iloc[-1])<neck


def _triangles_and_wedges(df):
    ph,pl=_pivots(df)
    if len(ph)<2 or len(pl)<2:return []
    h1,h2=df.high.iloc[ph[-2]],df.high.iloc[ph[-1]]; l1,l2=df.low.iloc[pl[-2]],df.low.iloc[pl[-1]]
    hs=float(h2-h1); ls=float(l2-l1); out=[]
    avg=max(float(df.close.iloc[-1]),1e-9)
    if abs(hs)/avg<.01 and ls>0: out.append('Ascending Triangle')
    if abs(ls)/avg<.01 and hs<0: out.append('Descending Triangle')
    if hs>0 and ls>0 and hs<ls: out.append('Rising Wedge')
    if hs<0 and ls<0 and abs(hs)<abs(ls): out.append('Falling Wedge')
    return out


def analyze_ohlc(df):
    if df is None or len(df)<40:return {'patterns':[],'direction':'NEUTRAL','score':0,'levels':{}}
    d=df.copy(); d.columns=[str(c).lower() for c in d.columns]
    d=d.dropna(subset=['open','high','low','close']).reset_index(drop=True)
    patterns=_candle_patterns(d)
    if _double_top(d):patterns.append('Double Top')
    if _double_bottom(d):patterns.append('Double Bottom')
    if _hs(d):patterns.append('Head & Shoulders')
    if _hs(d,True):patterns.append('Inverse Head & Shoulders')
    patterns += _triangles_and_wedges(d)
    patterns=list(dict.fromkeys(patterns))
    bull={'Bullish Engulfing','Morning Star','Double Bottom','Inverse Head & Shoulders','Ascending Triangle','Falling Wedge'}
    bear={'Bearish Engulfing','Evening Star','Double Top','Head & Shoulders','Descending Triangle','Rising Wedge'}
    b=sum(p in bull for p in patterns); s=sum(p in bear for p in patterns)
    direction='BULLISH' if b>s else 'BEARISH' if s>b else 'NEUTRAL'
    score=min(100,50+15*max(b,s)+8*max(0,len(patterns)-1))
    tr=np.maximum(d.high-d.low,np.maximum(abs(d.high-d.close.shift()),abs(d.low-d.close.shift())))
    atr=float(tr.rolling(14).mean().iloc[-1]); entry=float(d.close.iloc[-1])
    if direction=='BULLISH': sl=entry-atr; t1=entry+1.5*atr; t2=entry+2.5*atr
    elif direction=='BEARISH': sl=entry+atr; t1=entry-1.5*atr; t2=entry-2.5*atr
    else: sl=t1=t2=float('nan')
    return {'patterns':patterns,'direction':direction,'score':int(score),'levels':{'entry':entry,'sl':sl,'t1':t1,'t2':t2}}


def breakout_signal(df, lookback=20, buffer=0.0):
    if df is None or len(df)<lookback+2:return ('NONE',0.0)
    d=df.copy(); last=d.iloc[-1]; prev=d.iloc[-lookback-1:-1]
    hh=float(prev.high.max()); ll=float(prev.low.min()); c=float(last.close)
    if c>hh*(1+buffer): return ('BREAKOUT', (c/hh-1)*100)
    if c<ll*(1-buffer): return ('BREAKDOWN', (c/ll-1)*100)
    return ('NONE',0.0)
