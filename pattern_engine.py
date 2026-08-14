import numpy as np

def body(c): return abs(float(c.close)-float(c.open))
def rng(c): return max(float(c.high)-float(c.low),1e-9)
def bull(c): return c.close>c.open
def bear(c): return c.close<c.open

def candle_patterns(d):
    p=[]
    if len(d)>=2:
        a,b=d.iloc[-2],d.iloc[-1]
        if bear(a) and bull(b) and b.open<=a.close and b.close>=a.open and body(b)>=body(a)*.9: p.append('Bullish Engulfing')
        if bull(a) and bear(b) and b.open>=a.close and b.close<=a.open and body(b)>=body(a)*.9: p.append('Bearish Engulfing')
    if len(d)>=3:
        a,b,c=d.iloc[-3],d.iloc[-2],d.iloc[-1]
        if bear(a) and body(b)<=rng(b)*.35 and bull(c) and c.close>(a.open+a.close)/2: p.append('Morning Star')
        if bull(a) and body(b)<=rng(b)*.35 and bear(c) and c.close<(a.open+a.close)/2: p.append('Evening Star')
    if len(d) and body(d.iloc[-1])<=rng(d.iloc[-1])*.12: p.append('Doji')
    return p

def chart_patterns(d):
    if len(d)<30:return []
    x=d.tail(120).reset_index(drop=True); p=[]; h=x.high.values;l=x.low.values;hs=[];ls=[]
    for i in range(2,len(x)-2):
        if h[i]>=max(h[i-2:i+3]):hs.append(i)
        if l[i]<=min(l[i-2:i+3]):ls.append(i)
    if len(hs)>=3:
        a,b,c=[h[i] for i in hs[-3:]]
        if abs(a-c)/max(a,c)<.025 and b>a*1.015 and b>c*1.015:p.append('Head & Shoulders')
        if abs(a-b)/max(a,b)<.012 and x.close.iloc[-1]<min(a,b)*.995:p.append('Double Top')
    if len(ls)>=3:
        a,b,c=[l[i] for i in ls[-3:]]
        if abs(a-c)/max(a,c)<.025 and b<a*.985 and b<c*.985:p.append('Inverse Head & Shoulders')
        if abs(a-b)/max(a,b)<.012 and x.close.iloc[-1]>max(a,b)*1.005:p.append('Double Bottom')
    if len(x)>=25:
        hi=x.high.tail(25).values;lo=x.low.tail(25).values;s=max(x.close.iloc[-1],1)
        sh=np.polyfit(np.arange(25),hi,1)[0]/s;sl=np.polyfit(np.arange(25),lo,1)[0]/s
        if abs(sh)<.0005 and sl>.0005:p.append('Ascending Triangle')
        elif sh<-.0005 and abs(sl)<.0005:p.append('Descending Triangle')
        elif sh<-.0005 and sl>.0005:p.append('Symmetrical Triangle')
        elif sh>.0005 and sl>.0005 and abs(sh-sl)<.0008:p.append('Rising Wedge')
        elif sh<-.0005 and sl<-.0005 and abs(sh-sl)<.0008:p.append('Falling Wedge')
        old=x.iloc[-25:-10];recent=x.iloc[-10:];imp=old.close.iloc[-1]/old.close.iloc[0]-1;rr=(recent.high.max()-recent.low.min())/max(recent.close.mean(),1)
        if abs(imp)>.025 and rr<.035:p.append('Bull Flag' if imp>0 else 'Bear Flag')
    return list(dict.fromkeys(p))

def analyze(d):
    if d is None or d.empty:return {'pattern':'NO DATA','direction':'NEUTRAL','patterns':[]}
    p=list(dict.fromkeys(candle_patterns(d)+chart_patterns(d)))
    bs={'Bullish Engulfing','Morning Star','Double Bottom','Inverse Head & Shoulders','Ascending Triangle','Falling Wedge','Bull Flag','Cup & Handle'}
    rs={'Bearish Engulfing','Evening Star','Double Top','Head & Shoulders','Descending Triangle','Rising Wedge','Bear Flag'}
    b=sum(x in bs for x in p);r=sum(x in rs for x in p);direction='BULLISH' if b>r else 'BEARISH' if r>b else 'NEUTRAL'
    return {'pattern':' + '.join(p) if p else 'None','direction':direction,'patterns':p}

def score(index_signal,a5,a1,ad):
    target='BULLISH' if index_signal=='BREAKOUT' else 'BEARISH';s=20
    if a5['direction']==target:s+=25
    if a1['direction']==target:s+=20
    if ad['direction']==target:s+=20
    if a5['patterns']:s+=5
    if a1['patterns']:s+=5
    if ad['patterns']:s+=5
    return min(s,100)

def levels(d,a):
    c=d.iloc[-1]
    if a['direction']=='BULLISH':
        e=float(c.high);sl=float(d.tail(5).low.min());risk=max(e-sl,e*.005);return e,sl,e+risk,e+2*risk
    if a['direction']=='BEARISH':
        e=float(c.low);sl=float(d.tail(5).high.max());risk=max(sl-e,e*.005);return e,sl,e-risk,e-2*risk
    e=float(c.close);return e,e,e,e
