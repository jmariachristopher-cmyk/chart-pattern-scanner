import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
from angel_client import AngelClient, load_master, find_indices, find_equities
from pattern_engine import analyze_ohlc, breakout_signal

st.set_page_config(page_title='JMC Angel One Live Scanner', layout='wide')
st.title('JMC Index Breakout → Stock Pattern Scanner')
st.caption('Live OHLC from Angel One SmartAPI • table-only scanner • no order execution')

with st.sidebar:
    st.header('Angel One SmartAPI')
    st.info('Put credentials in Streamlit Secrets. Never paste your API key, PIN or TOTP secret into the source code.')
    index_interval=st.selectbox('Index timeframe', ['FIVE_MINUTE','FIFTEEN_MINUTE'], index=0)
    lookback=st.slider('Index breakout lookback', 10, 50, 20)
    min_score=st.slider('Minimum stock score', 50, 100, 70, 5)
    index_days=st.slider('Index history days', 2, 10, 3)
    stock_days=st.slider('Stock history days', 3, 30, 7)
    symbols_text=st.text_area('Stocks to scan (comma separated)', 'RELIANCE,TCS,INFY,HDFCBANK,ICICIBANK,SBIN,LT,BHARTIARTL,AXISBANK,MARUTI,SUNPHARMA,APOLLOHOSP,TATAMOTORS,JSWSTEEL,COALINDIA', height=140)
    run=st.button('🔄 CONNECT & SCAN LIVE', type='primary', use_container_width=True)

if run:
    try:
        api_key, client_code, pin, totp_secret = (
            st.secrets.get('ANGEL_API_KEY',''), st.secrets.get('ANGEL_CLIENT_CODE',''),
            st.secrets.get('ANGEL_PIN',''), st.secrets.get('ANGEL_TOTP_SECRET',''))
        client=AngelClient(api_key, client_code, pin, totp_secret)
        with st.spinner('Logging in to Angel One...'):
            login=client.login()
        st.success(f"Angel One connected: {login.get('data',{}).get('clientcode',client_code)}")

        master=load_master()
        indices=find_indices(master)
        if indices.empty:
            st.error('No NSE index instruments found in Angel One instrument master.')
            st.stop()

        now=datetime.now(); start=now-timedelta(days=index_days)
        idx_rows=[]; broken=[]
        progress=st.progress(0)
        for n, r in enumerate(indices.itertuples(index=False),1):
            try:
                df=client.candles('NSE', r.token, index_interval, start, now)
                sig,strength=breakout_signal(df, lookback)
                ltp=float(df.close.iloc[-1]) if len(df) else float('nan')
                idx_rows.append({'Index':r.display,'Signal':sig,'LTP':round(ltp,2) if ltp==ltp else '-', 'Strength %':round(strength,2),'Token':str(r.token)})
                if sig!='NONE': broken.append((r,sig,df))
            except Exception as e:
                idx_rows.append({'Index':r.display,'Signal':'ERROR','LTP':'-','Strength %':'-','Token':str(r.token),'Error':str(e)[:80]})
            progress.progress(n/len(indices))
        progress.empty()
        idx_df=pd.DataFrame(idx_rows)
        st.subheader('1. ALL INDEX BREAKOUT / BREAKDOWN')
        st.dataframe(idx_df.drop(columns=['Token'],errors='ignore'),use_container_width=True,hide_index=True)

        st.subheader('2. BROKEN INDICES')
        if not broken:
            st.info('No confirmed index breakout/breakdown on the selected timeframe/lookback.')
            st.stop()
        broken_df=pd.DataFrame([{'Index':r.display,'Signal':sig,'LTP':round(float(df.close.iloc[-1]),2)} for r,sig,df in broken])
        st.dataframe(broken_df,use_container_width=True,hide_index=True)

        symbols=[x.strip().upper() for x in symbols_text.split(',') if x.strip()]
        eq=find_equities(master,symbols)
        if eq.empty:
            st.warning('None of the entered stocks were found in the Angel One NSE-EQ master.')
            st.stop()
        allowed={r.display.split()[0].upper() for r,sig,df in broken}
        rows=[]; progress=st.progress(0)
        for n, r in enumerate(eq.itertuples(index=False),1):
            try:
                base_start=now-timedelta(days=stock_days)
                d5=client.candles('NSE',r.token,'FIVE_MINUTE',base_start,now)
                if len(d5)<40: continue
                res5=analyze_ohlc(d5)
                if res5['score']<min_score: continue
                d1h=client.candles('NSE',r.token,'ONE_HOUR',base_start,now)
                dd=client.candles('NSE',r.token,'ONE_DAY',now-timedelta(days=260),now)
                res1h=analyze_ohlc(d1h); resd=analyze_ohlc(dd)
                # Keep stocks only when their 5M direction agrees with at least one broken index direction.
                stock_dir=res5['direction']; index_dirs=[sig for _,sig,_ in broken]
                compatible=(stock_dir=='BULLISH' and 'BREAKOUT' in index_dirs) or (stock_dir=='BEARISH' and 'BREAKDOWN' in index_dirs)
                if not compatible: continue
                lev=res5['levels']
                rows.append({'Index':', '.join([r0.display for r0,sig0,df0 in broken]),'Index Signal':' / '.join([sig0 for r0,sig0,df0 in broken]),'Stock':r.base,
                    '5M Pattern':' + '.join(res5['patterns']) or '-', '5M Dir':stock_dir,'Score':res5['score'],
                    '1H Pattern':' + '.join(res1h['patterns']) or '-', '1H Dir':res1h['direction'],
                    'Daily Pattern':' + '.join(resd['patterns']) or '-', 'Daily Dir':resd['direction'],
                    'Entry':round(lev['entry'],2),'SL':round(lev['sl'],2),'T1':round(lev['t1'],2),'T2':round(lev['t2'],2)})
            except Exception as e:
                pass
            progress.progress(n/len(eq))
        progress.empty()
        st.subheader('3. STOCKS AFTER INDEX BREAKOUT FILTER')
        if rows:
            out=pd.DataFrame(rows).sort_values(['Score','Stock'],ascending=[False,True])
            st.dataframe(out,use_container_width=True,hide_index=True)
        else:
            st.info('No stock passed the index-direction + 5M pattern + score filter.')
    except Exception as e:
        st.error(f'Connection/scanner error: {e}')
else:
    st.warning('Add Angel One credentials to Streamlit Secrets, then click CONNECT & SCAN LIVE.')
    st.markdown('### Required Streamlit Secrets')
    st.code('''ANGEL_API_KEY = "YOUR_API_KEY"\nANGEL_CLIENT_CODE = "YOUR_CLIENT_CODE"\nANGEL_PIN = "YOUR_PIN"\nANGEL_TOTP_SECRET = "YOUR_TOTP_SECRET"''', language='toml')
    st.markdown('The scanner uses Angel One historical candle data and the daily instrument master to resolve symbol tokens.')
