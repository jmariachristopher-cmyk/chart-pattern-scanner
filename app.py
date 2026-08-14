import streamlit as st,pandas as pd,requests,pyotp
from datetime import datetime,timedelta
from zoneinfo import ZoneInfo
from SmartApi import SmartConnect
import plotly.graph_objects as go
from pattern_engine import analyze,score,levels
from index_universe import INDEX_GROUPS,INDEX_ALIASES,STOCKS_BY_INDEX
IST=ZoneInfo('Asia/Kolkata')
st.set_page_config(page_title='JMC Index Pattern Scanner',layout='wide')
st.title('JMC Index Breakout + Pattern Scanner')
st.caption('Index breakout/breakdown -> component stocks -> 5M / 1H / Daily patterns')
with st.sidebar:
 st.header('Angel One');key=st.text_input('API Key',type='password');client=st.text_input('Client Code');pin=st.text_input('PIN / Password',type='password');secret=st.text_input('TOTP Secret',type='password')
 if st.button('Connect',type='primary'):
  try:
   api=SmartConnect(api_key=key);r=api.generateSession(client,pin,pyotp.TOTP(secret).now())
   if r and r.get('status'):st.session_state.api=api;st.success('Connected.')
   else:st.error(str(r))
  except Exception as e:st.error(str(e))
 max_stocks=st.slider('Stocks per broken index',5,25,12);threshold=st.slider('Minimum score',50,95,70,5)
 if st.button('Clear connection'):st.session_state.pop('api',None);st.rerun()
if 'api' not in st.session_state:st.warning('Connect Angel One.');st.stop()
api=st.session_state.api
@st.cache_data(ttl=3600)
def master():
 r=requests.get('https://margincalculator.angelone.in/OpenAPI_File/files/OpenAPIScripMaster.json',timeout=30);r.raise_for_status();return pd.DataFrame(r.json())
m=master()
def token(q):
 x=m[m.exch_seg.astype(str).str.upper()=='NSE'];q=q.upper()
 for c in ['name','symbol','tradingsymbol']:
  if c in x:
   z=x[x[c].astype(str).str.upper()==q]
   if len(z):return str(z.iloc[0].token)
 for c in ['name','symbol','tradingsymbol']:
  if c in x:
   z=x[x[c].astype(str).str.upper().str.contains(q,na=False)]
   if len(z):return str(z.iloc[0].token)
 return None
def candles(t,interval,days):
 now=datetime.now(IST);start=now-timedelta(days=days);p={'exchange':'NSE','symboltoken':str(t),'interval':interval,'fromdate':start.strftime('%Y-%m-%d %H:%M'),'todate':now.strftime('%Y-%m-%d %H:%M')};r=api.getCandleData(p)
 if not r or not r.get('status') or not r.get('data'):return pd.DataFrame()
 d=pd.DataFrame(r['data'],columns=['datetime','open','high','low','close','volume'])
 for c in ['open','high','low','close','volume']:d[c]=pd.to_numeric(d[c],errors='coerce')
 d['datetime']=pd.to_datetime(d['datetime'],errors='coerce');return d.dropna().reset_index(drop=True)
def idx_signal(d):
 if len(d)<20:return 'NO DATA'
 p=d.iloc[:-1].tail(12);c=d.iloc[-1];hi=p.high.max();lo=p.low.min();med=p.volume.median()
 if c.close>hi and c.volume>=med:return 'BREAKOUT'
 if c.close<lo and c.volume>=med:return 'BREAKDOWN'
 return 'INSIDE'
st.subheader('1. NSE Index Breakout / Breakdown');idxs=[]
for group,names in INDEX_GROUPS.items():
 for name in names:
  t=token(INDEX_ALIASES.get(name,name))
  if not t:continue
  try:s=idx_signal(candles(t,'FIVE_MINUTE',3))
  except:s='ERROR'
  idxs.append([group,name,s])
idf=pd.DataFrame(idxs,columns=['Segment','Index','Signal'])
st.dataframe(idf,use_container_width=True,hide_index=True)
broken=idf[idf.Signal.isin(['BREAKOUT','BREAKDOWN'])]
st.subheader('2. Stocks From Broken Indices');pairs=[]
for _,r in broken.iterrows():
 for s in STOCKS_BY_INDEX.get(r['Index'],[])[:max_stocks]:pairs.append((r['Index'],r['Signal'],s))
pairs=list(dict.fromkeys(pairs));rows=[];bar=st.progress(0)
for i,(idx,sig,stock) in enumerate(pairs):
 bar.progress((i+1)/max(len(pairs),1));t=token(stock)
 if not t:continue
 try:
  d5=candles(t,'FIVE_MINUTE',5);d1=candles(t,'ONE_HOUR',35);dd=candles(t,'ONE_DAY',250);a5=analyze(d5);a1=analyze(d1);ad=analyze(dd);sc=score(sig,a5,a1,ad);e,sl,t1,t2=levels(d5,a5)
  rows.append([idx,sig,stock,a5['pattern'],a1['pattern'],ad['pattern'],a5['direction'],a1['direction'],ad['direction'],sc,e,sl,t1,t2])
 except Exception:pass
r=pd.DataFrame(rows,columns=['Index','Index Signal','Stock','5M Pattern','1H Pattern','Daily Pattern','5M Dir','1H Dir','Daily Dir','Score','Entry','SL','T1','T2'])
if r.empty:st.info('No component stock data returned.');st.stop()
r=r.sort_values('Score',ascending=False);st.subheader('🔥 High-Confluence Setups');st.dataframe(r[r.Score>=threshold].head(15),use_container_width=True,hide_index=True)
st.subheader('3. Chart Pattern View');stock=st.selectbox('Stock',r.Stock.tolist());t=token(stock)
for title,d in [('5-Min Intraday',candles(t,'FIVE_MINUTE',5)),('1-Hour Positional',candles(t,'ONE_HOUR',35)),('Daily Positional',candles(t,'ONE_DAY',250))]:
 a=analyze(d)
 with st.expander(f'{title} • {a["pattern"]} • {a["direction"]}',expanded=title.startswith('5')):
  fig=go.Figure(go.Candlestick(x=d.datetime,open=d.open,high=d.high,low=d.low,close=d.close));fig.update_layout(height=430,xaxis_rangeslider_visible=False);st.plotly_chart(fig,use_container_width=True);st.write('Pattern:',a['pattern']);st.write('Direction:',a['direction'])
st.caption('Analysis only. Pattern detection is heuristic and cannot guarantee accuracy or returns.')
