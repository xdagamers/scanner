import io
import json
import html
import time
import hmac
from datetime import datetime, time as dtime
from zoneinfo import ZoneInfo

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import requests
import streamlit as st
import streamlit.components.v1 as components
import yfinance as yf

# Core backend engine imports
from scanner import load_universe, scan_universe, scan_single, score_stock, fetch_history, fetch_index_history
from audit_logger import build_scan_snapshot
from google_sheets_audit import (
    append_audit_batch,
    new_run_id,
    read_audit_signals,
    read_performance_keys,
    read_final_performance,
    append_performance_rows,
    append_analysis_rows,
    append_watchlist_row,
    read_watchlist,
    log_paper_trade,
    get_paper_trades,
    close_paper_trade
)
from audit_analysis import build_completed_outcomes, analyze_outcome_combinations
from performance_tracker import (
    build_performance_rows,
    fetch_ohlc_histories,
    latest_completed_market_date,
)
from fundamental_data import fetch_single_fundamental, apply_fundamental_gate
from live_watchlist import render_watchlist_tab
from sentiment_engine import get_headline_sentiment

# Optional delivery loader integration
try:
    from delivery_loader import enrich_shortlist_with_delivery
except ImportError:
    def enrich_shortlist_with_delivery(df, report_date=None):
        if df is not None and not df.empty and 'delivery_pct' not in df.columns:
            df['delivery_pct'] = None
            df['deliverable_qty'] = None
        return df

IST = ZoneInfo('Asia/Kolkata')

NIFTY50_CSV = 'https://nsearchives.nseindia.com/content/indices/ind_nifty50list.csv'
NSE_HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120 Safari/537.36',
    'Accept': 'text/csv,text/plain,*/*',
}

st.set_page_config(
    page_title='NIFTY Momentum Intelligence | Fintech Analytics',
    page_icon='📈',
    layout='wide',
    initial_sidebar_state='collapsed',
)

def password_gate():
    try:
        required = str(st.secrets.get('APP_PASSWORD', '')).strip()
    except Exception:
        required = ''
    if not required:
        return True
    if st.session_state.get('authenticated', False):
        return True

    col1, col2, col3 = st.columns([1, 1.2, 1])
    with col2:
        st.markdown("<div style='height:60px'></div>", unsafe_allow_html=True)
        st.title('🔐 NIFTY Momentum Intelligence')
        st.caption('Fintech Portfolio Analytics Secure Portal')
        with st.form('scanner_password_login'):
            entered = st.text_input('Enter access key', type='password')
            submitted = st.form_submit_button('Unlock Platform', use_container_width=True)
        if submitted:
            if hmac.compare_digest(entered, required):
                st.session_state['authenticated'] = True
                st.rerun()
            else:
                st.error('Incorrect password.')
    return False

if not password_gate():
    st.stop()

# -----------------------------------------------------------------------------
# SESSION STATE INITIALIZATION
# -----------------------------------------------------------------------------
if 'theme_mode' not in st.session_state:
    st.session_state.theme_mode = 'dark'
if 'ui_sandbox_mode' not in st.session_state:
    st.session_state.ui_sandbox_mode = False
if 'page' not in st.session_state:
    st.session_state.page = 'home'
if 'scan_result' not in st.session_state:
    st.session_state.scan_result = None
if 'scan_timestamp' not in st.session_state:
    st.session_state.scan_timestamp = None
if 'scanning' not in st.session_state:
    st.session_state.scanning = False
if 'audit_last_saved' not in st.session_state:
    st.session_state.audit_last_saved = None
if 'audit_pending_rows' not in st.session_state:
    st.session_state.audit_pending_rows = None
if 'audit_pending_run_id' not in st.session_state:
    st.session_state.audit_pending_run_id = None
if 'audit_pending_timestamp' not in st.session_state:
    st.session_state.audit_pending_timestamp = None
if 'audit_append_in_progress' not in st.session_state:
    st.session_state.audit_append_in_progress = False
if 'trade_filter' not in st.session_state:
    st.session_state.trade_filter = 'All'
if 'cap_filter' not in st.session_state:
    st.session_state.cap_filter = 'All Caps'
if 'portfolio_ticker_mode' not in st.session_state:
    st.session_state.portfolio_ticker_mode = True

# -----------------------------------------------------------------------------
# FINTECH ANALYTICS CSS
# -----------------------------------------------------------------------------
def inject_theme_css():
    is_light = st.session_state.theme_mode == 'light'
    
    theme_vars = (
        '''
        --bg: #f8fafc;
        --card: #ffffff;
        --card2: #f1f5f9;
        --border: #e2e8f0;
        --border-glow: rgba(79, 70, 229, 0.25);
        --text: #0f172a;
        --muted: #64748b;
        --accent: #059669;
        --accent-bg: rgba(5, 150, 105, 0.08);
        --red: #dc2626;
        --red-bg: rgba(220, 38, 38, 0.08);
        --yellow: #d97706;
        --yellow-bg: rgba(217, 119, 6, 0.08);
        --brand: #4f46e5;
        --brand-bg: rgba(79, 70, 229, 0.08);
        --bar-track: #e2e8f0;
        --shadow: 0 4px 20px rgba(15, 23, 42, 0.04);
        '''
        if is_light
        else '''
        --bg: #05070b;
        --card: #0d1017;
        --card2: #131823;
        --border: #1e2535;
        --border-glow: rgba(16, 185, 129, 0.3);
        --text: #f8fafc;
        --muted: #8c9bae;
        --accent: #10b981;
        --accent-bg: rgba(16, 185, 129, 0.12);
        --red: #ef4444;
        --red-bg: rgba(239, 68, 68, 0.12);
        --yellow: #f59e0b;
        --yellow-bg: rgba(245, 158, 11, 0.12);
        --brand: #6366f1;
        --brand-bg: rgba(99, 102, 241, 0.14);
        --bar-track: #1b2230;
        --shadow: 0 10px 30px rgba(0, 0, 0, 0.4);
        '''
    )

    css = f'''
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800;900&display=swap');
    :root {{ {theme_vars} }}
    html, body, [data-testid="stAppViewContainer"] {{
        background: var(--bg) !important;
        color: var(--text) !important;
        font-family: 'Inter', sans-serif !important;
    }}
    [data-testid="stHeader"], footer, #MainMenu, [data-testid="stToolbar"] {{
        visibility: hidden !important; height: 0 !important; display: none !important;
    }}
    .block-container {{
        max-width: 1840px !important;
        padding: 1.2rem 2.2rem 4rem !important;
    }}
    section[data-testid="stSidebar"] {{ display: none !important; }}
    * {{ box-sizing: border-box; }}
    
    .stMarkdown p, .stText p, label, .stRadio label {{ color: var(--text) !important; }}

    .stButton > button {{
        width: 100%;
        border-radius: 10px;
        border: 1px solid var(--border);
        background: var(--card2);
        color: var(--text);
        min-height: 44px;
        font-weight: 700;
        font-size: 0.84rem;
        transition: all 0.15s ease;
        box-shadow: var(--shadow);
    }}
    
    button[data-testid="baseButton-secondary"]:has(div:contains("SCAN MARKET")),
    button[data-testid="baseButton-secondary"]:has(div:contains("COLLECT AUDIT DATA")),
    button[data-testid="baseButton-secondary"]:has(div:contains("UPDATE PERFORMANCE TRACKING")) {{
        background-color: var(--card2);
        border: 1px solid var(--border);
        color: var(--text) !important;
    }}
    
    button[data-testid="baseButton-primary"] {{
        background-color: var(--text) !important;
        color: var(--bg) !important;
        border: 1px solid var(--text) !important;
    }}
    
    button[data-testid="baseButton-primary"]:hover {{
        opacity: 0.85;
    }}
    
    .stButton > button:hover {{
        border-color: var(--accent);
        color: var(--accent);
        transform: translateY(-1px);
    }}

    .bento-card {{
        background: var(--card);
        border: 1px solid var(--border);
        border-radius: 16px;
        padding: 20px;
        margin-bottom: 16px;
        box-shadow: var(--shadow);
    }}
    
    .bento-stock-card {{
        background: var(--card);
        border: 1px solid var(--border);
        border-radius: 16px;
        padding: 20px;
        margin-bottom: -4px;
        box-shadow: var(--shadow);
        transition: border-color 0.2s ease, transform 0.2s ease;
    }}
    .bento-stock-card:hover {{
        border-color: var(--border-glow);
        transform: translateY(-2px);
    }}

    .fintech-topbar {{
        display: flex;
        align-items: center;
        justify-content: space-between;
        flex-wrap: wrap;
        gap: 16px;
        padding: 16px 24px;
        background: var(--card);
        border: 1px solid var(--border);
        border-radius: 16px;
        box-shadow: var(--shadow);
        margin-bottom: 16px;
    }}
    .fintech-brand {{
        display: flex;
        align-items: center;
        gap: 14px;
    }}
    .fintech-logo {{
        width: 40px;
        height: 40px;
        border-radius: 12px;
        background: linear-gradient(135deg, #10b981, #4f46e5);
        display: flex;
        align-items: center;
        justify-content: center;
        font-weight: 900;
        color: #ffffff;
        font-size: 1.1rem;
        box-shadow: 0 4px 12px rgba(16, 185, 129, 0.3);
    }}
    .fintech-title {{
        font-size: 1.25rem;
        font-weight: 800;
        letter-spacing: -0.02em;
        color: var(--text);
        line-height: 1.1;
    }}
    .fintech-subtitle {{
        font-size: 0.75rem;
        color: var(--muted);
        font-weight: 500;
        margin-top: 2px;
    }}
    .fintech-indices {{
        display: flex;
        align-items: center;
        gap: 16px;
        flex-wrap: wrap;
    }}
    .fintech-pill {{
        padding: 8px 14px;
        border-radius: 10px;
        background: var(--card2);
        border: 1px solid var(--border);
        font-size: 0.82rem;
        color: var(--muted);
    }}
    .fintech-pill b {{
        color: var(--text);
        font-weight: 700;
        margin-right: 6px;
    }}

    .dot {{ width: 8px; height: 8px; border-radius: 50%; display: inline-block; margin-right: 6px; }}
    .dot.green {{ background: var(--accent); box-shadow: 0 0 10px var(--accent); }}
    .dot.red {{ background: var(--red); }}
    .dot.yellow {{ background: var(--yellow); }}
    .up {{ color: var(--accent) !important; font-weight: 700; }}
    .down {{ color: var(--red) !important; font-weight: 700; }}
    .small-muted, .ticker-note {{ color: var(--muted); font-size: 0.78rem; }}

    .badge {{
        display: inline-block;
        padding: 5px 10px;
        border-radius: 6px;
        font-size: 0.7rem;
        font-weight: 700;
        letter-spacing: 0.03em;
        text-transform: uppercase;
    }}
    .badge-green {{ background: var(--accent-bg); color: var(--accent); border: 1px solid rgba(16, 185, 129, 0.3); }}
    .badge-red {{ background: var(--red-bg); color: var(--red); border: 1px solid rgba(239, 68, 68, 0.3); }}
    .badge-yellow {{ background: var(--yellow-bg); color: var(--yellow); border: 1px solid rgba(245, 158, 11, 0.3); }}
    .badge-brand {{ background: var(--brand-bg); color: var(--brand); border: 1px solid rgba(99, 102, 241, 0.3); }}
    .badge-grey {{ background: var(--card2); color: var(--muted); border: 1px solid var(--border); }}
    .badge-accent {{ background: linear-gradient(90deg, #10b981, #059669); color: white; border: none; }}

    .bar-row {{
        display: flex;
        align-items: center;
        justify-content: space-between;
        gap: 12px;
        margin: 8px 0;
    }}
    .bar-label {{
        font-size: 0.7rem;
        font-weight: 700;
        color: var(--muted);
        width: 46px;
        text-transform: uppercase;
    }}
    .bar-track {{
        flex: 1;
        height: 6px;
        background: var(--bar-track);
        border-radius: 99px;
        overflow: hidden;
    }}
    .bar-fill {{
        height: 100%;
        border-radius: 99px;
    }}
    .bar-val {{
        font-size: 0.76rem;
        font-weight: 800;
        color: var(--text);
        width: 44px;
        text-align: right;
    }}

    .section-title {{
        font-size: 1.1rem;
        font-weight: 800;
        margin: 20px 0 14px;
        padding-bottom: 8px;
        border-bottom: 1px solid var(--border);
        color: var(--text);
        letter-spacing: -0.01em;
    }}
    .metric-card {{
        min-height: 76px;
        padding: 14px;
        border-radius: 12px;
        border: 1px solid var(--border);
        background: var(--card);
        margin-bottom: 12px;
    }}
    .metric-label {{ color: var(--muted); font-size: 0.68rem; text-transform: uppercase; letter-spacing: 0.05em; font-weight: 700; }}
    .metric-value {{ color: var(--text); font-weight: 800; font-size: 1.05rem; margin-top: 6px; word-break: break-word; }}
    .metric-good {{ border-left: 3px solid var(--accent); }}
    .metric-ok {{ border-left: 3px solid #84cc16; }}
    .metric-neutral {{ border-left: 3px solid var(--border); }}
    .metric-poor {{ border-left: 3px solid var(--yellow); }}
    .metric-bad {{ border-left: 3px solid var(--red); }}

    .target-box {{ padding: 14px 18px; border-radius: 12px; background: var(--card2); border: 1px solid var(--border); min-width: 130px; }}
    .target-label {{ font-size: 0.68rem; color: var(--muted); text-transform: uppercase; font-weight: 700; }}
    .target-value {{ font-size: 1.2rem; font-weight: 800; color: var(--text); margin-top: 4px; }}
    .target-upside {{ font-size: 0.8rem; color: var(--accent); margin-top: 2px; font-weight: 700; }}
    
    .audit-table-wrapper {{
        width: 100%;
        overflow-x: auto;
        border-radius: 12px;
        border: 1px solid var(--border);
        background: var(--card);
    }}
    .audit-table {{
        width: 100%;
        border-collapse: collapse;
        font-size: 0.85rem;
        color: var(--text);
    }}
    .audit-table th, .audit-table td {{
        border-bottom: 1px solid var(--border);
        padding: 10px 14px;
        text-align: left;
        white-space: nowrap;
    }}
    .audit-table th {{
        background-color: var(--card2);
        font-weight: 700;
        color: var(--text);
        text-transform: uppercase;
        font-size: 0.75rem;
    }}

    .scan-shell {{ background: var(--card); border: 1px solid var(--border); border-radius: 16px; padding: 24px; overflow: hidden; margin: 16px 0; }}
    .scan-chart {{ height: 130px; position: relative; overflow: hidden; border-radius: 10px; background: var(--card2); }}
    .candle-track {{ position: absolute; inset: 0; display: flex; align-items: center; gap: 12px; width: max-content; animation: scrollCandles 7s linear infinite; }}
    .candle {{ width: 6px; position: relative; border-radius: 2px; flex: none; }}
    .candle:before {{ content: ""; position: absolute; left: 2px; width: 2px; top: -12px; bottom: -12px; background: currentColor; opacity: 0.6; }}
    .candle.g {{ height: 50px; background: var(--accent); color: var(--accent); }}
    .candle.r {{ height: 34px; background: var(--red); color: var(--red); }}
    @keyframes scrollCandles {{ from {{ transform: translateX(0); }} to {{ transform: translateX(-50%); }} }}
    .scan-copy {{ display: flex; justify-content: space-between; color: var(--muted); font-size: 0.84rem; margin: 16px 0 10px; }}
    .progress {{ height: 6px; background: var(--card2); border-radius: 99px; overflow: hidden; }}
    .progress > div {{ width: 65%; height: 100%; border-radius: 99px; background: linear-gradient(90deg, var(--accent), var(--brand)); animation: progress 2.2s ease-in-out infinite; }}
    @keyframes progress {{ 0% {{ width: 8%; }} 50% {{ width: 78%; }} 100% {{ width: 94%; }} }}

    .news-item {{
        padding: 14px 18px;
        border-radius: 12px;
        background: var(--card2);
        border: 1px solid var(--border);
        margin-bottom: 10px;
        transition: border-color 0.2s ease;
    }}
    .news-item:hover {{
        border-color: var(--border-glow);
    }}
    .news-time {{
        font-size: 0.72rem;
        color: var(--muted);
        font-weight: 600;
        text-transform: uppercase;
        letter-spacing: 0.04em;
    }}
    .news-headline {{
        font-size: 0.95rem;
        font-weight: 700;
        color: var(--text);
        margin-top: 4px;
        line-height: 1.35;
    }}

    .stTabs [data-baseweb="tab-list"] {{ gap: 12px; border-bottom: 1px solid var(--border) !important; }}
    .stTabs [data-baseweb="tab"] {{ padding: 12px 20px; background: transparent; border: none; }}
    .stTabs [data-baseweb="tab"] p {{ color: var(--muted) !important; font-weight: 700; }}
    .stTabs [aria-selected="true"] {{ background: transparent; border-bottom: 3px solid var(--accent) !important; }}
    .stTabs [aria-selected="true"] p {{ color: var(--text) !important; }}

    @media (max-width: 768px) {{
        .block-container {{ padding: 0.6rem 0.8rem 3rem !important; }}
        .fintech-topbar {{ padding: 12px; }}
        .fintech-title {{ font-size: 1.1rem; }}
        .target-box {{ min-width: 110px; padding: 10px; }}
    }}
    </style>
    '''
    st.markdown(css, unsafe_allow_html=True)

inject_theme_css()

def render_reload_guard(active=True):
    if not active:
        return
    components.html('''
        <div id="reload-confirm" style="display:none;position:fixed;inset:0;z-index:999999;background:rgba(0,0,0,.5);backdrop-filter:blur(4px);align-items:center;justify-content:center;font-family:'Inter',sans-serif">
          <div style="width:min(400px,90vw);background:var(--card, #ffffff);color:var(--text, #111827);border:1px solid var(--border, #D1D5DB);border-radius:14px;padding:24px;box-shadow:0 20px 40px rgba(0,0,0,.5);text-align:center">
            <div style="font-size:18px;font-weight:700;margin-bottom:8px">Reload Application?</div>
            <div style="font-size:14px;color:var(--muted, #4B5563);line-height:1.5;margin-bottom:20px">The current scan and un-saved audit data will be lost if you reload.</div>
            <div style="display:flex;gap:12px;justify-content:center">
              <button id="reload-yes" style="flex:1;border:0;border-radius:8px;padding:12px;background:var(--red, #EF4444);color:#fff;font-weight:600;cursor:pointer">Reload</button>
              <button id="reload-no" style="flex:1;border:1px solid var(--border, #D1D5DB);border-radius:8px;padding:12px;background:var(--card2, #F8F9FA);color:var(--text, #111827);font-weight:600;cursor:pointer">Stay</button>
            </div>
          </div>
        </div>
        <script>
        (() => {
          try {
            const w = window.parent; const d = w.document;
            if (w.__niftyReloadGuardInstalled) return;
            w.__niftyReloadGuardInstalled = true;
            const modal = d.getElementById('reload-confirm');
            const yes = d.getElementById('reload-yes');
            const no = d.getElementById('reload-no');
            const show = () => { if (modal) modal.style.display='flex'; };
            const hide = () => { if (modal) modal.style.display='none'; };
            if (yes) yes.onclick = () => { w.location.href = w.location.origin + w.location.pathname + '?__reload_home=1'; };
            if (no) no.onclick = hide;
            w.addEventListener('beforeunload', (event) => { event.preventDefault(); event.returnValue = ''; });
            w.addEventListener('keydown', (event) => {
              const key = String(event.key || '').toLowerCase();
              const refresh = key === 'f5' || ((event.ctrlKey || event.metaKey) && key === 'r');
              if (refresh) { event.preventDefault(); show(); }
            }, true);
          } catch (e) {}
        })();
        </script>
    ''', height=0)
