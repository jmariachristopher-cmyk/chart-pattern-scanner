import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
from angel_client import AngelClient, load_master, find_indices, find_equities_all
from pattern_engine import analyze_ohlc, breakout_signal

st.set_page_config(page_title='JMC Angel One Live Scanner', layout='wide')
st.title('JMC Index Breakout → Stock Pattern Scanner')
st.caption('Live OHLC from Angel One SmartAPI • all NSE indices • automatic NSE equity universe • no order execution')

with st.sidebar:
    st.header('Angel One SmartAPI')
    st.info('Credentials are read only from Streamlit Secrets. Never paste your API key, PIN or TOTP secret into source code.')
    index_interval = st.selectbox('Index timeframe', ['FIVE_MINUTE', 'FIFTEEN_MINUTE'], index=0)
    lookback = st.slider('Index breakout lookback', 10, 50, 20)
    min_score = st.slider('Minimum stock score', 50, 100, 70, 5)
    index_days = st.slider('Index history days', 2, 10, 3)
    stock_days = st.slider('Stock 5M/1H history days', 3, 30, 7)
    max_stocks = st.slider('Maximum NSE stocks to scan per run', 100, 2500, 1000, 100)
    run = st.button('🔄 CONNECT & SCAN LIVE', type='primary', use_container_width=True)

required = ['ANGEL_API_KEY', 'ANGEL_CLIENT_CODE', 'ANGEL_PIN', 'ANGEL_TOTP_SECRET']
missing = [k for k in required if not st.secrets.get(k, '').strip()]

