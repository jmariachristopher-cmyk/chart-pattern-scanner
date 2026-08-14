
import numpy as np, pandas as pd

def pivots(df,left=3,right=3):
    hi,lo=df.high.to_numpy(float),df.low.to_numpy(float); ph=[];pl=[]
    for i in range(left,len(df)-right):
        if hi[i]>=max(hi[i-left:i+right+1]): ph.append(i)
        if lo[i]<=min(lo[i-left:i+right+1]): pl.append(i)
    return ph,pl

def candle_patterns(d):
    if len(d)<5:return []
    a,b,c=d.iloc[-1],d.iloc[-2],d.iloc[-3]; out=[]
    body=max(abs(a.close-a.open),1e-9); rng=max(a.high-a.low,1e-9)
    if a.close>a.open and b.close<b.open and a.open<=b.close and a.close>=b.open: out+=["Bullish Engulfing"]
    if a.close<a.open and b.close>b.open and a.open>=b.close and a.close<=b.open: out+=["Bearish Engulfing"]
    if body/rng<=.10: out+=["Doji"]
    if c.close<c.open and abs(b.close-b.open)<=abs(c.close-c.open)*.5 and a.close>a.open and a.close>(c.open+c.close)/2: out+=["Morning Star"]
    if c.close>c.open and abs(b.close-b.open)<=abs(c.close-c.open)*.5 and a.close<a.open and a.close<(c.open+c.close)/2: out+=["Evening Star"]
    return out

def strict_double_top(d,tol=.012,min_sep=5):
    ph,pl=pivots(d)
    if len(ph)<2:return False
    p1,p2=ph[-2:]
    if p2-p1<min_sep:return False
    h1,h2=d.high.iloc[p1],d.high.iloc[p2]
    if abs(h1-h2)/((h1+h2)/2) > tol:return False
    valleys=[i for i in pl if p1<i<p2]
    if not valleys:return False
    neck=min(d.low.iloc[i] for i in valleys)
    if (min(h1,h2)-neck)/min(h1,h2)<.01:return False
    return d.close.iloc[-1]<neck

def strict_double_bottom(d,tol=.012,min_sep=5):
    ph,pl=pivots(d)
    if len(pl)<2:return False
    p1,p2=pl[-2:]
    if p2-p1<min_sep:return False
    l1,l2=d.low.iloc[p1],d.low.iloc[p2]
    if abs(l1-l2)/((l1+l2)/2)>tol:return False
    peaks=[i for i in ph if p1<i<p2]
    if not peaks:return False
    neck=max(d.high.iloc[i] for i in peaks)
    if (neck-max(l1,l2))/neck<.01:return False
    return d.close.iloc[-1]>neck

def strict_hs(d,inverse=False,tol=.025):
    ph,pl=pivots(d)
    pts=pl if inverse else ph
    if len(pts)<3:return False
    a,b,c=pts[-3:]
    x,y,z=(d.low.iloc[a],d.low.iloc[b],d.low.iloc[c]) if inverse else (d.high.iloc[a],d.high.iloc[b],d.high.iloc[c])
    if inverse:
        if not(y<x and y<z) or abs(x-z)/((x+z)/2)>tol:return False
        mids=[i for i in ph if a<i<c]
        if len(mids)<2:return False
        neck=max(d.high.iloc[i] for i in mids[-2:])
        return d.close.iloc[-1]>neck
    else:
        if not(y>x and y>z) or abs(x-z)/((x+z)/2)>tol:return False
        mids=[i for i in pl if a<i<c]
        if len(mids)<2:return False
        neck=min(d.low.iloc[i] for i in mids[-2:])
        return d.close.iloc[-1]<neck

def analyze_ohlc(df):
    d=df.copy(); d.columns=[str(c).lower() for c in d.columns]
    if len(d)<40:return {"patterns":[],"direction":"NEUTRAL","score":0,"levels":{}}
    p=candle_patterns(d)
    if strict_double_top(d):p+=["Double Top"]
    if strict_double_bottom(d):p+=["Double Bottom"]
    if strict_hs(d):p+=["Head & Shoulders"]
    if strict_hs(d,True):p+=["Inverse Head & Shoulders"]
    ph,pl=pivots(d)
    if len(ph)>=2 and len(pl)>=2:
        hu=d.high.iloc[ph[-1]]>d.high.iloc[ph[-2]]; hd=not hu
        lu=d.low.iloc[pl[-1]]>d.low.iloc[pl[-2]]; ld=not lu
        if hu and lu:p+=["Rising Structure"]
        if hd and ld:p+=["Falling Structure"]
        if abs(d.high.iloc[ph[-1]]-d.high.iloc[ph[-2]])/d.high.iloc[ph[-2]]<.01 and lu:p+=["Ascending Triangle"]
        if abs(d.low.iloc[pl[-1]]-d.low.iloc[pl[-2]])/d.low.iloc[pl[-2]]<.01 and hd:p+=["Descending Triangle"]
    p=list(dict.fromkeys(p))
    bull={"Bullish Engulfing","Morning Star","Double Bottom","Inverse Head & Shoulders","Ascending Triangle","Rising Structure"}
    bear={"Bearish Engulfing","Evening Star","Double Top","Head & Shoulders","Descending Triangle","Falling Structure"}
    b=sum(x in bull for x in p); s=sum(x in bear for x in p)
    direction="BULLISH" if b>s else "BEARISH" if s>b else "NEUTRAL"
    score=min(100,50+15*max(b,s)+10*max(0,len(p)-1))
    tr=np.maximum(d.high-d.low,np.maximum(abs(d.high-d.close.shift()),abs(d.low-d.close.shift())))
    atr=tr.rolling(14).mean().iloc[-1]; entry=float(d.close.iloc[-1])
    if direction=="BULLISH": sl=entry-atr;t1=entry+1.5*atr;t2=entry+2.5*atr
    elif direction=="BEARISH": sl=entry+atr;t1=entry-1.5*atr;t2=entry-2.5*atr
    else: sl=t1=t2=float("nan")
    return {"patterns":p,"direction":direction,"score":int(score),"levels":{"entry":entry,"sl":sl,"t1":t1,"t2":t2}}