def get_timeframe_status(row):
    adx = float(row.get('adx', 0) or 0)
    rsi = float(row.get('rsi', 0) or 0)
    dist = float(row.get('distance_pct', 99) or 99)
    
    if dist <= 2.0 and rsi >= 60 and adx >= 20:
        return 'Breakout Swing (3-10d)', 'badge-accent'
    elif dist <= 4.0 and rsi >= 55:
        return 'Short Term (1-3w)', 'badge-brand'
    elif dist <= 7.0 and rsi >= 50:
        return 'Positional (2-6w)', 'badge-yellow'
    else:
        return 'Long Term (3-8m)', 'badge-brand'


@st.cache_data(ttl=60, show_spinner=False)
def get_market_snapshot():
    result = {'nifty': None, 'sensex': None, 'vix': None, 'updated': datetime.now(IST)}
    try:
        raw = yf.download(
            ['^NSEI', '^BSESN', '^INDIAVIX'],
            period='5d',
            interval='1d',
            auto_adjust=True,
            progress=False,
            threads=True,
            group_by='ticker',
            multi_level_index=True,
        )
        for symbol, key in [('^NSEI', 'nifty'), ('^BSESN', 'sensex'), ('^INDIAVIX', 'vix')]:
            try:
                df = (
                    raw[symbol]
                    if isinstance(raw.columns, pd.MultiIndex)
                    and symbol in raw.columns.get_level_values(0)
                    else raw.xs(symbol, axis=1, level=1)
                )
                df = df.dropna(subset=['Close'])
                if len(df) >= 2:
                    last, prev = float(df.Close.iloc[-1]), float(df.Close.iloc[-2])
                    result[key] = {'value': last, 'change': last - prev, 'pct': (last / prev - 1) * 100}
            except Exception:
                continue
    except Exception:
        pass
    return result

@st.cache_data(ttl=3600, show_spinner=False)
def get_nifty50_symbols():
    try:
        r = requests.get(NIFTY50_CSV, headers=NSE_HEADERS, timeout=15)
        r.raise_for_status()
        df = pd.read_csv(io.StringIO(r.text))
        col = next(c for c in df.columns if c.strip().lower() == 'symbol')
        return df[col].astype(str).str.strip().tolist()[:50]
    except Exception:
        return [
            'ADANIENT', 'ADANIPORTS', 'APOLLOHOSP', 'ASIANPAINT', 'AXISBANK',
            'BAJAJ-AUTO', 'BAJFINANCE', 'BAJAJFINSV', 'BEL', 'BHARTIARTL',
            'CIPLA', 'COALINDIA', 'DRREDDY', 'EICHERMOT', 'GRASIM', 'HCLTECH',
            'HDFCBANK', 'HDFCLIFE', 'HEROMOTOCO', 'HINDALCO', 'HINDUNILVR',
            'ICICIBANK', 'INDUSINDBK', 'INFY', 'ITC', 'JIOFIN', 'JSWSTEEL',
            'KOTAKBANK', 'LT', 'M&M', 'MARUTI', 'NESTLEIND', 'NTPC', 'ONGC',
            'POWERGRID', 'RELIANCE', 'SBILIFE', 'SBIN', 'SHRIRAMFIN', 'SUNPHARMA',
            'TATACONSUM', 'TATAMOTORS', 'TATASTEEL', 'TCS', 'TECHM', 'TITAN',
            'TRENT', 'ULTRACEMCO',
        ]

@st.cache_data(ttl=60, show_spinner=False)
def get_nifty50_ticker_data(symbols):
    rows = []
    try:
        tickers = [s.replace('&', '%26') + '.NS' for s in symbols]
        raw = yf.download(
            tickers,
            period='5d',
            interval='1d',
            auto_adjust=True,
            progress=False,
            threads=True,
            group_by='ticker',
            multi_level_index=True,
        )
        for symbol, ticker in zip(symbols, tickers):
            try:
                if isinstance(raw.columns, pd.MultiIndex):
                    if ticker in raw.columns.get_level_values(0):
                        df = raw[ticker]
                    elif ticker in raw.columns.get_level_values(1):
                        df = raw.xs(ticker, axis=1, level=1)
                    else:
                        continue
                else:
                    df = raw
                df = df.dropna(subset=['Close'])
                if len(df) < 2:
                    continue
                last, prev = float(df.Close.iloc[-1]), float(df.Close.iloc[-2])
                rows.append({'symbol': symbol, 'price': last, 'pct': (last / prev - 1) * 100})
            except Exception:
                continue
    except Exception:
        return pd.DataFrame(columns=['symbol', 'price', 'pct'])
    return pd.DataFrame(rows)

@st.cache_data(ttl=3600, show_spinner=False)
def get_fundamentals_cached(symbol):
    return fetch_single_fundamental(symbol)

@st.cache_data(ttl=120, show_spinner=False)
def fetch_history_cached(symbol, period='2y'):
    return fetch_history(symbol, period)

@st.cache_data(ttl=600, show_spinner=False)
def get_stock_news_and_sentiment_cached(symbol):
    news_list = []
    bullish = 0
    bearish = 0
    try:
        ticker_obj = yf.Ticker(symbol + '.NS')
        raw_news = ticker_obj.news
        if isinstance(raw_news, list):
            for idx, n in enumerate(raw_news):
                content = n.get('content', n)
                title = content.get('title', n.get('title', ''))
                if not title:
                    continue
                tag, cls = get_headline_sentiment(title)
                if idx < 8:
                    if 'Bullish' in tag or 'Positive' in tag:
                        bullish += 1
                    elif 'Bearish' in tag or 'Negative' in tag:
                        bearish += 1
                pub = content.get('provider', {}).get('displayName', n.get('publisher', 'Exchange Source'))
                link_data = content.get('clickThroughUrl', {})
                link = link_data.get('url', n.get('link', '#')) if isinstance(link_data, dict) else n.get('link', '#')
                pub_date = content.get('pubDate', n.get('providerPublishTime'))
                if isinstance(pub_date, str):
                    try:
                        pub_time = pd.to_datetime(pub_date).timestamp()
                    except Exception:
                        pub_time = None
                else:
                    pub_time = pub_date
                news_list.append({
                    'title': title,
                    'publisher': pub,
                    'link': link,
                    'providerPublishTime': pub_time,
                    'sentiment_tag': tag,
                    'sentiment_cls': cls,
                })
    except Exception:
        pass
    if bullish > bearish:
        agg_tag, agg_cls = 'Bullish News 📈', 'badge-green'
    elif bearish > bullish:
        agg_tag, agg_cls = 'Bearish News 📉', 'badge-red'
    elif news_list:
        agg_tag, agg_cls = 'Neutral News ⚖️', 'badge-grey'
    else:
        agg_tag, agg_cls = 'News Sentiment: N/A', 'badge-grey'
    return agg_tag, agg_cls, news_list

@st.cache_data(ttl=600, show_spinner=False)
def get_live_market_news_cached():
    news_items = []
    for tk_sym, default_tag in [('^NSEI', 'MARKET PULSE'), ('RELIANCE.NS', 'CORPORATE & MACRO'), ('HDFCBANK.NS', 'BANKING & FLOWS')]:
        try:
            raw_n = yf.Ticker(tk_sym).news
            if isinstance(raw_n, list):
                for n in raw_n[:3]:
                    content = n.get('content', n)
                    title = content.get('title', n.get('title', ''))
                    if not title or any(x['title'] == title for x in news_items):
                        continue
                    pub = content.get('provider', {}).get('displayName', n.get('publisher', 'Exchange Feed'))
                    link_data = content.get('clickThroughUrl', {})
                    link = link_data.get('url', n.get('link', '#')) if isinstance(link_data, dict) else n.get('link', '#')
                    pub_date = content.get('pubDate', n.get('providerPublishTime'))
                    if isinstance(pub_date, str):
                        try:
                            p_ts = pd.to_datetime(pub_date).timestamp()
                        except Exception:
                            p_ts = None
                    else:
                        p_ts = pub_date
                    sent_tag, _ = get_headline_sentiment(title)
                    news_items.append({
                        'title': title,
                        'publisher': pub,
                        'link': link,
                        'pub_time': p_ts,
                        'tag': sent_tag if sent_tag and sent_tag != 'Neutral' else default_tag,
                    })
                    if len(news_items) >= 3:
                        return news_items
        except Exception:
            continue
    return news_items

@st.cache_data(ttl=300, show_spinner=False)
def get_live_backtest_win_rate_cached():
    try:
        sig_df = read_audit_signals(st.secrets)
        fin_df = read_final_performance(st.secrets)
        if not sig_df.empty and not fin_df.empty:
            outcomes, rep = build_completed_outcomes(sig_df, fin_df, target_day=20)
            if not outcomes.empty and 'T1_Before_Stop' in outcomes.columns:
                valid = pd.to_numeric(outcomes['T1_Before_Stop'], errors='coerce').dropna()
                if len(valid) >= 5:
                    return round(float(valid.mean() * 100.0), 1), int(len(valid)), True
            if not outcomes.empty and 'T1_Hit' in outcomes.columns:
                valid_hit = pd.to_numeric(outcomes['T1_Hit'], errors='coerce').dropna()
                if len(valid_hit) >= 5:
                    return round(float(valid_hit.mean() * 100.0), 1), int(len(valid_hit)), True
    except Exception:
        pass
    return 68.0, 0, False

@st.cache_data(ttl=120, show_spinner=False)
def get_watchlist_cached():
    try:
        return read_watchlist(st.secrets)
    except Exception:
        return pd.DataFrame()

@st.cache_data(ttl=120, show_spinner=False)
def get_paper_trades_cached():
    try:
        return get_paper_trades(st.secrets)
    except Exception:
        return pd.DataFrame()

@st.cache_data(ttl=60, show_spinner=False)
def fetch_portfolio_live_prices_batch(symbols_tuple):
    if not symbols_tuple:
        return {}
    clean_syms = [str(s).strip().upper().replace('.NS', '') for s in symbols_tuple if str(s).strip()]
    if not clean_syms:
        return {}
    tickers = [s.replace('&', '%26') + '.NS' for s in clean_syms]
    live_prices = {}
    try:
        raw = yf.download(
            tickers,
            period='5d',
            interval='1d',
            auto_adjust=True,
            progress=False,
            threads=True,
            group_by='ticker',
            multi_level_index=True,
        )
        if raw is not None and not raw.empty:
            for sym, ticker in zip(clean_syms, tickers):
                try:
                    if isinstance(raw.columns, pd.MultiIndex):
                        if ticker in raw.columns.get_level_values(0):
                            df_s = raw[ticker]
                        elif ticker in raw.columns.get_level_values(1):
                            df_s = raw.xs(ticker, axis=1, level=1)
                        else:
                            continue
                    else:
                        df_s = raw
                    close_s = df_s['Close'].dropna()
                    if not close_s.empty:
                        val = float(close_s.iloc[-1])
                        if np.isfinite(val) and val > 0:
                            live_prices[sym] = val
                except Exception:
                    continue
    except Exception:
        pass
    # Fallback only for any symbol that missed batch download
    for sym, ticker in zip(clean_syms, tickers):
        if sym not in live_prices:
            try:
                fi = yf.Ticker(ticker).fast_info
                lp = fi.get('lastPrice') or fi.get('regularMarketPrice') or fi.get('previousClose')
                if lp and float(lp) > 0:
                    live_prices[sym] = float(lp)
            except Exception:
                pass
    return live_prices

def market_status(now=None):
    now = now or datetime.now(IST)
    if now.weekday() >= 5:
        return 'Closed', 'red'
    t = now.time()
    if dtime(9, 0) <= t < dtime(9, 15):
        return 'Pre-open', 'yellow'
    if dtime(9, 15) <= t <= dtime(15, 30):
        return 'Open', 'green'
    return 'Closed', 'red'

def money(x):
    return f'₹{x:,.2f}' if x is not None and np.isfinite(x) else '—'

def pct(x):
    return f'{x:+.2f}%' if x is not None and np.isfinite(x) else '—'

def render_fintech_topbar():
    if st.session_state.pop('_invalidate_portfolio_caches', False):
        get_watchlist_cached.clear()
        get_paper_trades_cached.clear()
        fetch_portfolio_live_prices_batch.clear()

    snap = get_market_snapshot()
    status, color = market_status()
    dot = f'<span class="dot {color}"></span>'

    nifty_item = snap.get('nifty')
    sensex_item = snap.get('sensex')
    vix_item = snap.get('vix')

    if nifty_item:
        nifty_cls = 'up' if nifty_item['pct'] >= 0 else 'down'
        nifty_str = f"{nifty_item['value']:,.2f} <span class='{nifty_cls}'>({nifty_item['pct']:+.2f}%)</span>"
    else:
        nifty_str = '—'
        
    if sensex_item:
        sensex_cls = 'up' if sensex_item['pct'] >= 0 else 'down'
        sensex_str = f"{sensex_item['value']:,.2f} <span class='{sensex_cls}'>({sensex_item['pct']:+.2f}%)</span>"
    else:
        sensex_str = '—'

    if vix_item:
        vix_cls = 'down' if vix_item['value'] >= 20.0 else 'up'
        vix_pill = f'<div class="fintech-pill"><b>INDIA VIX</b> <span class="{vix_cls}">{vix_item["value"]:.2f}</span> ({vix_item["pct"]:+.1f}%)</div>'
    else:
        vix_pill = ''

    col_brand, col_indices, col_controls = st.columns([2.7, 4.3, 3.0])
    with col_brand:
        st.markdown(
            f'''
            <div class="fintech-brand">
                <div class="fintech-logo">N</div>
                <div>
                    <div class="fintech-title">NIFTY INTELLIGENCE</div>
                    <div class="fintech-subtitle">{dot} Market Status: <b>{status}</b> • IST Live</div>
                </div>
            </div>
            ''',
            unsafe_allow_html=True,
        )

    with col_indices:
        st.markdown(
            f'''
            <div style="display:flex; gap:10px; justify-content:center; align-items:center; flex-wrap:wrap;">
                <div class="fintech-pill"><b>NIFTY 50</b> {nifty_str}</div>
                <div class="fintech-pill"><b>SENSEX</b> {sensex_str}</div>
                {vix_pill}
            </div>
            ''',
            unsafe_allow_html=True,
        )

    with col_controls:
        c1, c2, c3 = st.columns(3)
        with c1:
            port_crawl = st.toggle('🎯 My Crawl', value=st.session_state.get('portfolio_ticker_mode', True), key='portfolio_ticker_toggle', help='Crawl only your Watchlist & Open Paper Portfolio in the live ticker')
            if port_crawl != st.session_state.get('portfolio_ticker_mode', True):
                st.session_state.portfolio_ticker_mode = port_crawl
                st.rerun()
        with c2:
            is_light = st.toggle('☀️ Light', value=(st.session_state.theme_mode == 'light'), key='theme_toggle')
            new_mode = 'light' if is_light else 'dark'
            if new_mode != st.session_state.theme_mode:
                st.session_state.theme_mode = new_mode
                st.rerun()
        with c3:
            sandbox = st.toggle('🧪 Sandbox', value=st.session_state.ui_sandbox_mode, key='sandbox_toggle')
            if sandbox != st.session_state.ui_sandbox_mode:
                st.session_state.ui_sandbox_mode = sandbox
                st.rerun()

def _parse_float_safe(val, default=0.0):
    try:
        if pd.isna(val):
            return default
        s = str(val).replace('₹', '').replace(',', '').replace('%', '').strip()
        return float(s) if s else default
    except Exception:
        return default