if run:
    if missing:
        st.error('Angel One connection cannot start because Streamlit Secrets are missing: ' + ', '.join(missing))
        st.info('Open Streamlit Cloud → Manage app → Settings → Secrets and add the four required keys. Do not put the real values in app.py.')
        st.stop()
    try:
        api_key = st.secrets.get('ANGEL_API_KEY', '')
        client_code = st.secrets.get('ANGEL_CLIENT_CODE', '')
        pin = st.secrets.get('ANGEL_PIN', '')
        totp_secret = st.secrets.get('ANGEL_TOTP_SECRET', '')

        client = AngelClient(api_key, client_code, pin, totp_secret)
        with st.spinner('Logging in to Angel One...'):
            login = client.login()
        st.success(f"Angel One connected: {login.get('data', {}).get('clientcode', client_code)}")

        with st.spinner('Downloading Angel One instrument master...'):
            master = load_master()

        indices = find_indices(master)
        if indices.empty:
            st.error('No NSE index instruments found in Angel One instrument master.')
            st.stop()

        now = datetime.now()
        start = now - timedelta(days=index_days)
        idx_rows, broken = [], []
        progress = st.progress(0)

        for n, r in enumerate(indices.itertuples(index=False), 1):
            try:
                df = client.candles('NSE', r.token, index_interval, start, now)
                sig, strength = breakout_signal(df, lookback)
                ltp = float(df.close.iloc[-1]) if len(df) else float('nan')
                idx_rows.append({
                    'Index': r.display,
                    'Signal': sig,
                    'LTP': round(ltp, 2) if ltp == ltp else '-',
                    'Strength %': round(strength, 2),
                })
                if sig != 'NONE':
                    broken.append((r, sig, df))
            except Exception as e:
                idx_rows.append({'Index': r.display, 'Signal': 'ERROR', 'LTP': '-', 'Strength %': '-', 'Error': str(e)[:100]})
            progress.progress(n / len(indices))
        progress.empty()

        idx_df = pd.DataFrame(idx_rows)
        st.subheader('1. ALL NSE INDEX BREAKOUT / BREAKDOWN')
        st.dataframe(idx_df, use_container_width=True, hide_index=True)

        st.subheader('2. CONFIRMED BROKEN INDICES')
        if not broken:
            st.info('No confirmed index breakout/breakdown on the selected timeframe/lookback.')
            st.stop()

        broken_df = pd.DataFrame([
            {'Index': r.display, 'Signal': sig, 'LTP': round(float(df.close.iloc[-1]), 2)}
            for r, sig, df in broken
        ])
        st.dataframe(broken_df, use_container_width=True, hide_index=True)

        # AUTOMATIC UNIVERSE: no manual stock textbox. This includes the stocks
        # previously supplied by the user plus the rest of NSE cash equities.
        eq = find_equities_all(master)
        if eq.empty:
            st.error('No NSE-EQ stocks were found in the Angel One instrument master.')
            st.stop()

        # Keep the scan practical for Angel One API limits while preserving a
        # deterministic universe: alphabetical NSE-EQ symbols. Increase the
        # sidebar value when a larger universe is required.
        eq = eq.sort_values('base').head(max_stocks).reset_index(drop=True)
        st.caption(f'Automatic stock universe: {len(eq)} NSE-EQ symbols. No manual stock list is required.')

        rows = []
        progress = st.progress(0)
        base_start = now - timedelta(days=stock_days)
        index_dirs = [sig for _, sig, _ in broken]

        for n, r in enumerate(eq.itertuples(index=False), 1):
            try:
                d5 = client.candles('NSE', r.token, 'FIVE_MINUTE', base_start, now)
                if len(d5) < 40:
                    progress.progress(n / len(eq))
                    continue

                res5 = analyze_ohlc(d5)
                if res5['score'] < min_score:
                    progress.progress(n / len(eq))
                    continue

                stock_dir = res5['direction']
                compatible = (
                    (stock_dir == 'BULLISH' and 'BREAKOUT' in index_dirs) or
                    (stock_dir == 'BEARISH' and 'BREAKDOWN' in index_dirs)
                )
                if not compatible:
                    progress.progress(n / len(eq))
                    continue

                # Higher-timeframe calls are made only after a stock passes 5M,
                # reducing unnecessary Angel One API traffic.
                d1h = client.candles('NSE', r.token, 'ONE_HOUR', base_start, now)
                dd = client.candles('NSE', r.token, 'ONE_DAY', now - timedelta(days=260), now)
                res1h = analyze_ohlc(d1h)
                resd = analyze_ohlc(dd)
                lev = res5['levels']

                rows.append({
                    'Index': ', '.join([r0.display for r0, _, _ in broken]),
                    'Index Signal': ' / '.join([sig0 for _, sig0, _ in broken]),
                    'Stock': r.base,
                    '5M Pattern': ' + '.join(res5['patterns']) or '-',
                    '5M Dir': stock_dir,
                    'Score': res5['score'],
                    '1H Pattern': ' + '.join(res1h['patterns']) or '-',
                    '1H Dir': res1h['direction'],
                    'Daily Pattern': ' + '.join(resd['patterns']) or '-',
                    'Daily Dir': resd['direction'],
                    'Entry': round(lev['entry'], 2),
                    'SL': round(lev['sl'], 2),
                    'T1': round(lev['t1'], 2),
                    'T2': round(lev['t2'], 2),
                })
            except Exception:
                pass
            progress.progress(n / len(eq))
        progress.empty()

        st.subheader('3. STOCKS AFTER INDEX BREAKOUT FILTER')
        if rows:
            out = pd.DataFrame(rows).sort_values(['Score', 'Stock'], ascending=[False, True])
            st.dataframe(out, use_container_width=True, hide_index=True)
        else:
            st.info('No stock passed the index-direction + 5M pattern + score filter.')

    except Exception as e:
        st.error(f'Connection/scanner error: {e}')
else:
    if missing:
        st.warning('Angel One credentials are not configured yet. Add the four required Streamlit Secrets, then click CONNECT & SCAN LIVE.')
        st.markdown('### Required Streamlit Secrets')
        st.code('''ANGEL_API_KEY = "YOUR_API_KEY"\nANGEL_CLIENT_CODE = "YOUR_CLIENT_CODE"\nANGEL_PIN = "YOUR_PIN"\nANGEL_TOTP_SECRET = "YOUR_TOTP_SECRET"''', language='toml')
    else:
        st.success('Angel One credentials detected. Click CONNECT & SCAN LIVE.')

    st.markdown('### Automatic stock universe')
    st.write('The manual “Stocks to scan (comma separated)” box has been removed. The scanner now loads NSE cash-equity symbols automatically from the Angel One instrument master, so your previously supplied stocks are included without entering them again.')