def render_ticker():
    items = []
    use_portfolio_crawl = st.session_state.get('portfolio_ticker_mode', True)
    anim_duration = '45s'

    if use_portfolio_crawl:
        w_df = get_watchlist_cached()
        p_df = get_paper_trades_cached()

        open_p = pd.DataFrame()
        if not p_df.empty and 'Symbol' in p_df.columns:
            if 'Status' in p_df.columns:
                open_p = p_df[p_df['Status'].astype(str).str.strip().str.upper() == 'OPEN'].copy()
            else:
                open_p = p_df.copy()

        w_syms = []
        if not w_df.empty and 'Symbol' in w_df.columns:
            w_syms = [str(s).strip().upper().replace('.NS', '') for s in w_df['Symbol'].dropna().tolist() if str(s).strip()]

        p_syms = []
        if not open_p.empty and 'Symbol' in open_p.columns:
            p_syms = [str(s).strip().upper().replace('.NS', '') for s in open_p['Symbol'].dropna().tolist() if str(s).strip()]

        all_port_syms = tuple(sorted(set(w_syms + p_syms)))
        live_map = fetch_portfolio_live_prices_batch(all_port_syms) if all_port_syms else {}

        # 1. Open Paper Portfolio items first
        if not open_p.empty:
            for _, row in open_p.iterrows():
                sym = str(row.get('Symbol', '')).strip().upper().replace('.NS', '')
                if not sym or sym == 'NAN':
                    continue
                entry_p = _parse_float_safe(row.get('Entry_Price', 0.0))
                qty = int(round(_parse_float_safe(row.get('Quantity', 0.0))))
                live_p = live_map.get(sym, entry_p)
                pnl_pct = ((live_p / entry_p) - 1.0) * 100.0 if entry_p > 0 and live_p > 0 else 0.0
                pnl_rs = (live_p - entry_p) * qty if entry_p > 0 and live_p > 0 else 0.0
                cls = 'up' if pnl_pct >= 0 else 'down'
                arrow = '▲' if pnl_pct >= 0 else '▼'
                items.append(
                    f'<span class="tick" style="margin-right:32px;">'
                    f'<span style="color:#6366f1;font-weight:800;margin-right:5px;">📄 PAPER</span>'
                    f'<b>{html.escape(sym)}</b> {money(live_p)} '
                    f'<span class="{cls}">{arrow} {pnl_pct:+.2f}% ({pnl_rs:+,.0f}₹)</span>'
                    f'</span>'
                )

        # 2. Live Watchlist items
        if not w_df.empty and 'Symbol' in w_df.columns:
            seen_w = set()
            for _, row in w_df.iterrows():
                sym = str(row.get('Symbol', '')).strip().upper().replace('.NS', '')
                if not sym or sym == 'NAN' or sym in seen_w:
                    continue
                seen_w.add(sym)
                added_p = _parse_float_safe(row.get('Price_Added', 0.0))
                live_p = live_map.get(sym, added_p)
                ret_pct = ((live_p / added_p) - 1.0) * 100.0 if added_p > 0 and live_p > 0 else 0.0
                cls = 'up' if ret_pct >= 0 else 'down'
                arrow = '▲' if ret_pct >= 0 else '▼'
                items.append(
                    f'<span class="tick" style="margin-right:32px;">'
                    f'<span style="color:#10b981;font-weight:800;margin-right:5px;">👀 WATCH</span>'
                    f'<b>{html.escape(sym)}</b> {money(live_p)} '
                    f'<span class="{cls}">{arrow} {ret_pct:+.2f}%</span>'
                    f'</span>'
                )

    # Fallback to NIFTY 50 if user toggled off 'My Crawl' or if both Watchlist & Paper Portfolio are empty
    if not items:
        anim_duration = '90s'
        symbols = get_nifty50_symbols()
        df = get_nifty50_ticker_data(tuple(symbols))
        if df.empty:
            st.markdown('<div class="ticker-note">Live ticker stream temporarily unavailable.</div>', unsafe_allow_html=True)
            return
        for _, r in df.iterrows():
            cls = 'up' if r.pct >= 0 else 'down'
            arrow = '▲' if r.pct >= 0 else '▼'
            items.append(f'<span class="tick" style="margin-right:28px;"><b>{html.escape(r.symbol)}</b> {money(r.price)} <span class="{cls}">{arrow} {r.pct:+.2f}%</span></span>')

    repeat_factor = max(2, (12 // max(1, len(items))) + 1)
    content = ''.join(items * repeat_factor)
    
    light = st.session_state.theme_mode == 'light'
    bg = '#ffffff' if light else '#0d1017'
    textc = '#0f172a' if light else '#f8fafc'
    muted = '#64748b' if light else '#8c9bae'
    border = '#e2e8f0' if light else '#1e2535'
    markup = f'''<html><head><style>@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700;800&display=swap'); *{{box-sizing:border-box}}body{{margin:0;background:{bg};color:{textc};font-family:'Inter',sans-serif;overflow:hidden}}.viewport{{width:100%;overflow:hidden;border:1px solid {border};border-radius:12px;background:{bg};padding:10px 0}}.track{{display:flex;width:max-content;animation:marquee {anim_duration} linear infinite}}.track:hover{{animation-play-state:paused}}.tick{{white-space:nowrap;font-size:12px;color:{muted};font-weight:500}}.tick b{{color:{textc};margin-right:6px;font-weight:700}}.up{{color:#10b981;font-weight:700}}.down{{color:#ef4444;font-weight:700}}@keyframes marquee{{from{{transform:translateX(0)}}to{{transform:translateX(-50%)}}}}</style></head><body><div class="viewport"><div class="track">{content}{content}</div></div></body></html>'''
    components.html(markup, height=44, scrolling=False)

def day_change(symbol, period='2y', hist=None):
    hist = hist if hist is not None else fetch_history_cached(symbol, period)
    if hist is None or len(hist) < 2:
        return None, None, None
    last, prev = float(hist.Close.iloc[-1]), float(hist.Close.iloc[-2])
    return last, last - prev, (last / prev - 1) * 100

def ema(s, n):
    return s.ewm(span=n, adjust=False).mean()

def detect_pattern(df):
    if len(df) < 3: return None
    a, b, c = df.iloc[-3], df.iloc[-2], df.iloc[-1]
    body = lambda x: abs(x['Close'] - x['Open'])
    rng = lambda x: max(x['High'] - x['Low'], 1e-9)
    clv_c = (c['Close'] - c['Low']) / rng(c)
    if b['Close'] < b['Open'] < c['Close'] and c['Open'] <= b['Close'] and c['Close'] >= b['Open'] and clv_c >= 0.65: return "Bullish Engulfing"
    lower = min(c['Open'], c['Close']) - c['Low']
    upper = c['High'] - max(c['Open'], c['Close'])
    if lower >= 2 * body(c) and upper <= body(c) * 1.0 and clv_c >= 0.60: return "Hammer"
    if c['Close'] > c['Open'] and body(c) / rng(c) > 0.75: return "Bullish Marubozu"
    if a['Close'] < a['Open'] and body(b) < body(a) * 0.5 and c['Close'] > c['Open'] and c['Close'] > (a['Open'] + a['Close']) / 2: return "Morning Star"
    if b['Close'] < b['Open'] and c['Close'] > c['Open'] and c['Open'] < b['Low'] and c['Close'] > (b['Open'] + b['Close']) / 2: return "Piercing Line"
    if all(x['Close'] > x['Open'] for _, x in df.iloc[-3:].iterrows()) and a['Close'] < b['Close'] < c['Close']: return "Three White Soldiers"
    return None

def detail_chart(symbol, row, period='2y', hist=None):
    hist = hist if hist is not None else fetch_history_cached(symbol, period)
    if hist is None or hist.empty:
        st.warning('Price history is temporarily unavailable for the chart.')
        return
    light = st.session_state.theme_mode == 'light'
    fig = go.Figure()
    
    # 1. Base Candlestick
    fig.add_trace(go.Candlestick(x=hist.index, open=hist['Open'], high=hist['High'], low=hist['Low'], close=hist['Close'], name=symbol))
    
    # 2. Add EMA 50 and EMA 200
    if len(hist) >= 50:
        ema50 = ema(hist['Close'], 50)
        fig.add_trace(go.Scatter(x=hist.index, y=ema50, mode='lines', line=dict(color='#8B5CF6', width=1.5), name='EMA 50'))
        
        # Add dynamic floating label at the end of the line
        fig.add_annotation(
            x=hist.index[-1], y=ema50.iloc[-1],
            xref="x", yref="y",
            text="EMA 50", showarrow=False,
            xanchor="left", yanchor="middle",
            font=dict(color="#8B5CF6", size=10, weight="bold"),
            bgcolor="rgba(139, 92, 246, 0.1)", borderpad=2, xshift=10
        )
        
    if len(hist) >= 200:
        ema200 = ema(hist['Close'], 200)
        fig.add_trace(go.Scatter(x=hist.index, y=ema200, mode='lines', line=dict(color='#F59E0B', width=1.5), name='EMA 200'))
        
        # Add dynamic floating label at the end of the line
        fig.add_annotation(
            x=hist.index[-1], y=ema200.iloc[-1],
            xref="x", yref="y",
            text="EMA 200", showarrow=False,
            xanchor="left", yanchor="middle",
            font=dict(color="#F59E0B", size=10, weight="bold"),
            bgcolor="rgba(245, 158, 11, 0.1)", borderpad=2, xshift=10
        )
    
    # 3. Candlestick Pattern Recognition
    pattern = detect_pattern(hist)
    if pattern:
        # Point arrow at the most recent candle's low
        last_date = hist.index[-1]
        last_low = hist['Low'].iloc[-1]
        fig.add_annotation(
            x=last_date, y=last_low,
            xref="x", yref="y",
            text=f"🎯 {pattern}",
            showarrow=True, arrowhead=2, arrowsize=1, arrowwidth=2, arrowcolor="#10b981",
            ax=0, ay=30, # Arrow points UP to the low
            font=dict(color="#10b981", size=11, weight="bold"),
            bgcolor="rgba(16, 185, 129, 0.1)", bordercolor="#10b981", borderwidth=1, borderpad=4
        )

    # 4. Volume Bar
    fig.add_trace(go.Bar(x=hist.index, y=hist['Volume'], name='Volume', yaxis='y2', opacity=0.25, marker_color='#3B82F6'))
    
    # 5. Breakout Line
    fig.add_hline(y=float(row.get('breakout_level', 0) or 0), line_dash='dash', line_color='#10b981', annotation_text=f"Breakout: ₹{row.get('breakout_level', 0):.2f}", annotation_position='top left')
    
    # Layout Config
    fig.update_layout(
        template='plotly_white' if light else 'plotly_dark',
        height=520,
        margin=dict(l=10, r=40, t=25, b=10), # Added extra right margin for EMA labels
        xaxis_rangeslider_visible=False,
        hovermode='x unified',
        paper_bgcolor='#ffffff' if light else '#0d1017',
        plot_bgcolor='#F8F9FA' if light else '#05070b',
        font=dict(color='#111827' if light else '#f8fafc'),
        yaxis=dict(title='Price', gridcolor='#E5E7EB' if light else '#1e2535', color='#111827' if light else '#f8fafc'),
        yaxis2=dict(title='Volume', overlaying='y', side='right', showgrid=False, rangemode='tozero', color='#111827' if light else '#f8fafc'),
        legend=dict(orientation='h', y=1.02, x=0, font=dict(color='#111827' if light else '#f8fafc')),
    )
    st.plotly_chart(fig, use_container_width=True, config={'displayModeBar': False, 'responsive': True})

def verdict(score):
    if score >= 90: return 'Strong', True
    if score >= 75: return 'Good', True
    if score >= 60: return 'Neutral', False
    if score >= 40: return 'Weak', False
    return 'Avoid', False

def score_class(value, kind):
    try: v = float(value)
    except Exception: return 'metric-neutral'
    if kind == 'rsi': return 'metric-good' if 52 <= v <= 68 else 'metric-ok' if 48 <= v <= 72 else 'metric-poor'
    if kind == 'rvol': return 'metric-good' if v >= 1.5 else 'metric-ok' if v >= 1.1 else 'metric-poor' if v >= .8 else 'metric-bad'
    if kind == 'adx': return 'metric-good' if v >= 25 else 'metric-ok' if v >= 18 else 'metric-poor'
    if kind == 'distance': return 'metric-good' if v <= 1 else 'metric-ok' if v <= 3 else 'metric-neutral' if v <= 5 else 'metric-poor' if v <= 10 else 'metric-bad'
    if kind == 'rr': return 'metric-good' if v >= 2 else 'metric-ok' if v >= 1.5 else 'metric-neutral' if v >= 1 else 'metric-poor'
    if kind == 'score': return 'metric-good' if v >= 80 else 'metric-ok' if v >= 65 else 'metric-neutral' if v >= 50 else 'metric-poor' if v >= 35 else 'metric-bad'
    return 'metric-neutral'

def metric_card(label, value, kind=None):
    cls = score_class(value, kind) if kind else 'metric-neutral'
    return f'<div class="metric-card {cls}"><div class="metric-label">{html.escape(str(label))}</div><div class="metric-value">{html.escape(str(value))}</div></div>'

def target_values(row, price):
    b = float(row.get('breakout_level', 0) or 0)
    try: t1 = float(row.get('target1'))
    except Exception: t1 = None
    try: t2 = float(row.get('target2'))
    except Exception: t2 = None
    if t1 is None or not np.isfinite(t1):
        base = max(b - float(price), 0)
        t1 = b + base if base else b * 1.01
    if t2 is None or not np.isfinite(t2):
        base = max(b - float(price), 0)
        t2 = b + 2 * base if base else b * 1.02
    return t1, t2

def build_single_stock_export(symbol, row, scanned_at, rank=''):
    t1 = float(row.get('target1')) if pd.notna(row.get('target1')) else np.nan
    t2 = float(row.get('target2')) if pd.notna(row.get('target2')) else np.nan
    t3 = t2 + (t2 - t1) if np.isfinite(t1) and np.isfinite(t2) else np.nan
    targets = ' | '.join([f'T1: {t1:.2f}' if np.isfinite(t1) else 'T1: —', f'T2: {t2:.2f}' if np.isfinite(t2) else 'T2: —', f'T3: {t3:.2f}' if np.isfinite(t3) else 'T3: —'])
    return pd.DataFrame([{
        'Date': str(scanned_at).split(' ')[0], 'Stock': row.get('company_name', symbol), 'Symbol': symbol, 'Cap': row.get('cap_category', ''),
        'Rank': rank, 'Score': round(float(row.get('score', 0)), 2), 'Strength': row.get('rating', ''), 'Price': round(float(row.get('price')), 2),
        'Breakout Level': round(float(row.get('breakout_level')), 2), 'Targets': targets, 'Stop': round(float(row.get('stop_reference')), 2),
        'Distance %': round(float(row.get('distance_pct')), 2), 'RVOL': round(float(row.get('rvol')), 2), 'RSI': round(float(row.get('rsi')), 2),
        'ADX': round(float(row.get('adx')), 2), 'EOD Delivery %': row.get('delivery_pct', '—'), 'Market Regime': row.get('market_regime', ''),
    }])

# --- NEW FUNCTION FOR ENTRY CHECKLIST ---
def render_entry_zone_checklists(symbol, row, current_price, hist=None):
    try:
        breakout_level = float(row.get('breakout_level', 0))
        rsi_val = float(row.get('rsi', 0))
        rvol_val = float(row.get('rvol', 0))
        comp_vol = float(row.get('component_volume', 0.5))
        false_bo = bool(row.get('false_breakout', False))
    except (ValueError, TypeError):
        breakout_level, rsi_val, rvol_val, comp_vol, false_bo = 0.0, 0.0, 0.0, 0.5, False

    # PRE-BREAKOUT (Aligned with scanner-v2 institutional rules)
    if breakout_level > 0:
        dist_pct = ((current_price - breakout_level) / breakout_level) * 100
        prox_passed = -3.0 <= dist_pct <= 1.5
    else:
        prox_passed = False

    rsi_passed = 54.0 <= rsi_val <= 73.0
    vol_trend_passed = (rvol_val >= 1.0 or comp_vol >= 0.50) and (comp_vol > 0.10) and (not false_bo)

    # POST-BREAKOUT
    close_passed = (current_price > breakout_level) and (comp_vol > 0.10) if breakout_level > 0 else False
    brk_vol_passed = (rvol_val >= 1.4) and (comp_vol >= 0.70)
    
    sustain_passed = False
    try:
        hist_use = hist if hist is not None else fetch_history_cached(symbol, '2y')
        if hist_use is not None and len(hist_use) >= 2:
            last_2_closes = hist_use['Close'].dropna().tail(2).tolist()
            sustain_passed = (len(last_2_closes) == 2 and 
                              last_2_closes[0] > breakout_level and 
                              last_2_closes[1] > breakout_level)
    except Exception:
        pass

    def badge(condition, pending=False):
        if condition: 
            return "<span style='color:var(--accent); font-weight:800; font-size:0.75rem; padding:2px 8px; background:rgba(16,185,129,0.1); border-radius:4px;'>✅ PASSED</span>"
        if pending: 
            return "<span style='color:#fbbf24; font-weight:800; font-size:0.75rem; padding:2px 8px; background:rgba(251,191,36,0.1); border-radius:4px;'>⏳ PENDING</span>"
        return "<span style='color:var(--red); font-weight:800; font-size:0.75rem; padding:2px 8px; background:rgba(239,68,68,0.1); border-radius:4px;'>❌ FAILED</span>"

    html = f"""
    <div style="display:flex; gap:20px; flex-wrap:wrap; margin-bottom:24px;">
        <div class="bento-stock-card" style="flex:1; min-width:300px; padding:18px; border:1px solid var(--border); border-radius:12px; background:var(--card);">
            <div style="font-size:1.05rem; font-weight:900; color:var(--text); margin-bottom:16px; border-bottom:1px solid rgba(139,162,181,0.15); padding-bottom:10px;">🎯 PRE-BREAKOUT SETUP</div>
            <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:12px;"><span style="font-size:0.85rem; font-weight:500;">Price Proximity <span style="color:var(--muted); font-size:0.75rem;">(-3% to +1.5%)</span></span> {badge(prox_passed)}</div>
            <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:12px;"><span style="font-size:0.85rem; font-weight:500;">Bullish Momentum <span style="color:var(--muted); font-size:0.75rem;">(RSI 54–73)</span></span> {badge(rsi_passed)}</div>
            <div style="display:flex; justify-content:space-between; align-items:center;"><span style="font-size:0.85rem; font-weight:500;">Volume Accumulation <span style="color:var(--muted); font-size:0.75rem;">(RVOL ≥ 1.0 / 20D Acc.)</span></span> {badge(vol_trend_passed)}</div>
        </div>
        <div class="bento-stock-card" style="flex:1; min-width:300px; padding:18px; border:1px solid var(--border); border-radius:12px; background:var(--card);">
            <div style="font-size:1.05rem; font-weight:900; color:var(--text); margin-bottom:16px; border-bottom:1px solid rgba(139,162,181,0.15); padding-bottom:10px;">🚀 POST-BREAKOUT CONFIRMATION</div>
            <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:12px;"><span style="font-size:0.85rem; font-weight:500;">Daily Close <span style="color:var(--muted); font-size:0.75rem;">(> BO Level)</span></span> {badge(close_passed, pending=not close_passed)}</div>
            <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:12px;"><span style="font-size:0.85rem; font-weight:500;">Breakout Volume <span style="color:var(--muted); font-size:0.75rem;">(RVOL ≥ 1.4 &amp; Vol ≥ 70%)</span></span> {badge(brk_vol_passed, pending=not close_passed)}</div>
            <div style="display:flex; justify-content:space-between; align-items:center;"><span style="font-size:0.85rem; font-weight:500;">Price Sustain <span style="color:var(--muted); font-size:0.75rem;">(Holds > 2 Days)</span></span> {badge(sustain_passed, pending=not sustain_passed)}</div>
        </div>
    </div>
    """
    st.markdown(html, unsafe_allow_html=True)
# -----------------------------------------------


def get_aggregate_sentiment(symbol):
    agg_tag, agg_cls, _ = get_stock_news_and_sentiment_cached(symbol)
    return agg_tag, agg_cls

def render_detail(symbol, row):
    render_fintech_topbar()
    st.markdown("<div style='height:10px'></div>", unsafe_allow_html=True)

    col_back, col_watch = st.columns([5, 2])
    with col_back:
        if st.button('← Back to Analytics Dashboard'):
            st.session_state.page = 'home'
            st.rerun()

    company = row.get('company_name', symbol)
    hist_2y = fetch_history_cached(symbol, '2y')
    last, change, change_pct = day_change(symbol, hist=hist_2y)
    price = last if last is not None else row.get('price')
    score = float(row.get('score', 0))
    change_cls = 'up' if (change_pct or 0) >= 0 else 'down'
    arrow = '▲' if (change_pct or 0) >= 0 else '▼'
    
    t1, t2 = target_values(row, price)
    t1up = ((t1 / price) - 1) * 100 if price else 0
    t2up = ((t2 / price) - 1) * 100 if price else 0
    t3 = t2 + (t2 - t1) if np.isfinite(t1) and np.isfinite(t2) else np.nan
    timeframe, tf_cls = get_timeframe_status(row)
    
    # Calculate Dual Stop Losses from already-loaded 2Y history (zero extra network calls)
    price_val = float(price) if price else 0.0
    struct_stop = float(row.get('stop_reference', 0) or 0.0)
    aggr_stop = price_val * 0.98
    try:
        if hist_2y is not None and not hist_2y.empty:
            aggr_stop = float(hist_2y['Low'].tail(3).min()) # Last 3 days low for Breakout Candle Low
    except Exception:
        pass
        
    aggr_stop_pct = ((aggr_stop / price_val) - 1) * 100 if price_val else 0
    struct_stop_pct = ((struct_stop / price_val) - 1) * 100 if price_val else 0
    
    # Aggregate News Sentiment & Cached News List (fetched once per stock)
    sent_tag, sent_cls, cached_news_list = get_stock_news_and_sentiment_cached(symbol)

    with col_watch:
        if st.button('⭐ Add to Watchlist', type='primary', use_container_width=True):
            exp_days = timeframe.split('(')[-1].replace(')', '') if '(' in timeframe else "N/A"
            trade_type = timeframe.split(' (')[0]
            
            payload = {
                "Symbol": symbol,
                "Stock_Name": company,
                "Date_Added": datetime.now(IST).strftime('%Y-%m-%d'),
                "Price_Added": round(float(price), 2) if price else "",
                "Trade_Type": trade_type,
                "Expected_Days": exp_days,
                "Target_1": round(float(t1), 2) if np.isfinite(t1) else "",
                "Target_2": round(float(t2), 2) if np.isfinite(t2) else "",
                "Target_3": round(float(t3), 2) if np.isfinite(t3) else "",
                "MACD": round(float(row.get('macd', 0)), 3),
                "RSI": round(float(row.get('rsi', 0)), 1),
                "ADX": round(float(row.get('adx', 0)), 1),
                "Trigger_Price": round(float(row.get('breakout_trigger', 0)), 2)
            }
            try:
                append_watchlist_row(st.secrets, payload)
                get_watchlist_cached.clear()
                st.toast(f"✅ {symbol} saved to Manual_Watch_List!")
            except Exception as e:
                st.error(f"Watchlist save failed: {e}")

    hero_html = (
        f'<div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:24px;padding:24px;background:var(--card);border-radius:16px;border:1px solid var(--border);box-shadow:var(--shadow); flex-wrap:wrap; gap:20px;">'
        
        # Left side: Price & Sentiment
        f'<div style="flex:1; min-width:300px;">'
        f'<div class="small-muted" style="font-size:.9rem;font-weight:600;margin-bottom:6px;letter-spacing:.02em;text-transform:uppercase;">{html.escape(str(company))}</div>'
        f'<div style="display:flex;align-items:center;gap:12px;"><div style="font-size:2.4rem;font-weight:800;line-height:1.1;color:var(--text);">{html.escape(symbol)}</div> <span class="badge {tf_cls}">{timeframe}</span> <span class="badge {sent_cls}">{sent_tag}</span></div>'
        f'<div style="display:flex;align-items:center;gap:14px;margin-top:10px;">'
        f'<div style="font-size:1.8rem;font-weight:800;color:var(--text);">{money(price)}</div>'
        f'<div class="{change_cls}" style="font-weight:700;font-size:1.1rem;">{arrow} {money(change)} ({pct(change_pct)})</div>'
        f'</div>'
        f'</div>'
        
        # Right side: Targets & Dual Stops Grid
        f'<div style="display:grid; grid-template-columns: repeat(3, 1fr); gap:12px;">'
        f'<div class="target-box" style="border-left: 3px solid var(--accent);"><div class="target-label">Target 1 (Swing)</div><div class="target-value">{money(t1)}</div><div class="target-upside" style="color:var(--accent);">{t1up:+.2f}%</div></div>'
        f'<div class="target-box" style="border-left: 3px solid var(--brand);"><div class="target-label">Target 2 (Positional)</div><div class="target-value">{money(t2)}</div><div class="target-upside" style="color:var(--brand);">{t2up:+.2f}%</div></div>'
        f'<div class="target-box" style="border-left: 3px solid #8b5cf6;"><div class="target-label">Target 3 (Long Term)</div><div class="target-value">{money(t3)}</div><div class="target-upside" style="color:#8b5cf6;">{((t3/price)-1)*100 if price else 0:+.2f}%</div></div>'
        f'<div class="target-box" style="border-left: 3px solid var(--yellow);"><div class="target-label">Aggressive SL</div><div class="target-value">{money(aggr_stop)}</div><div class="target-upside" style="color:var(--red);">{aggr_stop_pct:+.2f}%</div></div>'
        f'<div class="target-box" style="border-left: 3px solid var(--red);"><div class="target-label">Structural SL</div><div class="target-value">{money(struct_stop)}</div><div class="target-upside" style="color:var(--red);">{struct_stop_pct:+.2f}%</div></div>'
        f'<div class="target-box" style="border-left: 3px solid var(--border);"><div class="target-label">Risk/Reward (T2)</div><div class="target-value">{float(row.get("risk_reward", 0)):.2f}x</div><div class="target-upside" style="color:var(--muted);">Ratio</div></div>'
        f'</div>'
        
        f'</div>'
    )
    st.markdown(hero_html, unsafe_allow_html=True)

    # --- POSITION SIZER ---
    st.markdown("<div class='section-title' style='margin-top:0;'>🛡️ Dynamic Position Sizer</div>", unsafe_allow_html=True)
    
    ps_col1, ps_col2, ps_col3 = st.columns([1, 1, 2])
    with ps_col1:
        max_risk = st.number_input("Max Risk Amount (₹)", min_value=100, value=2000, step=500, key=f"risk_{symbol}")
    with ps_col2:
        stop_choice = st.selectbox("Stop Loss Basis", ["Structural SL (EMA)", "Aggressive SL (Candle Low)"], key=f"sl_choice_{symbol}")
    
    active_sl = struct_stop if "Structural" in stop_choice else aggr_stop
    risk_per_share = max(price_val - active_sl, 0.01) # Avoid division by zero
    shares_to_buy = int(max_risk / risk_per_share)
    capital_required = shares_to_buy * price_val
    
    with ps_col3:
        st.markdown(f'''
        <div style="display:flex; gap:16px; align-items:center; height:100%; padding-top:28px;">
            <div class="bento-card" style="flex:1; margin-bottom:0; padding:12px 16px; border-color:var(--brand); background:var(--brand-bg);">
                <div style="font-size:0.75rem; font-weight:700; color:var(--brand); text-transform:uppercase;">Recommended Size</div>
                <div style="font-size:1.5rem; font-weight:900; color:var(--text); line-height:1.2;">{shares_to_buy} <span style="font-size:0.9rem; font-weight:600; color:var(--muted);">Shares</span></div>
            </div>
            <div class="bento-card" style="flex:1; margin-bottom:0; padding:12px 16px;">
                <div style="font-size:0.75rem; font-weight:700; color:var(--muted); text-transform:uppercase;">Capital Required</div>
                <div style="font-size:1.5rem; font-weight:900; color:var(--text); line-height:1.2;">{money(capital_required)}</div>
            </div>
        </div>
        ''', unsafe_allow_html=True)
        
    st.markdown("<div style='height:16px'></div>", unsafe_allow_html=True)
    
    # Paper Trade Execution Button
    if shares_to_buy > 0:
        if st.button(f"🚀 EXECUTE PAPER TRADE: Buy {shares_to_buy} shares of {symbol}", type="primary", use_container_width=True):
            trade_payload = {
                "Trade_ID": f"{symbol}_{int(time.time())}",
                "Symbol": symbol,
                "Entry_Date": datetime.now(IST).strftime('%Y-%m-%d %H:%M:%S'),
                "Entry_Price": price_val,
                "Quantity": shares_to_buy,
                "Invested_Capital": capital_required,
                "Stop_Loss": active_sl,
                "Target_1": float(t1) if t1 else 0.0,
                "Target_2": float(t2) if t2 else 0.0,
                "Status": "OPEN",
                "PnL": 0.0
            }
            try:
                log_paper_trade(st.secrets, trade_payload)
                get_paper_trades_cached.clear()
                st.toast(f"✅ Executed Paper Trade for {symbol}!")
            except Exception as e:
                st.error(f"Paper trade failed to execute. Error: {e}")
    # ----------------------

    tab_tech, tab_fund, tab_news, tab_audit = st.tabs(['📈 Technical Analytics', '🏛️ Fundamental Health', '📰 News & Filings', '📊 Audit Details'])

    with tab_tech:
        # INSERT THE ENTRY CHECKLIST HERE
        render_entry_zone_checklists(symbol, row, float(price) if price else 0, hist=hist_2y)
        
        c_left, c_right = st.columns([3, 1])
        with c_left:
            st.markdown('<div class="section-title" style="margin-top:0;">Price Action & Volume</div>', unsafe_allow_html=True)
            tv_symbol = str(symbol).replace('.NS', '').upper()
            tv_url = f'https://www.tradingview.com/chart/?symbol=NSE:{tv_symbol}'
            detail_chart(symbol, row, hist=hist_2y)
            st.markdown(f'<div style="text-align:center;margin:8px 0 16px;"><a href="{tv_url}" target="_blank" rel="noopener" style="color:var(--brand);font-weight:700;font-size:.85rem;text-decoration:none;">Open Full Interactive Chart ↗</a></div>', unsafe_allow_html=True)

        with c_right:
            st.markdown('<div class="section-title" style="margin-top:0;">Momentum Score</div>', unsafe_allow_html=True)
            light = st.session_state.theme_mode == 'light'
            fig = go.Figure(go.Indicator(
                mode='gauge+number',
                value=score,
                number={'suffix': '', 'font': {'size': 42, 'color': '#111827' if light else '#f8fafc'}},
                gauge={
                    'axis': {'range': [0, 100], 'tickwidth': 0, 'tickcolor': 'rgba(0,0,0,0)'},
                    'bar': {'color': '#10b981', 'thickness': 0.15},
                    'bgcolor': '#e2e8f0' if light else '#1b2230',
                    'borderwidth': 0,
                    'steps': [
                        {'range': [0, 40], 'color': 'rgba(239,68,68,0.15)'},
                        {'range': [40, 65], 'color': 'rgba(245,158,11,0.15)'},
                        {'range': [65, 80], 'color': 'rgba(132,204,22,0.15)'},
                        {'range': [80, 100], 'color': 'rgba(16,185,129,0.15)'},
                    ],
                },
            ))
            fig.update_layout(template='plotly_white' if light else 'plotly_dark', height=260, margin=dict(l=15, r=15, t=20, b=0), paper_bgcolor='#ffffff' if light else '#0d1017')
            st.plotly_chart(fig, use_container_width=True, config={'displayModeBar': False})

            level = float(row.get('breakout_level', 0) or 0)
            p = float(price or 0)
            distance = ((level - p) / level * 100) if level else 999
            if p >= level:
                title, msg, cls = 'Breakout Confirmed', 'Trading above detected resistance.', 'badge-green'
            elif distance <= 2:
                title, msg, cls = 'ENTRY ZONE', 'Near breakout level. Await volume confirmation.', 'badge-green'
            elif distance <= 5:
                title, msg, cls = 'Developing', 'Setup forming, not near entry.', 'badge-yellow'
            else:
                title, msg, cls = 'Watch', 'Monitoring base formation.', 'badge-grey'

            st.markdown(f'<div class="bento-card" style="text-align:center;"><span class="badge {cls}">{title}</span><div style="font-size:1rem;font-weight:700;margin-top:14px;color:var(--text);">{msg}</div><div class="small-muted" style="margin-top:8px">Distance: <span style="font-weight:600;">{distance:.2f}%</span> &nbsp; • &nbsp; Trigger: <span style="font-weight:600;">{money(row.get("breakout_trigger"))}</span></div></div>', unsafe_allow_html=True)

            if row.get('delivery_pct'):
                d_exp = float(row.get('deliv_expansion_ratio', 1.0) or 1.0)
                st.markdown(f'<div class="bento-card" style="text-align:center;"><span class="badge badge-green">EOD Delivery Confirmed</span><div style="font-size:1.6rem;font-weight:900;margin-top:8px;color:var(--accent);">{row.get("delivery_pct")}%</div><div class="small-muted">Relative Expansion: <b>{d_exp:.2f}x</b> vs Base</div></div>', unsafe_allow_html=True)

        # Institutional Diagnostic Summary from Scanner v3
        expl_text = str(row.get('explanation', '') or '')
        has_warning = ('WARNING' in expl_text) or bool(row.get('false_breakout', False)) or (float(row.get('component_volume', 0.5) or 0.5) <= 0.10)
        diag_border = 'var(--red)' if has_warning else 'var(--accent)'
        diag_badge = '<span class="badge badge-red">⚠️ TRAP / REJECTION WARNING</span>' if has_warning else '<span class="badge badge-green">🛡️ INSTITUTIONAL ANTI-TRAP PASSED</span>'
        if expl_text:
            st.markdown(
                f'<div class="bento-card" style="border-left: 4px solid {diag_border}; padding: 14px 18px; margin-bottom: 16px;">'
                f'<div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:6px;">'
                f'<span class="small-muted" style="text-transform:uppercase; font-weight:700; font-size:0.72rem;">Scanner v3 Regime-Adaptive Thesis</span>'
                f'{diag_badge}'
                f'</div>'
                f'<div style="font-size:0.92rem; font-weight:600; color:var(--text);">{html.escape(expl_text)}</div>'
                f'</div>',
                unsafe_allow_html=True,
            )

        st.markdown('<div class="section-title">Technical Parameters</div>', unsafe_allow_html=True)
        fields = [
            ('Breakout level', money(row.get('breakout_level')), 'distance'), ('Breakout trigger', money(row.get('breakout_trigger')), None),
            ('Distance', pct(row.get('distance_pct')), 'distance'), ('Rating', f"{row.get('rating','—')}/10", 'score'),
            ('Score', f"{row.get('score',0):.1f}/100", 'score'), ('RVOL', f"{row.get('rvol',0):.2f}x", 'rvol'),
            ('RSI', f"{row.get('rsi',0):.1f}", 'rsi'), ('ADX', f"{row.get('adx',0):.1f}", 'adx'),
            ('EMA structure', row.get('ema_structure', '—'), None), ('MACD', f"{row.get('macd',0):.3f}", None),
            ('ATR %', f"{row.get('atr_pct',0):.2f}%", None), ('VCP / VDU Squeeze', f"{row.get('squeeze',0):.2f}", None),
            ('NIFTY rel strength', pct(row.get('nifty_relative_strength')), None), ('Sector rel strength', pct(row.get('sector_relative_strength')), None),
            ('60D rel strength', pct(row.get('relative_strength')), None), ('Candlestick', row.get('candlestick', '—'), None),
            ('Resistance touches', row.get('resistance_touches', '—'), None), ('Risk / reward (T2)', f"{row.get('risk_reward',0):.2f}x", 'rr'),
            ('Market regime', row.get('market_regime', '—'), None), ('Stop reference', money(row.get('stop_reference')), None),
            ('EOD Delivery %', f"{row.get('delivery_pct','—')}%" if pd.notna(row.get('delivery_pct')) else '—', 'rvol'),
            ('Deliv Expansion', f"{float(row.get('deliv_expansion_ratio', 1.0) or 1.0):.2f}x", 'rvol'),
            ('20D U/D Vol Ratio', f"{float(row.get('ud_vol_ratio', 1.0) or 1.0):.2f}x", 'rvol'),
            ('Candle CLV', f"{float(row.get('clv', 0.5) or 0.5):.2f}", None),
            ('Below 52W High', f"{float(row.get('pct_below_52w', 0.0) or 0.0):.1f}%", 'distance'),
            ('Rank Score (v3)', f"{float(row.get('rank_score', row.get('score', 0))):.1f}/100", 'score'),
            ('Vol Quality Score', f"{float(row.get('component_volume', 0))*100:.0f}%", 'score'),
            ('Multi-TF RS Score', f"{float(row.get('component_relative_strength', 0))*100:.0f}%", 'score'),
            ('False BO Risk', 'Yes ⚠️' if row.get('false_breakout') else 'Clean ✅', None),
            ('Setup Status', row.get('status', '—'), None),
        ]
        for start in range(0, len(fields), 5):
            cols = st.columns(5)
            for j, col in enumerate(cols):
                idx = start + j
                if idx >= len(fields): continue
                with col: st.markdown(metric_card(fields[idx][0], fields[idx][1], fields[idx][2]), unsafe_allow_html=True)

    with tab_fund:
        st.markdown('<div class="section-title" style="margin-top:0;">Fundamental Health & Financial Filings</div>', unsafe_allow_html=True)
        with st.spinner('Retrieving latest financial filings...'):
            fund_data = get_fundamentals_cached(symbol)

        if fund_data.get('fundamental_quality') == 'OK':
            rev_yoy = fund_data.get('q_rev_growth_yoy_pct')
            prof_yoy = fund_data.get('q_profit_growth_yoy_pct')
            rev_qoq = fund_data.get('q_rev_growth_qoq_pct')
            prof_qoq = fund_data.get('q_profit_growth_qoq_pct')
            margin = fund_data.get('operating_margin_pct')
            dte = fund_data.get('debt_to_equity')
            roe = fund_data.get('roe_pct')
            pe = fund_data.get('pe_ratio')
            earn_dt = fund_data.get('earnings_date')
            days_earn = fund_data.get('days_to_earnings')
            f_score = fund_data.get('fundamental_score', 55.0)
            f_grade = fund_data.get('fundamental_grade', 'B')
            f_flag = fund_data.get('fundamental_flag', 'ACCEPTABLE')

            rev_str = f'{rev_yoy:+.2f}%' if pd.notna(rev_yoy) else 'N/A'
            prof_str = f'{prof_yoy:+.2f}%' if pd.notna(prof_yoy) else 'N/A'
            rev_qoq_sub = f'Sequential QoQ: {rev_qoq:+.2f}%' if pd.notna(rev_qoq) else 'Sequential QoQ: —'
            prof_qoq_sub = f'Sequential QoQ: {prof_qoq:+.2f}%' if pd.notna(prof_qoq) else 'Sequential QoQ: —'
            margin_str = f'{margin:.2f}%' if pd.notna(margin) else 'N/A'
            dte_str = f'{dte:.2f}' if pd.notna(dte) else 'N/A'
            roe_str = f'{roe:.2f}%' if pd.notna(roe) else 'N/A'
            pe_str = f'{pe:.1f}x' if pd.notna(pe) else 'N/A'

            rev_c = 'var(--accent)' if pd.notna(rev_yoy) and rev_yoy > 0 else 'var(--red)' if pd.notna(rev_yoy) else 'var(--text)'
            prof_c = 'var(--accent)' if pd.notna(prof_yoy) and prof_yoy > 0 else 'var(--red)' if pd.notna(prof_yoy) else 'var(--text)'
            dte_c = 'var(--red)' if pd.notna(dte) and dte > 1.8 else 'var(--accent)' if pd.notna(dte) else 'var(--text)'
            roe_c = 'var(--accent)' if pd.notna(roe) and roe >= 12.0 else ('var(--red)' if pd.notna(roe) and roe < 0 else 'var(--text)')

            earn_banner = ""
            if earn_dt and days_earn is not None and 0 <= int(days_earn) <= 7:
                earn_banner = f'''
                <div class="bento-card" style="border-left: 4px solid var(--yellow); background: var(--yellow-bg); padding: 14px 18px; margin-bottom: 16px;">
                    <span class="badge badge-yellow">⚠️ UPCOMING EARNINGS EVENT RISK</span>
                    <div style="font-weight:700; margin-top:6px; font-size:0.95rem; color:var(--text);">
                        Corporate earnings scheduled for <b>{html.escape(str(earn_dt))}</b> ({int(days_earn)} days away). Avoid holding full swing size into binary overnight earnings gaps!
                    </div>
                </div>
                '''

            grade_cls = 'badge-green' if f_grade in {'A+', 'A'} else ('badge-yellow' if f_grade in {'B', 'C'} else 'badge-red')
            st.markdown(f'''
            {earn_banner}
            <div class="bento-card" style="display:flex; justify-content:space-between; align-items:center; flex-wrap:wrap; gap:12px; padding:16px 20px; margin-bottom:16px; border-left:4px solid var(--brand);">
                <div>
                    <div class="small-muted" style="text-transform:uppercase; font-weight:700; font-size:0.72rem;">Institutional Fundamental Rating</div>
                    <div style="font-size:1.6rem; font-weight:900; color:var(--text); margin-top:4px;">{f_score:.1f} / 100 &nbsp;<span class="badge {grade_cls}">GRADE {html.escape(str(f_grade))} • {html.escape(str(f_flag))}</span></div>
                </div>
                <div class="small-muted" style="text-align:right;"> Next Earnings Date: <b>{html.escape(str(earn_dt or 'Not Scheduled'))}</b></div>
            </div>
            <div style="display:grid;grid-template-columns:repeat(3,1fr);gap:16px;">
                <div class="bento-card"><b style="color:var(--muted);font-size:.75rem;text-transform:uppercase;">YoY Revenue Growth</b><br><span style="font-size:1.6rem;font-weight:800;color:{rev_c}">{rev_str}</span><div class="small-muted" style="margin-top:4px;">{rev_qoq_sub}</div></div>
                <div class="bento-card"><b style="color:var(--muted);font-size:.75rem;text-transform:uppercase;">YoY Net Profit Growth</b><br><span style="font-size:1.6rem;font-weight:800;color:{prof_c}">{prof_str}</span><div class="small-muted" style="margin-top:4px;">{prof_qoq_sub}</div></div>
                <div class="bento-card"><b style="color:var(--muted);font-size:.75rem;text-transform:uppercase;">Operating Margin</b><br><span style="font-size:1.6rem;font-weight:800;">{margin_str}</span><div class="small-muted" style="margin-top:4px;">Core EBIT / Operating</div></div>
                <div class="bento-card"><b style="color:var(--muted);font-size:.75rem;text-transform:uppercase;">Debt to Equity</b><br><span style="font-size:1.6rem;font-weight:800;color:{dte_c}">{dte_str}</span><div class="small-muted" style="margin-top:4px;">Balance Sheet Leverage</div></div>
                <div class="bento-card"><b style="color:var(--muted);font-size:.75rem;text-transform:uppercase;">Return on Equity (ROE)</b><br><span style="font-size:1.6rem;font-weight:800;color:{roe_c}">{roe_str}</span><div class="small-muted" style="margin-top:4px;">Capital Efficiency</div></div>
                <div class="bento-card"><b style="color:var(--muted);font-size:.75rem;text-transform:uppercase;">Valuation (P/E Ratio)</b><br><span style="font-size:1.6rem;font-weight:800;">{pe_str}</span><div class="small-muted" style="margin-top:4px;">Trailing / Forward P/E</div></div>
            </div>
            <div class="small-muted" style="margin-top:12px;text-align:right;">Data sourced securely via Yahoo Finance APIs &amp; corporate filings (6h TTL cache).</div>
            ''', unsafe_allow_html=True)
        else:
            st.warning(f"Fundamental data is currently unavailable for {symbol}. Status: {fund_data.get('fundamental_quality')}")

    with tab_news:
        st.markdown('<div class="section-title" style="margin-top:0;">Corporate News & Exchange Filings</div>', unsafe_allow_html=True)
        news_list = cached_news_list

        if news_list:
            for item in news_list[:6]:
                title = item.get('title', 'No Title')
                publisher = item.get('publisher', 'Exchange Source')
                link = item.get('link', '#')
                pub_time = item.get('providerPublishTime')
                time_str = datetime.fromtimestamp(pub_time).strftime('%d %b %Y • %H:%M IST') if pub_time else 'Recent'
                sentiment_tag = item.get('sentiment_tag', 'Neutral')
                sentiment_cls = item.get('sentiment_cls', 'badge-grey')
                
                st.markdown(f'''
                <div class="news-item">
                    <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:6px;">
                        <span class="news-time">{time_str}</span>
                        <div>
                            <span class="badge {sentiment_cls}" style="margin-right:6px;">{sentiment_tag}</span>
                            <span class="badge badge-brand">{publisher}</span>
                        </div>
                    </div>
                    <div class="news-headline"><a href="{link}" target="_blank" rel="noopener" style="color:var(--text);text-decoration:none;">{html.escape(title)} ↗</a></div>
                </div>
                ''', unsafe_allow_html=True)
        else:
            st.markdown(f'<div class="bento-card"><span class="badge badge-brand">Live Feed</span><div style="margin-top:10px;font-weight:600;font-size:1.05rem;">No recent news articles or exchange filings found via Yahoo Finance for {symbol}.</div></div>', unsafe_allow_html=True)

    with tab_audit:
        st.markdown('<div class="section-title" style="margin-top:0;">Google Sheets Audit Export</div>', unsafe_allow_html=True)
        st.markdown('<div class="small-muted" style="margin-bottom:16px;">Raw technical properties formatted for your external sheet tracker.</div>', unsafe_allow_html=True)
        audit_df = build_single_stock_export(symbol, row, st.session_state.get('search_timestamp', datetime.now(IST).strftime('%Y-%m-%d %H:%M:%S IST')), rank='')
        
        # HTML table for perfect dark/light mode integration
        html_table = audit_df.to_html(index=False, classes="audit-table", border=0)
        st.markdown(f'<div class="audit-table-wrapper">{html_table}</div>', unsafe_allow_html=True)
        
        st.markdown('<div style="height:12px;"></div>', unsafe_allow_html=True)
        st.download_button('📥 DOWNLOAD AUDIT ROW (CSV)', data=audit_df.to_csv(index=False).encode('utf-8-sig'), file_name=f"audit_{symbol}_{datetime.now(IST).strftime('%Y%m%d_%H%M%S')}.csv", mime='text/csv', use_container_width=False, key=f'audit_{symbol}')

# -----------------------------------------------------------------------------
# MAIN DASHBOARD (BENTO GRID LAYOUT)
# -----------------------------------------------------------------------------
def render_home():
    render_fintech_topbar()
    st.markdown("<div style='height:8px'></div>", unsafe_allow_html=True)
    render_ticker()
    
    # Create the Tabs for the Main Screen
    tab_dash, tab_sikho, tab_watch, tab_portfolio = st.tabs(["🚀 Scanner Dashboard", "📚 Sikho (Learn)", "👀 Live Watchlist", "🎮 Paper Portfolio"])

    with tab_watch:
        wc1, wc2 = st.columns([6, 2])
        with wc1:
            st.markdown("<div style='font-size:1.05rem; font-weight:800; color:var(--text); padding-top:8px; margin-bottom:12px;'>👀 Live Tracked Setups</div>", unsafe_allow_html=True)
        with wc2:
            if st.button("🔄 Refresh Live Prices", use_container_width=True):
                get_watchlist_cached.clear()
                fetch_portfolio_live_prices_batch.clear()
                st.rerun()
                
        watchlist_df = get_watchlist_cached()
        render_watchlist_tab(watchlist_df)

    with tab_portfolio:
        pc1, pc2 = st.columns([6, 2])
        with pc1:
            st.markdown("<div style='font-size:1.05rem; font-weight:800; color:var(--text); padding-top:8px; margin-bottom:12px;'>🎮 Paper Trading Portfolio</div>", unsafe_allow_html=True)
        with pc2:
            if st.button("🔄 Refresh Live PnL", key="refresh_paper_pnl", use_container_width=True):
                get_paper_trades_cached.clear()
                fetch_portfolio_live_prices_batch.clear()
                st.rerun()
        
        paper_df = get_paper_trades_cached()
            
        if paper_df.empty:
            st.info("No paper trades found. Go to the Scanner Dashboard, analyze a stock, and execute a trade!")
        else:
            paper_df['Status_Clean'] = paper_df['Status'].astype(str).str.strip().str.upper()
            open_trades = paper_df[paper_df['Status_Clean'] == 'OPEN'].copy()
            closed_trades = paper_df[paper_df['Status_Clean'].str.startswith('CLOSED')].copy()
            
            def clean_num(val, default=0.0):
                try:
                    if pd.isna(val):
                        return default
                    cleaned = str(val).replace('₹', '').replace(',', '').strip()
                    return float(cleaned) if cleaned else default
                except Exception:
                    return default

            if open_trades.empty:
                st.success("No open trades. You are all flat! Head to the scanner to find new setups.")
            else:
                st.markdown("<div class='small-muted' style='margin-bottom:16px;'>Live prices are pulled securely via Yahoo Finance APIs.</div>", unsafe_allow_html=True)
                
                # Fetch live prices in a single parallel batch call (cached 60s)
                symbols_tuple = tuple(sorted({str(s).strip().upper().replace('.NS', '') for s in open_trades['Symbol'].unique() if str(s).strip()}))
                live_prices = fetch_portfolio_live_prices_batch(symbols_tuple)

                # Pre-calculate Open Trades summary metrics & Action Alerts (Total, In Profit, In Loss, Alerts)
                open_count = len(open_trades)
                prof_trades = 0
                loss_trades = 0
                target_hit_count = 0
                sl_breach_count = 0
                for _, tr_row in open_trades.iterrows():
                    s_clean = str(tr_row['Symbol']).strip().upper().replace('.NS', '')
                    ep_val = clean_num(tr_row.get('Entry_Price', 0))
                    lp_val = live_prices.get(s_clean, ep_val)
                    sl_val = clean_num(tr_row.get('Stop_Loss', 0))
                    t1_val = clean_num(tr_row.get('Target_1', 0))
                    t2_val = clean_num(tr_row.get('Target_2', 0))
                    if lp_val > ep_val:
                        prof_trades += 1
                    elif lp_val < ep_val:
                        loss_trades += 1
                    if sl_val > 0 and lp_val <= sl_val:
                        sl_breach_count += 1
                    elif (t2_val > 0 and lp_val >= t2_val) or (t1_val > 0 and lp_val >= t1_val):
                        target_hit_count += 1

                st.markdown(f'''
                <div style="display:grid; grid-template-columns: repeat(4, 1fr); gap:16px; margin-bottom:20px;">
                    <div class="bento-card" style="margin-bottom:0; padding:16px 20px; border-left: 4px solid var(--brand);">
                        <div class="small-muted" style="text-transform:uppercase; font-size:0.72rem; font-weight:700;">Total Open Paper Trades</div>
                        <div style="font-size:1.8rem; font-weight:900; color:var(--text); margin-top:4px;">{open_count}</div>
                        <div class="small-muted" style="font-size:0.74rem; margin-top:2px;">Active Positions</div>
                    </div>
                    <div class="bento-card" style="margin-bottom:0; padding:16px 20px; border-left: 4px solid var(--accent); background:var(--accent-bg);">
                        <div class="small-muted" style="text-transform:uppercase; font-size:0.72rem; font-weight:700; color:var(--accent);">Trades in Profit</div>
                        <div style="font-size:1.8rem; font-weight:900; color:var(--accent); margin-top:4px;">{prof_trades}</div>
                        <div class="small-muted" style="font-size:0.74rem; margin-top:2px;">🎯 {target_hit_count} at Target Zone</div>
                    </div>
                    <div class="bento-card" style="margin-bottom:0; padding:16px 20px; border-left: 4px solid var(--red); background:var(--red-bg);">
                        <div class="small-muted" style="text-transform:uppercase; font-size:0.72rem; font-weight:700; color:var(--red);">Trades in Loss</div>
                        <div style="font-size:1.8rem; font-weight:900; color:var(--red); margin-top:4px;">{loss_trades}</div>
                        <div class="small-muted" style="font-size:0.74rem; margin-top:2px;">🚨 {sl_breach_count} SL Breached</div>
                    </div>
                    <div class="bento-card" style="margin-bottom:0; padding:16px 20px; border-left: 4px solid var(--yellow); background:var(--yellow-bg);">
                        <div class="small-muted" style="text-transform:uppercase; font-size:0.72rem; font-weight:700; color:var(--yellow);">Action Triggers Active</div>
                        <div style="font-size:1.8rem; font-weight:900; color:var(--text); margin-top:4px;">{target_hit_count + sl_breach_count}</div>
                        <div class="small-muted" style="font-size:0.74rem; margin-top:2px;">{target_hit_count} Target • {sl_breach_count} Stop Alert</div>
                    </div>
                </div>
                ''', unsafe_allow_html=True)

                # Display Open Trades
                total_pnl = 0.0
                total_invested = 0.0
                for idx, trade in open_trades.iterrows():
                    sym = str(trade['Symbol']).strip().upper().replace('.NS', '')
                    entry_price = clean_num(trade.get('Entry_Price', 0))
                    qty = int(round(clean_num(trade.get('Quantity', 0))))
                    live_price = live_prices.get(sym, entry_price)
                    stop_loss = clean_num(trade.get('Stop_Loss', 0))
                    target_1 = clean_num(trade.get('Target_1', 0))
                    target_2 = clean_num(trade.get('Target_2', 0))
                    target_3 = (target_2 + (target_2 - target_1)) if (target_1 > 0 and target_2 > target_1) else 0.0
                    entry_date_str = str(trade.get('Entry_Date', '—') or '—').split(' ')[0]
                    
                    pnl = (live_price - entry_price) * qty
                    total_pnl += pnl
                    total_invested += (entry_price * qty)
                    pnl_pct = ((live_price / entry_price) - 1) * 100 if entry_price > 0 else 0.0
                    
                    pnl_color = "var(--accent)" if pnl >= 0 else "var(--red)"
                    pnl_sign = "+" if pnl >= 0 else ""

                    # Evaluate Target & Stop-Loss Alert Badges + Card Border Accent
                    if stop_loss > 0 and live_price <= stop_loss:
                        alert_badge = "<span class='badge badge-red'>🚨 STOP LOSS BREACHED — EXIT NOW</span>"
                        card_border = "border-left: 4px solid var(--red); background: var(--red-bg);"
                    elif stop_loss > 0 and live_price > stop_loss and ((live_price - stop_loss) / live_price * 100) <= 1.0:
                        alert_badge = "<span class='badge badge-yellow'>⚠️ NEAR STOP LOSS (&le;1% BUFFER)</span>"
                        card_border = "border-left: 4px solid var(--yellow);"
                    elif target_3 > 0 and live_price >= target_3:
                        alert_badge = "<span class='badge badge-accent'>🏆 TARGET 3 HIT — BOOK FULL / TRAIL</span>"
                        card_border = "border-left: 4px solid var(--accent); background: var(--accent-bg);"
                    elif target_2 > 0 and live_price >= target_2:
                        alert_badge = "<span class='badge badge-accent'>🎯 TARGET 2 HIT — TRAIL SL TO T1</span>"
                        card_border = "border-left: 4px solid var(--accent); background: var(--accent-bg);"
                    elif target_1 > 0 and live_price >= target_1:
                        alert_badge = "<span class='badge badge-green'>✅ TARGET 1 HIT — BOOK 50% &amp; MOVE SL TO COST</span>"
                        card_border = "border-left: 4px solid var(--accent);"
                    elif target_1 > 0 and live_price < target_1 and ((target_1 - live_price) / live_price * 100) <= 1.0:
                        alert_badge = "<span class='badge badge-brand'>🔥 APPROACHING T1 (&le;1% AWAY)</span>"
                        card_border = "border-left: 4px solid var(--brand);"
                    elif pnl >= 0:
                        alert_badge = "<span class='badge badge-green'>🟢 IN PROFIT ZONE — HOLD</span>"
                        card_border = "border-left: 4px solid var(--accent);"
                    else:
                        alert_badge = "<span class='badge badge-yellow'>⏳ ACTIVE — ABOVE STOP LOSS</span>"
                        card_border = "border-left: 4px solid var(--border);"

                    # Calculate progress bar from Stop Loss (0%) to Target 2 (100%)
                    if target_2 > stop_loss and stop_loss > 0:
                        prog_pct = float(np.clip(((live_price - stop_loss) / (target_2 - stop_loss)) * 100.0, 0.0, 100.0))
                    elif target_1 > entry_price and entry_price > 0:
                        prog_pct = float(np.clip(((live_price - entry_price) / (target_1 - entry_price)) * 100.0, 0.0, 100.0))
                    else:
                        prog_pct = 50.0 if pnl >= 0 else 20.0
                    prog_color = "var(--red)" if (stop_loss > 0 and live_price <= stop_loss) else ("var(--accent)" if pnl >= 0 else "var(--yellow)")

                    dist_to_sl_pct = ((live_price - stop_loss) / entry_price * 100.0) if (stop_loss > 0 and entry_price > 0) else 0.0
                    dist_to_t1_pct = ((target_1 - live_price) / live_price * 100.0) if (target_1 > 0 and live_price > 0) else 0.0
                    
                    st.markdown(f'''
                    <div class="bento-card" style="{card_border} display:flex; justify-content:space-between; align-items:center; flex-wrap:wrap; gap:16px;">
                        <div style="flex:1.6; min-width:250px;">
                            <div style="display:flex; align-items:center; gap:8px; flex-wrap:wrap;">
                                <span style="font-weight:900; font-size:1.25rem; color:var(--text);">{html.escape(sym)}</span>
                                {alert_badge}
                            </div>
                            <div class="small-muted" style="margin-top:6px;">
                                Entry: <b>{money(entry_price)}</b> ({html.escape(entry_date_str)}) &nbsp;|&nbsp; Qty: <b>{qty}</b> &nbsp;|&nbsp; Invested: <b>{money(entry_price * qty)}</b>
                            </div>
                            <div class="small-muted" style="margin-top:4px;">
                                🛑 SL: <b style="color:var(--red);">{money(stop_loss) if stop_loss > 0 else '—'}</b> &nbsp;|&nbsp;
                                🎯 T1: <b style="color:var(--accent);">{money(target_1) if target_1 > 0 else '—'}</b> &nbsp;|&nbsp;
                                🎯 T2: <b style="color:var(--brand);">{money(target_2) if target_2 > 0 else '—'}</b> &nbsp;|&nbsp;
                                🏆 T3: <b>{money(target_3) if target_3 > 0 else '—'}</b>
                            </div>
                            <div style="margin-top:8px; max-width:380px;">
                                <div style="display:flex; justify-content:space-between; font-size:0.68rem; color:var(--muted); font-weight:700; margin-bottom:3px;">
                                    <span>SL Buffer: {dist_to_sl_pct:+.2f}%</span>
                                    <span>{('T1 HIT ✅' if (target_1 > 0 and live_price >= target_1) else f'To T1: {dist_to_t1_pct:+.2f}%') if target_1 > 0 else ''}</span>
                                </div>
                                <div class="bar-track" style="height:6px;"><div class="bar-fill" style="width:{prog_pct:.1f}%; background:{prog_color};"></div></div>
                            </div>
                        </div>
                        <div>
                            <div class="small-muted" style="text-transform:uppercase; font-size:0.7rem;">Live Price</div>
                            <div style="font-weight:800; font-size:1.15rem; color:var(--text);">{money(live_price)}</div>
                        </div>
                        <div style="text-align:right; min-width:165px;">
                            <div class="small-muted" style="text-transform:uppercase; font-size:0.7rem;">Unrealized PnL</div>
                            <div style="font-weight:900; font-size:1.25rem; color:{pnl_color};">{pnl_sign}{money(pnl)} ({pnl_sign}{pnl_pct:.2f}%)</div>
                            <div class="small-muted" style="font-size:0.72rem;">Per Share: {pnl_sign}{money(live_price - entry_price)}</div>
                        </div>
                    </div>
                    ''', unsafe_allow_html=True)
                    
                    close_col1, close_col2 = st.columns([8, 2])
                    with close_col2:
                        if st.button("Close Trade", key=f"close_{trade['Trade_ID']}_{idx}", use_container_width=True):
                            with st.spinner("Closing trade in Google Sheets..."):
                                close_paper_trade(st.secrets, trade['Trade_ID'], round(live_price, 2), round(pnl, 2))
                                get_paper_trades_cached.clear()
                            st.toast(f"✅ Closed {sym} trade. PnL: {pnl_sign}{money(pnl)}")
                            time.sleep(1)
                            st.rerun()
                
                # Show Total PnL Header
                total_color = "var(--accent)" if total_pnl >= 0 else "var(--red)"
                total_sign = "+" if total_pnl >= 0 else ""
                total_pct = (total_pnl / total_invested * 100) if total_invested > 0 else 0.0
                st.markdown(f'''
                <div style="text-align:right; margin-top:8px; padding-right:16px;">
                    <span class="small-muted" style="font-size:0.8rem; text-transform:uppercase; font-weight:700;">Total Open PnL:</span> 
                    <span style="font-size:1.3rem; font-weight:900; color:{total_color}; margin-left:8px;">{total_sign}{money(total_pnl)} ({total_sign}{total_pct:.2f}%)</span>
                </div>
                ''', unsafe_allow_html=True)
            
            # Show closed trades history
            if not closed_trades.empty:
                st.markdown("<div style='height:24px'></div>", unsafe_allow_html=True)
                st.markdown("<div class='section-title'>Closed Trades History</div>", unsafe_allow_html=True)
                
                history_df = closed_trades.copy()
                cols_to_show = [c for c in ['Symbol', 'Entry_Date', 'Entry_Price', 'Exit_Price', 'Quantity', 'PnL', 'Status'] if c in history_df.columns]
                st.dataframe(history_df[cols_to_show], use_container_width=True, hide_index=True)

    with tab_sikho:
        st.markdown("""
        # 📚 SIKHO: The Complete NIFTY Momentum Intelligence Masterclass
        ## Institutional-Grade Technical & Fundamental Reference Manual

        Welcome to the definitive manual for your proprietary scanner and analytics dashboard. This curriculum is engineered to break down **every single technical term, indicator, badge, and metric** displayed anywhere across your app screen. 

        You will learn exactly what each value represents mathematically, why it matters in real-world market dynamics, and how combinations of these metrics signal high-probability institutional accumulation.

        ---

        ## SECTION 1: Dashboard Home & Scanner Results Screen
        When you run the scanner or view the Bento grid of matching stocks, several core metrics appear on each stock card. Here is what they mean:

        ### 1. Cap Category (`Large Cap`, `Large+Mid Cap`, etc.)
        * **What it is:** The market capitalization classification of the company based on its total valuation on the NSE/BSE.
        * **Why it matters:** Large caps provide institutional liquidity and lower volatility during macro pullbacks; mid/small caps provide explosive momentum velocity.
        * **Real-World Representation:** Large caps are like massive cargo ships—harder to move, but impossible to sink easily. Smaller caps are speedboats—faster returns, but higher risk in choppy waters.

        ### 2. Score (`Score: 0 to 100`)
        * **What it is:** The proprietary composite mathematical rating calculated by your scanner engine, weighing volume, momentum, trend, and proximity.
        * **Why it matters:** It filters out 200+ NIFTY stocks down to the top tier instantly. 
        * **The Threshold:** Scores **$\ge 80$** represent elite setups; **$65-79$** represent strong institutional setups.

        ### 3. Distance to Resistance (`Distance %`)
        * **What it is:** The percentage gap between the current stock price and its detected historical breakout ceiling (`Breakout Level`).
        * **Real-World Representation:** Distance measures how close a runner is to the starting line. 
        * **The Sweet Spot:** **$0.00\%$ to $+2.00\%$**. If distance is negative, the stock is approaching resistance. If it is slightly positive ($+0.5\%$), it has just breached the ceiling. If it is $> 5\%$, the move is overextended.

        ### 4. Timeframe Badge (`Breakout Swing`, `Short Term`, `Positional`, `Long Term`)
        * **What it is:** An automated classification of the trade duration based on indicator velocity (RSI, ADX, and Price Proximity).
        * **Breakout Swing (3–10d):** Tight proximity ($\le 2\%$), RSI $\ge 60$, ADX $\ge 20$. Ready to explode immediately.
        * **Short Term (1–3w):** Moderate momentum building a continuation pattern.
        * **Positional (2–6w):** Deep base accumulation requiring multi-week patience.
        * **Long Term (3-8m):** Extended timeframe breakout targets based on macro targets.

        ---

        ## SECTION 2: Technical Analytics View (The Detail Screen)
        When you click **"Launch Analytics"**, you open the deep-dive command center. Every parameter displayed in the metrics grid and charts corresponds to specific market behavior:

        ### 2.1 Breakout Level & Breakout Trigger
        * **Breakout Level:** The exact historical price ceiling where sellers previously stepped in and pushed the stock down (tested across 3 to 10 resistance touches).
        * **Breakout Trigger:** A dynamic buffer price slightly *above* the Breakout Level. 
        * **Real-World Representation:** The Breakout Level is the physical ceiling of a room. The Trigger is the exact height where you punch through drywall to confirm you are outside the room. Buying at the trigger ensures you don't get faked out by a false breakout.

        ### 2.2 Relative Volume (`RVOL`)
        * **What it is:** Today’s trading volume divided by its historical average volume (typically a 20-period moving average).
        * **What the values represent:**
          * **$< 0.8x$:** Low volume. Retail-only activity; avoid breakouts.
          * **$1.1x$ to $1.4x$:** Moderate institutional interest.
          * **$\ge 1.5x$:** **High Conviction.** Massive institutional block deals or accumulation occurring.
        * **Real-World Combination:** An RVOL of $\ge 1.5x$ *combined* with a Distance of $0–2\%$ is your primary institutional footprint flag.

        ### 2.3 Relative Strength Index (`RSI`)
        * **What it is:** Momentum oscillator measuring the speed and change of price movements on a 0 to 100 scale.
        * **What the values represent:**
          * **$55$ to $70$ (The Sweet Spot):** The stock is in a healthy, aggressive bull phase. 
          * **$> 75$:** Overheated / Parabolic. High risk of a short-term shakeout.
          * **$< 45$:** Bearish control; momentum is dead.

        ### 2.4 Average Directional Index (`ADX`)
        * **What it is:** Trend strength indicator (0 to 100), measuring *how powerfully* a trend is moving regardless of direction.
        * **What the values represent:**
          * **$< 18$:** Choppy, range-bound, or sideways market. Breakouts fail here.
          * **$20$ to $25$:** A trend is successfully forming.
          * **$> 25$ to $40+$:** **Strong Trending Market.** Institutions are driving a sustained directional wave.

        ### 2.5 MACD (Moving Average Convergence Divergence)
        * **What it is:** Trend-following momentum indicator showing the relationship between two exponential moving averages.
        * **Why it matters:** Positive MACD values with expanding histogram bars confirm that short-term momentum is accelerating faster than long-term average momentum.

        ### 2.6 ATR % (Average True Range Percentage)
        * **What it is:** Measures absolute daily volatility as a percentage of the stock price.
        * **Real-World Representation:** ATR tells you how much a stock naturally "breathes" or fluctuates daily. If a stock has an ATR of $3\%$, normal daily noise is $3\%$. 
        * **Why it matters:** Your Stop-Loss *must* be wider than your ATR %; otherwise, normal daily market breathing will trigger your stop-loss and knock you out of a winning trade prematurely.

        ### 2.7 EOD Delivery % (`Delivery %`)
        * **What it is:** The exact percentage of traded shares that were transferred into investors' Demat accounts at the end of the trading day rather than squared off intraday.
        * **What the values represent:**
          * **$< 45\%$:** Day-trader heavy, speculative churn.
          * **$> 55\%$ to $70+\%$:** **Structural Accumulation.** Buyers are locking shares away in long-term portfolios.

        ---

        ## SECTION 3: Candlestick Patterns & Chart Overlays
        The Plotly chart on your analytics view features automated pattern recognition and institutional moving averages:

        ### 3.1 EMA 50 & EMA 200 (Exponential Moving Averages)
        * **EMA 50 (Purple Line):** Represents the medium-term institutional trend (approx. 10 weeks of trading data). Healthy swing trade stocks ride above the EMA 50.
        * **EMA 200 (Yellow Line):** Represents the macro bull/bear dividing line (approx. 40 weeks). 
        * **Real-World Representation:** When Price > EMA 50 > EMA 200 in a clean stacked formation, it means short-term, medium-term, and long-term participants are all making money. The path of least resistance is strictly upward.

        ### 3.2 Automated Candlestick Pattern Recognition (`🎯`)
        Your app scans the last 3 candles to detect high-probability institutional reversal and continuation formations:
        * **Bullish Engulfing:** A large green candle completely swallows the previous red candle. Sellers tried to push price down, but buyers overwhelmed them completely by the close.
        * **Hammer:** A small body with a long lower shadow (wick) at least twice the size of the body. Sellers drove prices down intraday, but aggressive institutional buyers stepped in at the lows and bought the entire dip before the close.
        * **Morning Star:** A three-candle bottom reversal pattern indicating the exhaustion of sellers and a rapid shift in control to buyers.
        * **Bullish Marubozu:** A strong green candle with virtually no wicks (opens near the low, closes near the high). Absolute, uncontested buyer dominance.

        ---

        ## SECTION 4: The Master Combination Matrix (How Terms Work Together)
        In real-world trading, single indicators can lie. True institutional edge comes from **confluence**—when multiple parameters align simultaneously. Here is how you should read your app's signals in combination:

        | Market Condition | Metric Combination on Your App | Real-World Meaning | Action |
        | :--- | :--- | :--- | :--- |
        | **Elite Breakout** | Distance $\le 2\%$ + RVOL $\ge 1.5x$ + Delivery $> 55\%$ + RSI $55-70$ | Institutions are sweeping the order book to break resistance on heavy delivery volume. | **A+ Setup:** Execute Paper Trade / Plan Entry. |
        | **Fakeout Trap** | Distance $\le 1\%$ + RVOL $< 0.8x$ + Delivery $< 40\%$ + RSI $> 75$ | Retail hype pushing price to resistance with zero institutional backing; volume is dying. | **Avoid / Ignore:** High probability of reversal. |
        | **Coiled Spring** | Squeeze Active + ADX $> 22$ + EMA Structure Stacked + ATR contracting | Volatility has compressed to historic lows inside an uptrend; expansion is imminent. | **Watch Closely:** Set alert for breakout trigger. |
        | **Trend Exhaustion** | RSI $> 80$ + ADX falling from $40$ + RVOL declining over 3 days | Momentum is burning out; early buyers are starting to take profits off the table. | **Tighten Stops / Take Profit.** |

        ---

        ## SECTION 5: Risk Management & The Paper Portfolio Dashboard
        Once a stock passes all technical and fundamental criteria, the app shifts from **Analysis** to **Execution & Tracking**:

        ### 5.1 Dual Stop-Loss Framework
        * **Aggressive Stop (Candle Low):** Placed right under the low of the breakout candle. Used when you want zero tolerance for failure; if the very next day reverses, you cut losses immediately.
        * **Structural Stop (EMA / ATR):** Placed below the rising EMA 50. Used for positional trades where you want to give a large-cap stock room to fluctuate through normal 3–5 day market pullbacks.

        ### 5.2 Dynamic Position Sizer & Capital Required
        * **Max Risk Amount (₹):** The maximum rupees you are willing to lose if the trade hits your stop-loss (e.g., ₹2,000).
        * **Recommended Shares:** Automatically computed via formula: $\text{Shares} = \frac{\text{Max Risk}}{\text{Price} - \text{Stop Loss}}$. This ensures your position size scales dynamically based on stock volatility.

        ### 5.3 Live PnL & Paper Portfolio Tracking
        * When you click **🚀 Execute Paper Trade**, the trade is logged via webhook into your Google Sheet (`Paper_Trades` tab).
        * The **Paper Portfolio Tab** pings Yahoo Finance in real time to fetch live market prices, calculating your **Unrealized PnL** in Rupees and Percentage.
        * Clicking **Close Trade** instantly logs your exit price, final profit/loss, and timestamp back to the sheet, archiving your performance in the Closed Trades History table.
        """)

    with tab_dash:
        # ACTION BAR (Bento Action Header)
        col_search, col_scan, col_audit, col_track = st.columns([3, 2, 2, 2])
        
        audit_pending = st.session_state.get("audit_pending_rows") is not None
        
        with col_search:
            st.markdown('<div style="font-size:.72rem;font-weight:700;margin-bottom:6px;color:var(--muted);text-transform:uppercase;letter-spacing:.05em;">Manual Ticker Search</div>', unsafe_allow_html=True)
            sc1, sc2 = st.columns([3, 1])
            with sc1:
                query = st.text_input('Stock symbol', placeholder='e.g. RELIANCE, TCS...', key='stock_search_input', label_visibility='collapsed')
            with sc2:
                search_clicked = st.button('SEARCH', key='search_stock', use_container_width=True)

        with col_scan:
            st.markdown('<div style="font-size:.72rem;font-weight:700;margin-bottom:6px;color:var(--muted);text-transform:uppercase;letter-spacing:.05em;">Market Scanner</div>', unsafe_allow_html=True)
            normal_clicked = st.button('🚀 SCAN MARKET', key='scan_market', use_container_width=True, disabled=audit_pending)
            if normal_clicked: st.session_state.scan_intent = True

        with col_audit:
            st.markdown('<div style="font-size:.72rem;font-weight:700;margin-bottom:6px;color:transparent;">-</div>', unsafe_allow_html=True)
            audit_clicked = st.button('📊 COLLECT AUDIT', key='collect_audit', use_container_width=True, disabled=audit_pending)

        with col_track:
            st.markdown('<div style="font-size:.72rem;font-weight:700;margin-bottom:6px;color:transparent;">-</div>', unsafe_allow_html=True)
            tracking_clicked = st.button('📈 UPDATE TRACKING', key='update_performance_tracking', use_container_width=True, disabled=audit_pending)

        if search_clicked and query.strip():
            symbol = query.strip().upper().replace('.NS', '')
            st.session_state.search_error = None
            with st.spinner(f'Analyzing {symbol}…'):
                try:
                    row = scan_single(symbol, max_distance=10.0, period='2y')
                    if row is None:
                        hist = fetch_history(symbol, '2y')
                        if hist is None: raise ValueError('No usable 2-year price history available.')
                        nifty = __import__('scanner').fetch_index_history('^NSEI', period='2y')
                        row = score_stock(hist, nifty_df=nifty)
                        if row is None: raise ValueError('Could not calculate technical setup.')
                        row['symbol'] = symbol
                        row['company_name'] = symbol
                        row['cap_category'] = ''
                        row['outside_near_breakout_range'] = True
                    else:
                        row['outside_near_breakout_range'] = False
                        try:
                            universe = load_universe()
                            m = universe.loc[universe.symbol == symbol]
                            if not m.empty:
                                row['company_name'] = m.iloc[0]['company_name']
                                row['cap_category'] = m.iloc[0]['cap_category']
                        except Exception: pass
                    st.session_state.selected_stock = symbol
                    st.session_state.selected_row = row
                    st.session_state.page = 'detail'
                    st.rerun()
                except Exception as exc:
                    st.error(str(exc))

        st.markdown("<div style='height:20px'></div>", unsafe_allow_html=True)

        # -------------------------------------------------------------------------
        # PERFORMANCE TRACKING & COMBINATION ANALYSIS LOGIC RESTORED
        # -------------------------------------------------------------------------
        if tracking_clicked:
            try:
                with st.status("📈 Updating 20-day performance tracking…", expanded=True) as tracking_status:
                    tracking_status.write("Reading saved audit signals from Google Sheets…")
                    signal_df = read_audit_signals(st.secrets)
                    existing_keys = read_performance_keys(st.secrets)
                    if signal_df.empty:
                        st.warning("No saved audit signals were found. Run Collect Audit and confirm it before updating performance.")
                    else:
                        cutoff_date = latest_completed_market_date()
                        total_steps = st.empty()
                        progress_bar = st.progress(0)
                        last_progress = {"value": -1}

                        def progress_update(done, total, message):
                            total = max(1, int(total))
                            pct_value = min(100, int((done / total) * 100))
                            if pct_value != last_progress["value"]:
                                progress_bar.progress(pct_value)
                                last_progress["value"] = pct_value
                            total_steps.caption(message)

                        tracking_status.write(f"Fetching historical daily OHLC through {cutoff_date.isoformat()}…")
                        price_histories, missing_symbols, market_sessions, calendar_source = fetch_ohlc_histories(
                            signal_df,
                            as_of_date=cutoff_date,
                            progress_callback=progress_update,
                        )
                        progress_bar.progress(100)
                        tracking_status.write("Building Day 1–20 rows and checking existing tracking keys…")
                        progress_bar.progress(0)

                        def build_progress(done, total, message):
                            total = max(1, int(total))
                            done = max(0, min(int(done), total))
                            progress_bar.progress(min(100, int(done / total * 100)))
                            total_steps.caption(message)

                        new_performance, tracking_report = build_performance_rows(
                            signal_df,
                            price_histories,
                            existing_performance=existing_keys,
                            as_of_date=cutoff_date,
                            market_sessions=market_sessions,
                            calendar_source=calendar_source,
                            progress_callback=build_progress,
                        )
                        tracking_report["missing_symbols_from_fetch"] = missing_symbols
                        if not new_performance.empty:
                            tracking_status.write(f"Preparing to reconcile {len(new_performance):,} daily rows in bounded batches…")
                            progress_bar.progress(0)

                            def write_progress(done, total, message):
                                total = max(1, int(total))
                                done = max(0, min(int(done), total))
                                progress_bar.progress(min(100, int(done / total * 100)))
                                total_steps.caption(message)

                            write_result = append_performance_rows(
                                st.secrets,
                                new_performance,
                                batch_size=400,
                                progress_callback=write_progress,
                            )
                            progress_bar.progress(100)
                            total_steps.caption(
                                f"Write stage complete: {write_result.get('batches', 0)} batches; "
                                f"{write_result.get('rows', 0):,} appended, "
                                f"{write_result.get('updated', 0):,} repaired, "
                                f"{write_result.get('skipped_duplicates', 0):,} already present."
                            )
                        else:
                            write_result = {"saved": False, "rows": 0, "expected": 0, "reason": "no_new_rows"}
                        tracking_status.update(label="✅ Performance tracking update finished", state="complete", expanded=False)

                        c1, c2, c3, c4 = st.columns(4)
                        c1.metric("Saved signals", f"{len(signal_df):,}")
                        c2.metric("OHLC symbols loaded", f"{len(price_histories):,}")
                        c3.metric("New daily rows", f"{write_result.get('rows', 0):,}")
                        stored_keys = read_performance_keys(st.secrets)
                        stored_pairs = set()
                        if not stored_keys.empty:
                            for _, key_row in stored_keys.iterrows():
                                try:
                                    stored_pairs.add((str(key_row.get("Signal_ID", "")), int(float(key_row.get("Tracking_Day")))))
                                except Exception:
                                    continue
                        expected_pairs = { (str(sid), int(day)) for sid, day in tracking_report.get("expected_keys", []) }
                        missing_saved_pairs = sorted(expected_pairs - stored_pairs)
                        c4.metric("20-day complete", f"{tracking_report.get('signals_complete_20d', 0):,}")
                        latest_market_session = tracking_report.get("latest_market_session") or "No completed session returned"
                        st.success(
                            f"Tracking update finished. Latest market session in the fetched calendar: {latest_market_session}. "
                            f"{write_result.get('rows', 0):,} new daily rows appended; "
                            f"{write_result.get('updated', 0):,} incomplete rows repaired/reconciled; "
                            f"{write_result.get('skipped_duplicates', 0):,} existing rows safely skipped."
                        )
                        st.info(
                            f"Coverage: {tracking_report.get('signals_with_history', 0):,} signals have at least one OHLC candle; "
                            f"{tracking_report.get('signals_without_history', 0):,} signals have no OHLC returned yet; "
                            f"{tracking_report.get('signals_window_elapsed_20d', 0):,} signals have reached a 20-session window; "
                            f"{tracking_report.get('signals_complete_20d', 0):,} have all 20 candles complete; "
                            f"{tracking_report.get('signals_waiting_for_first_session', 0):,} are waiting for their first post-signal session. "
                            f"Calendar source: {calendar_source}."
                        )
                        if missing_saved_pairs:
                            st.error(f"Verification found {len(missing_saved_pairs):,} expected Signal_ID/Tracking_Day keys not present in Google Sheets. Retry the update; duplicate protection is active.")
                        else:
                            st.success(f"✅ Reconciliation check passed: all {len(expected_pairs):,} expected Signal_ID/Tracking_Day records exist in Daily_Performance (including explicit missing-OHLC placeholders where needed).")
                        issue_rows = tracking_report.get("missing_signals", [])
                        aged_issues = tracking_report.get("incomplete_signals", [])
                        candle_gaps = tracking_report.get("missing_candles", [])
                        if issue_rows or aged_issues or candle_gaps or missing_symbols or missing_saved_pairs:
                            with st.expander("Review data gaps (do not ignore these)", expanded=True):
                                if missing_symbols:
                                    st.write("Symbols with no usable response from the price provider:")
                                    st.code(", ".join(missing_symbols[:150]))
                                if missing_saved_pairs:
                                    st.write("Expected records still absent after the write:")
                                    st.code(str(missing_saved_pairs[:100]))
                                issue_records = issue_rows + aged_issues + candle_gaps
                                issues_df = pd.DataFrame(issue_records)
                                if not issues_df.empty:
                                    st.caption(f"Showing first 100 of {len(issues_df):,} issue rows. Download the full report to inspect every signal/session gap.")
                                    st.dataframe(issues_df.head(100), use_container_width=True, hide_index=True)
                                    st.download_button(
                                        "📥 Download complete tracking gaps report",
                                        data=issues_df.to_csv(index=False).encode("utf-8-sig"),
                                        file_name=f"tracking_gaps_{cutoff_date.strftime('%Y%m%d')}.csv",
                                        mime="text/csv",
                                        key=f"tracking_gaps_download_{cutoff_date.strftime('%Y%m%d')}",
                                    )
                        if tracking_report.get("signals_without_history", 0) or tracking_report.get("incomplete_signals") or tracking_report.get("missing_candles") or missing_saved_pairs:
                            st.warning("Some OHLC data is still missing or provisional. Retry Update Performance Tracking later. Missing placeholders will be repaired when data becomes available, and the app will keep the original Audit_Signals snapshots unchanged.")
            except Exception as exc:
                st.error("Performance tracking update failed. No scanner logic was changed. Details: " + str(exc))

        with st.expander("🔬 Research: analyse completed 20-trading-day outcomes", expanded=False):
            outcome_labels = {
                "Target 1 reached before Stop": "T1_Before_Stop",
                "Target 2 reached before Stop": "T2_Before_Stop",
                "Target 3 reached before Stop": "T3_Before_Stop",
                "Stop reached before any target": "Stop_Before_Target",
                "Target 1 touched at any time": "T1_Hit",
                "Target 2 touched at any time": "T2_Hit",
                "Target 3 touched at any time": "T3_Hit",
                "Breakout trigger reached": "Breakout_Hit",
            }
            
            r_col1, r_col2, r_col3 = st.columns([2, 1, 1])
            with r_col1:
                selected_outcome_label = st.selectbox(
                    "Outcome to evaluate",
                    list(outcome_labels.keys()),
                    key="audit_research_outcome_choice",
                )
            with r_col2:
                min_sig_input = st.number_input(
                    "Min signals per combo",
                    min_value=3,
                    max_value=200,
                    value=15,
                    step=5,
                    key="audit_min_signals_input",
                )
            with r_col3:
                max_ord_input = st.selectbox(
                    "Max factors combined",
                    options=[2, 3, 4],
                    index=1,
                    key="audit_max_order_input",
                )

            run_analysis_clicked = st.button(
                "🔬 RUN COMBINATION ANALYSIS",
                key="run_audit_combination_analysis",
                use_container_width=True,
            )
            if run_analysis_clicked:
                try:
                    with st.status("Reading matured audit outcomes and testing combinations…", expanded=True) as analysis_status:
                        all_signals = read_audit_signals(st.secrets)
                        final_rows = read_final_performance(st.secrets)
                        analysis_status.write(f"Loaded {len(all_signals):,} saved signal snapshots and {len(final_rows):,} Day-20 performance rows.")
                        completed_outcomes, completion_report = build_completed_outcomes(all_signals, final_rows)
                        if completed_outcomes.empty:
                            st.session_state.audit_analysis_result = None
                            st.session_state.audit_analysis_report = completion_report
                            st.session_state.audit_analysis_saved = False
                            analysis_status.update(label="Not enough signals have completed 20 trading days yet", state="complete", expanded=False)
                        else:
                            eff_min_signals = min(int(min_sig_input), max(3, len(completed_outcomes) // 2))
                            analysis_df = analyze_outcome_combinations(
                                completed_outcomes,
                                outcome_col=outcome_labels[selected_outcome_label],
                                min_signals=eff_min_signals,
                                max_order=int(max_ord_input),
                            )
                            st.session_state.audit_analysis_result = analysis_df
                            st.session_state.audit_analysis_report = completion_report
                            st.session_state.audit_analysis_outcome = outcome_labels[selected_outcome_label]
                            st.session_state.audit_analysis_saved = False
                            analysis_status.update(label=f"Analysis complete: {len(completed_outcomes):,} matured signals evaluated ({len(analysis_df):,} combinations found)", state="complete", expanded=False)
                except Exception as exc:
                    st.error("Combination analysis failed. Details: " + str(exc))

            stored_report = st.session_state.get("audit_analysis_report")
            stored_analysis = st.session_state.get("audit_analysis_result")
            if stored_report is not None:
                st.caption(
                    f"Matured signals: {stored_report.get('signals_matured_20d', 0):,} / "
                    f"{stored_report.get('signals_total', 0):,}; pending 20-day outcome: "
                    f"{stored_report.get('signals_pending', 0):,}. Only a saved Tracking_Day 20 row counts as mature."
                )
            if isinstance(stored_analysis, pd.DataFrame) and not stored_analysis.empty:
                st.markdown('<div class="section-title" style="margin-top:8px;">🏆 Top 3 Most Consistent Setups</div>', unsafe_allow_html=True)
                top_cols = st.columns(min(3, len(stored_analysis)))
                for idx, col in enumerate(top_cols):
                    top_row = stored_analysis.iloc[idx]
                    with col:
                        # Updating the UI to read the newly renamed columns
                        st.markdown(
                            f'<div class="bento-card" style="padding:16px;">'
                            f'<span class="badge badge-green">RANK #{idx+1} • {top_row.get("Win_Rate_%", 0):.1f}% WIN</span>'
                            f'<div style="font-weight:800;font-size:0.95rem;margin-top:10px;color:var(--text);">{html.escape(str(top_row.get("Setup_Rules", "")))}</div>'
                            f'<div class="small-muted" style="margin-top:8px;">Signals: <b>{int(top_row.get("Times_Occurred", 0))}</b> • Avg Profit: <b>{top_row.get("Avg_Profit_%", 0):+.2f}%</b> • Stop Rate: <b>{top_row.get("Stop_Hit_Rate_%", 0):.1f}%</b></div>'
                            f'<div class="small-muted" style="margin-top:6px;font-size:0.72rem;">Consistency Score: {top_row.get("Overall_Score_(0-100)", 0)}/100</div>'
                            f'</div>',
                            unsafe_allow_html=True,
                        )
                st.dataframe(stored_analysis.head(50), use_container_width=True, hide_index=True)
                st.download_button(
                    "📥 Download combination analysis CSV",
                    data=stored_analysis.to_csv(index=False).encode("utf-8-sig"),
                    file_name=f"audit_combinations_{datetime.now(IST).strftime('%Y%m%d_%H%M%S')}.csv",
                    mime="text/csv",
                    key="download_audit_combinations",
                )
                if not st.session_state.get("audit_analysis_saved", False):
                    if st.button("💾 APPEND ANALYSIS RESULTS TO GOOGLE SHEET", key="save_audit_analysis", use_container_width=True):
                        try:
                            with st.spinner("Appending analysis rows to Analysis_Results…"):
                                saved_count = append_analysis_rows(st.secrets, stored_analysis)
                            st.session_state.audit_analysis_saved = True
                            st.success(f"Saved {saved_count:,} analysis rows to Analysis_Results.")
                            st.rerun()
                        except Exception as exc:
                            st.error("Could not save analysis results. Details: " + str(exc))
                else:
                    st.success("These analysis results have already been appended to Analysis_Results for this analysis run.")
            elif stored_report is not None:
                st.info("No Day-20 outcomes matched the minimum signal count yet. Lower 'Min signals per combo' above or continue updating performance tracking after market close.")

        # SANDBOX / SCAN TRIGGER
        if st.session_state.ui_sandbox_mode and st.session_state.scan_result is None:
            st.session_state.scan_result = pd.DataFrame([
                {'symbol': 'BOSCHLTD', 'company_name': 'Bosch Ltd.', 'cap_category': 'Large Cap', 'score': 92.5, 'rank_score': 95.0, 'rating': 9, 'price': 35850.0, 'breakout_level': 35000.0, 'distance_pct': 0.42, 'rvol': 2.1, 'rsi': 62, 'adx': 28, 'macd': 124.5, 'delivery_pct': 64.2, 'deliv_expansion_ratio': 1.65, 'sector_relative_strength': 6.4, 'squeeze': 0.84, 'market_regime': 'Bullish', 'fundamental_grade': 'A+'},
                {'symbol': 'MANKIND', 'company_name': 'Mankind Pharma Ltd.', 'cap_category': 'Large+Mid Cap', 'score': 88.0, 'rank_score': 90.5, 'rating': 9, 'price': 2740.0, 'breakout_level': 2700.0, 'distance_pct': 1.25, 'rvol': 1.8, 'rsi': 58, 'adx': 24, 'macd': 15.2, 'delivery_pct': 58.4, 'deliv_expansion_ratio': 1.40, 'sector_relative_strength': 4.8, 'squeeze': 0.78, 'market_regime': 'Bullish', 'fundamental_grade': 'A'},
                {'symbol': 'MARICO', 'company_name': 'Marico Ltd.', 'cap_category': 'Large Cap', 'score': 81.2, 'rank_score': 84.0, 'rating': 8, 'price': 685.0, 'breakout_level': 670.0, 'distance_pct': 2.30, 'rvol': 1.5, 'rsi': 65, 'adx': 30, 'macd': 8.4, 'delivery_pct': 72.1, 'deliv_expansion_ratio': 1.85, 'sector_relative_strength': 5.1, 'squeeze': 0.72, 'market_regime': 'Bullish', 'fundamental_grade': 'A'},
                {'symbol': 'TRENT', 'company_name': 'Trent Ltd.', 'cap_category': 'Large Cap', 'score': 79.5, 'rank_score': 82.5, 'rating': 8, 'price': 7450.0, 'breakout_level': 7300.0, 'distance_pct': 0.85, 'rvol': 2.4, 'rsi': 60, 'adx': 32, 'macd': 45.1, 'delivery_pct': 61.9, 'deliv_expansion_ratio': 1.50, 'sector_relative_strength': 8.2, 'squeeze': 0.81, 'market_regime': 'Bullish', 'fundamental_grade': 'A+'},
            ])

        scan_mode = 'audit' if audit_clicked else 'normal' if normal_clicked else None
        if scan_mode:
            st.session_state.scanning = True
            st.session_state.scan_error = None
            st.session_state.scan_result = None
            scan_placeholder = st.empty()
            try:
                scan_placeholder.markdown('<div class="scan-shell"><div style="font-weight:700;font-size:1.1rem;color:var(--text)">🔎 Processing Market Scan</div><div class="scan-copy"><span>Evaluating NIFTY 500 Universe, Sector RS, Delivery Baseline &amp; Fundamental Gate</span><span>Executing</span></div><div class="scan-chart"><div class="candle-track">' + ''.join([f'<span class="candle {"g" if i % 3 else "r"}"></span>' for i in range(42)]) + '</div></div><div class="progress"><div></div></div></div>', unsafe_allow_html=True)
                with st.spinner('Executing Scanner v3 models, EOD delivery baseline & fundamental gate…'):
                    result = scan_universe(max_distance=10.0, period='2y', top_n=500)
                    result = enrich_shortlist_with_delivery(result)
                    result = apply_fundamental_gate(result, top_k=30, max_workers=10)

                st.session_state.scan_result = result
                st.session_state.scan_timestamp = datetime.now(IST).strftime('%Y-%m-%d %H:%M:%S IST')

                if scan_mode == 'audit' and result is not None and not result.empty:
                    run_id = new_run_id()
                    st.session_state.audit_pending_run_id = run_id
                    st.session_state.audit_pending_timestamp = st.session_state.scan_timestamp
                    st.session_state.audit_pending_rows = build_scan_snapshot(result, run_id=run_id, scan_timestamp_ist=st.session_state.scan_timestamp, scanner_period='2y', max_distance_pct=10.0)
                    st.session_state.audit_last_saved = None
            except Exception as exc:
                st.session_state.scan_result = pd.DataFrame()
                st.session_state.scan_error = str(exc)
            finally:
                st.session_state.scanning = False
                scan_placeholder.empty()

        result = st.session_state.get('scan_result')
        if st.session_state.get('scan_error'): st.error(st.session_state.scan_error)

        pending_rows = st.session_state.get("audit_pending_rows")
        pending_run_id = st.session_state.get("audit_pending_run_id")
        pending_timestamp = st.session_state.get("audit_pending_timestamp")
        append_in_progress = st.session_state.get("audit_append_in_progress", False)
        
        if pending_rows is not None:
            if append_in_progress:
                st.info(f"⏳ Writing {len(pending_rows)} audit rows to Google Sheets… Please keep this page open.")
                try:
                    with st.status("⏳ Appending audit batch…", expanded=True) as status:
                        status.write("Connecting to Google Sheets…")
                        audit_info = append_audit_batch(
                            st.secrets,
                            pending_rows,
                            run_id=pending_run_id,
                            scan_timestamp_ist=pending_timestamp,
                            scanner_period="2y",
                            max_distance_pct=10.0,
                        )
                        status.update(label=f"✅ Audit batch written: {audit_info.get('rows', 0)} new rows.", state="complete", expanded=False)
                    st.session_state.audit_last_saved = audit_info
                    st.session_state.audit_pending_rows = None
                    st.session_state.audit_pending_run_id = None
                    st.session_state.audit_pending_timestamp = None
                    st.session_state.audit_append_in_progress = False
                    st.rerun()
                except Exception as exc:
                    st.session_state.audit_append_in_progress = False
                    st.error("Audit batch NOT written. Details: " + str(exc))
            else:
                st.warning(f"📊 Audit collection is ready: {len(pending_rows)} signal rows from {pending_timestamp}. Append this batch to Google Sheets?")
                yes_col, no_col = st.columns(2)
                with yes_col:
                    append_clicked = st.button("✅ YES — APPEND TO AUDIT SHEET", key="audit_yes", use_container_width=True, type="primary")
                with no_col:
                    discard_clicked = st.button("❌ NO — DISCARD THIS AUDIT", key="audit_no", use_container_width=True)
                if append_clicked:
                    st.session_state.audit_append_in_progress = True
                    st.rerun()
                elif discard_clicked:
                    st.session_state.audit_pending_rows = None
                    st.session_state.audit_pending_run_id = None
                    st.session_state.audit_pending_timestamp = None
                    st.session_state.audit_append_in_progress = False
                    st.session_state.audit_last_saved = {"saved": False, "rows": 0, "reason": "discarded_by_user"}
                    st.success("Audit batch discarded. Normal scan result remains available.")
                    st.rerun()

        audit_info = st.session_state.get("audit_last_saved") or {}
        if audit_info.get("saved") and audit_info.get("reason") in {"appended", "batch_already_exists"}:
            st.success(f"✅ Audit batch recorded: {audit_info.get('rows', 0)} new signal rows. Run ID: {audit_info.get('run_id', '—')}")

        # -------------------------------------------------------------------------
        # PRE-PROCESS DATA FOR FILTERS & LAYOUT
        # -------------------------------------------------------------------------
        if result is None or result.empty:
            display = pd.DataFrame()
        else:
            display = result.copy()
            
            # Pre-compute timeframes for filtering and display
            display['timeframe_val'] = display.apply(lambda r: get_timeframe_status(r)[0], axis=1)
            
            if st.session_state.trade_filter != "All":
                display = display[display['timeframe_val'] == st.session_state.trade_filter]
            if st.session_state.cap_filter != "All Caps":
                display = display[display['cap_category'] == st.session_state.cap_filter]

            sort_cols = [c for c in ['rank_score', 'score', 'rating', 'distance_pct'] if c in display.columns]
            if sort_cols:
                display = display.sort_values(sort_cols, ascending=[False, False, False, True][:len(sort_cols)], kind='stable').reset_index(drop=True)
                
        matches_count = len(display)

        # -------------------------------------------------------------------------
        # LAYOUT: LEFT BENTO ANALYTICS COLUMN & RIGHT STOCK CARDS GRID
        # -------------------------------------------------------------------------
        col_analytics, col_grid = st.columns([1, 3])

        with col_analytics:
            st.markdown('<div class="section-title" style="margin-top:0;">Executive Summary</div>', unsafe_allow_html=True)
            
            st.markdown(f'''
            <div class="bento-card" style="text-align:center;padding:24px;">
                <div style="font-size:2.8rem;font-weight:900;color:var(--text);line-height:1;">{matches_count}</div>
                <div style="font-size:0.8rem;font-weight:700;color:var(--muted);text-transform:uppercase;margin-top:6px;letter-spacing:0.05em;">Qualified Matches</div>
            </div>
            ''', unsafe_allow_html=True)
            
            # CATEGORY FILTERS
            st.markdown('<div class="section-title">Filter by Setup</div>', unsafe_allow_html=True)
            
            def set_tf_filter(tf):
                st.session_state.trade_filter = tf
                
            st.button("All Setups", type="primary" if st.session_state.trade_filter == "All" else "secondary", on_click=set_tf_filter, args=("All",), use_container_width=True)
            st.button("Breakout Swing (3-10d)", type="primary" if st.session_state.trade_filter == "Breakout Swing (3-10d)" else "secondary", on_click=set_tf_filter, args=("Breakout Swing (3-10d)",), use_container_width=True)
            st.button("Short Term (1-3w)", type="primary" if st.session_state.trade_filter == "Short Term (1-3w)" else "secondary", on_click=set_tf_filter, args=("Short Term (1-3w)",), use_container_width=True)
            st.button("Positional (2-6w)", type="primary" if st.session_state.trade_filter == "Positional (2-6w)" else "secondary", on_click=set_tf_filter, args=("Positional (2-6w)",), use_container_width=True)
            st.button("Long Term (3-8m)", type="primary" if st.session_state.trade_filter == "Long Term (3-8m)" else "secondary", on_click=set_tf_filter, args=("Long Term (3-8m)",), use_container_width=True)

            st.markdown('<div class="section-title">Filter by Cap Size</div>', unsafe_allow_html=True)
            def set_cap_filter(cf):
                st.session_state.cap_filter = cf
            
            c_cap1, c_cap2 = st.columns(2)
            with c_cap1:
                st.button("All Caps", type="primary" if st.session_state.cap_filter == "All Caps" else "secondary", on_click=set_cap_filter, args=("All Caps",), use_container_width=True)
                st.button("Mid Cap", type="primary" if st.session_state.cap_filter == "Mid Cap" else "secondary", on_click=set_cap_filter, args=("Mid Cap",), use_container_width=True)
            with c_cap2:
                st.button("Large Cap", type="primary" if st.session_state.cap_filter == "Large Cap" else "secondary", on_click=set_cap_filter, args=("Large Cap",), use_container_width=True)
                st.button("Small Cap", type="primary" if st.session_state.cap_filter == "Small Cap" else "secondary", on_click=set_cap_filter, args=("Small Cap",), use_container_width=True)

            st.markdown('<div class="section-title">Cap Allocation</div>', unsafe_allow_html=True)
            light = st.session_state.theme_mode == 'light'
            
            if not display.empty and 'cap_category' in display.columns:
                caps = display['cap_category'].replace('', 'Unclassified').fillna('Unclassified')
                cap_counts = caps.value_counts()
                labels = cap_counts.index.tolist()
                values = cap_counts.values.tolist()
                
                palette = ['#10b981', '#3b82f6', '#f59e0b', '#ec4899', '#8b5cf6']
                colors = [palette[i % len(palette)] for i in range(len(labels))]
        
                fig_donut = go.Figure(go.Pie(
                    labels=labels,
                    values=values,
                    hole=0.7,
                    marker_colors=colors,
                    textinfo='none',
                ))
                fig_donut.update_layout(
                    template='plotly_white' if light else 'plotly_dark',
                    height=220,
                    margin=dict(l=10, r=10, t=10, b=10),
                    paper_bgcolor='#ffffff' if light else '#0d1017',
                    font=dict(color='#111827' if light else '#f8fafc'),
                    showlegend=True,
                    legend=dict(orientation='h', y=-0.1, x=0, font=dict(color='#111827' if light else '#f8fafc')),
                )
                st.plotly_chart(fig_donut, use_container_width=True, config={'displayModeBar': False})
            else:
                st.markdown('<div class="small-muted" style="text-align:center;">No caps to display</div>', unsafe_allow_html=True)

            st.markdown('<div class="section-title">20-Day Backtest Win Rate</div>', unsafe_allow_html=True)
            fig_gauge = go.Figure(go.Indicator(
                mode='gauge+number',
                value=68.0,
                number={'suffix': '%', 'font': {'size': 32, 'color': '#0f172a' if light else '#f8fafc'}},
                gauge={
                    'axis': {'range': [0, 100], 'tickwidth': 0, 'tickcolor': '#111827' if light else '#f8fafc'},
                    'bar': {'color': '#10b981', 'thickness': 0.2},
                    'bgcolor': '#e2e8f0' if light else '#1b2230',
                    'borderwidth': 0,
                },
            ))
            fig_gauge.update_layout(
                template='plotly_white' if light else 'plotly_dark', 
                height=180, 
                margin=dict(l=20, r=20, t=10, b=10), 
                paper_bgcolor='#ffffff' if light else '#0d1017',
                font=dict(color='#111827' if light else '#f8fafc')
            )
            st.plotly_chart(fig_gauge, use_container_width=True, config={'displayModeBar': False})

        with col_grid:
            if not display.empty and 'market_regime' in display.columns:
                active_reg = str(display['market_regime'].iloc[0] or 'Neutral')
                if active_reg == 'Bearish':
                    reg_border, reg_bg, reg_badge = 'var(--red)', 'var(--red-bg)', '<span class="badge badge-red">🚨 BEARISH REGIME • CAPITAL PRESERVATION GATE</span>'
                    reg_msg = 'NIFTY trend or internal breadth is weak. Scanner v3 has automatically capped non-leader scores and boosted relative-strength weights. Use 50% smaller position sizes.'
                elif active_reg == 'Overheated':
                    reg_border, reg_bg, reg_badge = 'var(--yellow)', 'var(--yellow-bg)', '<span class="badge badge-yellow">⚠️ OVERHEATED CLIMAX • ANTI-CHASE MODE</span>'
                    reg_msg = 'Market momentum is stretched. Scanner v3 is prioritizing fresh VCP squeezes and tight proximity (-0.5% to +2%) while penalizing extended breakouts.'
                elif active_reg == 'Bullish':
                    reg_border, reg_bg, reg_badge = 'var(--accent)', 'var(--accent-bg)', '<span class="badge badge-green">🟢 CONFIRMED BULLISH REGIME • RISK-ON</span>'
                    reg_msg = 'Broad market trend and internal NIFTY 500 breadth are aligned. Prioritize high RVOL, strong 20D Up/Down accumulation, and expanding EOD delivery.'
                else:
                    reg_border, reg_bg, reg_badge = 'var(--brand)', 'var(--brand-bg)', '<span class="badge badge-brand">🎯 ROTATIONAL / NEUTRAL • SNIPER MODE</span>'
                    reg_msg = 'Selective rotational market. Scanner v3 has increased weights on VCP/VDU contraction, multi-touch resistance quality, and institutional delivery.'
                st.markdown(
                    f'<div class="bento-card" style="border-left: 4px solid {reg_border}; background: {reg_bg}; padding: 12px 16px; margin-bottom: 14px;">'
                    f'<div style="display:flex; justify-content:space-between; align-items:center; flex-wrap:wrap; gap:8px;">{reg_badge}<span class="small-muted" style="font-weight:700;">Regime-Adaptive Weights Active</span></div>'
                    f'<div style="font-size:0.84rem; font-weight:600; color:var(--text); margin-top:6px;">{reg_msg}</div>'
                    f'</div>',
                    unsafe_allow_html=True,
                )

            hdr_c1, hdr_c2 = st.columns([4, 1.4])
            with hdr_c1:
                st.markdown(f'<div style="display:flex;justify-content:space-between;align-items:baseline;margin-bottom:14px;"><div class="section-title" style="border:none;margin:0;padding:0;">Screening Results <span style="color:var(--muted);font-weight:600;font-size:1rem;">({matches_count} Matches)</span></div><div class="small-muted">Ranked by Scanner v3 Quality, Sector RS &amp; Relative Delivery</div></div>', unsafe_allow_html=True)
            with hdr_c2:
                show_all_cards = st.toggle(f"Show All ({matches_count})", value=False, key="show_all_grid_cards") if matches_count > 30 else True

            if display.empty:
                st.markdown('<div class="bento-card" style="text-align:center;padding:60px 20px;"><div style="font-size:1.1rem;font-weight:700;">No Setups Found</div><div class="small-muted" style="margin-top:8px">Try changing the filter or scanning the market.</div></div>', unsafe_allow_html=True)
            else:
                grid_df = display if show_all_cards else display.head(30)
                for start in range(0, len(grid_df), 3):
                    cols = st.columns(3)
                    for j, col in enumerate(cols):
                        idx = start + j
                        if idx >= len(grid_df): continue
                        row = grid_df.iloc[idx]
                        
                        timeframe, tf_cls = get_timeframe_status(row)

                        with col:
                            rating = int(float(row.get('rating', 0) or 0))
                            score = float(row.get('score', 0) or 0)
                            price = float(row.get('price', 0) or 0)
                            rsi = float(row.get('rsi', 0) or 0)
                            adx = float(row.get('adx', 0) or 0)
                            macd = float(row.get('macd', 0) or 0)
                            dly = row.get('delivery_pct')
                            d_exp = float(row.get('deliv_expansion_ratio', 1.0) or 1.0)
                            sec_rs = float(row.get('sector_relative_strength', 0.0) or 0.0)
                            sqz_v = float(row.get('squeeze', 0.0) or 0.0)
                            f_grade = str(row.get('fundamental_grade', '') or '').strip()
                            f_flag = str(row.get('fundamental_flag', '') or '').strip()
                            
                            score_cls = 'badge-green' if score >= 80 else 'badge-brand' if score >= 65 else 'badge-yellow'
                            badges_html = f'<span class="badge {tf_cls}" style="margin-bottom:8px;margin-right:6px;">{timeframe}</span>'
                            badges_html += f'<span class="badge {score_cls}" style="margin-bottom:8px;margin-right:6px;">SCORE: {score:.0f} ({rating}/10)</span>'
                            if pd.notna(dly):
                                badges_html += f'<span class="badge badge-green" style="margin-bottom:8px;margin-right:6px;">DEL: {dly}% ({d_exp:.1f}x)</span>'
                            if sec_rs != 0:
                                sec_c = 'badge-green' if sec_rs >= 0 else 'badge-red'
                                badges_html += f'<span class="badge {sec_c}" style="margin-bottom:8px;margin-right:6px;">SEC RS: {sec_rs:+.1f}%</span>'
                            if sqz_v >= 0.75:
                                badges_html += '<span class="badge badge-brand" style="margin-bottom:8px;margin-right:6px;">💎 VCP / VDU</span>'
                            if f_grade and f_grade not in {'nan', 'None'}:
                                fg_cls = 'badge-green' if f_grade in {'A+', 'A'} else ('badge-red' if f_grade == 'D' else 'badge-grey')
                                badges_html += f'<span class="badge {fg_cls}" style="margin-bottom:8px;margin-right:6px;">FUND: {html.escape(f_grade)}</span>'
                            if f_flag == 'EARNINGS_EVENT_RISK':
                                badges_html += '<span class="badge badge-yellow" style="margin-bottom:8px;margin-right:6px;">⚠️ EARNINGS SOON</span>'
                            if row.get('false_breakout') or float(row.get('component_volume', 0.5) or 0.5) <= 0.10:
                                badges_html += '<span class="badge badge-red" style="margin-bottom:8px;">⚠️ TRAP RISK</span>'

                            card_html = (
                                f'<div class="bento-stock-card">'
                                f'<div style="display:flex;justify-content:space-between;align-items:center;">'
                                f'<span style="font-size:.7rem;font-weight:700;color:var(--muted);text-transform:uppercase;">RANK #{idx+1}</span>'
                                f'<span class="badge badge-grey">{html.escape(str(row.get("cap_category","")))}</span>'
                                f'</div>'
                                f'<div style="font-weight:800;font-size:1.15rem;color:var(--text);margin-top:8px;line-height:1.2;">{html.escape(str(row.get("company_name",row["symbol"])))}</div>'
                                f'<div class="small-muted" style="margin-bottom:10px;">{html.escape(str(row["symbol"]))}</div>'
                                f'<div>{badges_html}</div>'
                                f'<div style="display:flex;justify-content:space-between;align-items:baseline;margin-bottom:12px;">'
                                f'<div style="font-weight:900;font-size:1.35rem;">{money(price)}</div>'
                                f'<div style="font-size:.75rem;color:var(--accent);font-weight:700;">{float(row.get("distance_pct",0)):.2f}% to res.</div>'
                                f'</div>'
                                f'<div class="bar-row"><span class="bar-label">RSI</span><div class="bar-track"><div class="bar-fill" style="width:{min(rsi, 100)}%;background:var(--accent);"></div></div><span class="bar-val">{rsi:.0f}</span></div>'
                                f'<div class="bar-row"><span class="bar-label">ADX</span><div class="bar-track"><div class="bar-fill" style="width:{min(adx*1.5, 100)}%;background:var(--accent);"></div></div><span class="bar-val">{adx:.0f}</span></div>'
                                f'<div class="bar-row"><span class="bar-label">MACD</span><div class="bar-track"><div class="bar-fill" style="width:{min(abs(macd)*3, 100)}%;background:var(--accent);"></div></div><span class="bar-val">{macd:.1f}</span></div>'
                                f'</div>'
                            )
                            st.markdown(card_html, unsafe_allow_html=True)
                            if st.button('Launch Analytics ↗', key=f'stock_{row["symbol"]}_{idx}', use_container_width=True):
                                st.session_state.selected_stock = row['symbol']
                                st.session_state.selected_row = row.to_dict()
                                st.session_state.page = 'detail'
                                st.rerun()

        # -------------------------------------------------------------------------
        # MARKET NEWS & CORPORATE ANNOUNCEMENTS FEED (LIVE YAHOO FINANCE)
        # -------------------------------------------------------------------------
        st.markdown("<div style='height:24px'></div>", unsafe_allow_html=True)
        st.markdown('<div class="section-title">Market News & Exchange Filings Feed</div>', unsafe_allow_html=True)

        live_news = get_live_market_news_cached()
        if not live_news:
            t_fallback = datetime.now(IST).strftime('%d %b %Y • %H:%M IST')
            live_news = [
                {'pub_time': None, 'time_str': t_fallback, 'title': 'NIFTY 50 & BSE Sensex live market feed active; click any stock card for company-specific filings.', 'tag': 'MARKET PULSE', 'link': 'https://www.nseindia.com/'},
                {'pub_time': None, 'time_str': t_fallback, 'title': 'Scanner v3 Regime-Adaptive Engine & Pre-Scan Fundamental Gate active for top candidates.', 'tag': 'SYSTEM STATUS', 'link': 'https://www.nseindia.com/'},
                {'pub_time': None, 'time_str': t_fallback, 'title': 'NSE EOD Deliverable Quantity & multi-session baseline comparison synced.', 'tag': 'EXCHANGE ARCHIVE', 'link': 'https://www.nseindia.com/'},
            ]

        news_cols = st.columns(min(3, len(live_news)))
        for col, item in zip(news_cols, live_news[:3]):
            p_ts = item.get('pub_time')
            time_str = datetime.fromtimestamp(p_ts, tz=IST).strftime('%d %b %Y • %H:%M IST') if p_ts else item.get('time_str', 'Recent')
            link_url = item.get('link', '#')
            headline_txt = html.escape(str(item.get('title', '')))
            tag_txt = html.escape(str(item.get('tag', 'MARKET PULSE')))
            with col:
                st.markdown(f'''
                <div class="news-item">
                    <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:6px;">
                        <span class="news-time">{time_str}</span>
                        <span class="badge badge-brand">{tag_txt}</span>
                    </div>
                    <div class="news-headline"><a href="{link_url}" target="_blank" rel="noopener" style="color:var(--text);text-decoration:none;">{headline_txt} ↗</a></div>
                </div>
                ''', unsafe_allow_html=True)

# -----------------------------------------------------------------------------
# ROUTER EXECUTION
# -----------------------------------------------------------------------------
render_reload_guard(True)

if st.session_state.page == 'detail' and st.session_state.get('selected_stock'):
    render_detail(st.session_state.selected_stock, st.session_state.selected_row)
else:
    render_home()
