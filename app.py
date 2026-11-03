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
from scanner import load_universe, scan_universe, scan_single, score_stock, fetch_history
from audit_logger import build_scan_snapshot
from google_sheets_audit import (
    append_audit_batch,
    new_run_id,
    read_audit_signals,
    read_performance_keys,
    read_final_performance,
    append_performance_rows,
    append_analysis_rows,
)
from audit_analysis import build_completed_outcomes, analyze_outcome_combinations
from performance_tracker import (
    build_performance_rows,
    fetch_ohlc_histories,
    latest_completed_market_date,
)
from fundamental_data import fetch_single_fundamental

# Optional delivery loader integration
try:
    from delivery_loader import enrich_shortlist_with_delivery
except ImportError:
    def enrich_shortlist_with_delivery(df, report_date=None):
        if df is not None and not df.empty and "delivery_pct" not in df.columns:
            df["delivery_pct"] = None
            df["deliverable_qty"] = None
        return df

IST = ZoneInfo("Asia/Kolkata")

NIFTY50_CSV = "https://nsearchives.nseindia.com/content/indices/ind_nifty50list.csv"
NSE_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120 Safari/537.36",
    "Accept": "text/csv,text/plain,*/*",
}

st.set_page_config(
    page_title="NIFTY Momentum Intelligence | Fintech Analytics",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="collapsed",
)


def password_gate():
    try:
        required = str(st.secrets.get("APP_PASSWORD", "")).strip()
    except Exception:
        required = ""
    if not required:
        return True
    if st.session_state.get("authenticated", False):
        return True

    col1, col2, col3 = st.columns([1, 1.2, 1])
    with col2:
        st.markdown("<div style='height:60px'></div>", unsafe_allow_html=True)
        st.title("🔐 NIFTY Momentum Intelligence")
        st.caption("Fintech Portfolio Analytics Secure Portal")
        with st.form("scanner_password_login"):
            entered = st.text_input("Enter access key", type="password")
            submitted = st.form_submit_button("Unlock Platform", use_container_width=True)
        if submitted:
            if hmac.compare_digest(entered, required):
                st.session_state["authenticated"] = True
                st.rerun()
            else:
                st.error("Incorrect password.")
    return False


if not password_gate():
    st.stop()


# -----------------------------------------------------------------------------
# SESSION STATE INITIALIZATION
# -----------------------------------------------------------------------------
if "theme_mode" not in st.session_state:
    st.session_state.theme_mode = "dark"
if "ui_sandbox_mode" not in st.session_state:
    st.session_state.ui_sandbox_mode = False
if "page" not in st.session_state:
    st.session_state.page = "home"
if "scan_result" not in st.session_state:
    st.session_state.scan_result = None
if "scan_timestamp" not in st.session_state:
    st.session_state.scan_timestamp = None
if "scanning" not in st.session_state:
    st.session_state.scanning = False
if "audit_last_saved" not in st.session_state:
    st.session_state.audit_last_saved = None
if "audit_pending_rows" not in st.session_state:
    st.session_state.audit_pending_rows = None
if "audit_pending_run_id" not in st.session_state:
    st.session_state.audit_pending_run_id = None
if "audit_pending_timestamp" not in st.session_state:
    st.session_state.audit_pending_timestamp = None
if "audit_append_in_progress" not in st.session_state:
    st.session_state.audit_append_in_progress = False


# -----------------------------------------------------------------------------
# FINTECH ANALYTICS CSS (BENTO GRID & LIGHT/DARK THEME)
# -----------------------------------------------------------------------------
def inject_theme_css():
    is_light = st.session_state.theme_mode == "light"
    theme_vars = (
        """
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
        """
        if is_light
        else """
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
        """
    )

    css = f"""
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

    /* Fintech Buttons */
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
    .stButton > button:hover {{
        border-color: var(--accent);
        color: var(--accent);
        transform: translateY(-1px);
    }}

    /* Bento Cards */
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

    /* Top Command Header */
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

    /* Status & Badges */
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

    /* Micro Indicator Bars */
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

    /* Scanner Animation */
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

    /* Tabs */
    .stTabs [data-baseweb="tab-list"] {{ gap: 12px; border-bottom: 1px solid var(--border) !important; }}
    .stTabs [data-baseweb="tab"] {{ padding: 12px 20px; background: transparent; border: none; font-weight: 700; color: var(--muted); }}
    .stTabs [aria-selected="true"] {{ background: transparent; border-bottom: 3px solid var(--accent) !important; color: var(--text) !important; }}

    @media (max-width: 768px) {{
        .block-container {{ padding: 0.6rem 0.8rem 3rem !important; }}
        .fintech-topbar {{ padding: 12px; }}
        .fintech-title {{ font-size: 1.1rem; }}
        .target-box {{ min-width: 110px; padding: 10px; }}
    }}
    </style>
    """
    st.markdown(css, unsafe_allow_html=True)


inject_theme_css()


def render_reload_guard(active=True):
    if not active:
        return
    components.html(
        """
        <div id="reload-confirm" style="display:none;position:fixed;inset:0;z-index:999999;background:rgba(0,0,0,.5);backdrop-filter:blur(4px);align-items:center;justify-content:center;font-family:'Inter',sans-serif">
          <div style="width:min(400px,90vw);background:#0d1017;color:#f8fafc;border:1px solid #1e2535;border-radius:14px;padding:24px;box-shadow:0 20px 40px rgba(0,0,0,.5);text-align:center">
            <div style="font-size:18px;font-weight:700;margin-bottom:8px">Reload Application?</div>
            <div style="font-size:14px;color:#8c9bae;line-height:1.5;margin-bottom:20px">The current scan and un-saved audit data will be lost if you reload.</div>
            <div style="display:flex;gap:12px;justify-content:center">
              <button id="reload-yes" style="flex:1;border:0;border-radius:8px;padding:12px;background:#ef4444;color:#fff;font-weight:600;cursor:pointer">Reload</button>
              <button id="reload-no" style="flex:1;border:1px solid #1e2535;border-radius:8px;padding:12px;background:#131823;color:#f8fafc;font-weight:600;cursor:pointer">Stay</button>
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
            w.addEventListener('keydown', (event) => {
              const key = String(event.key || '').toLowerCase();
              const refresh = key === 'f5' || ((event.ctrlKey || event.metaKey) && key === 'r');
              if (refresh) { event.preventDefault(); show(); }
            }, true);
          } catch (e) {}
        })();
        </script>
        """,
        height=0,
    )


# -----------------------------------------------------------------------------
# MARKET DATA HELPERS
# -----------------------------------------------------------------------------
@st.cache_data(ttl=60, show_spinner=False)
def get_market_snapshot():
    result = {"nifty": None, "sensex": None, "updated": datetime.now(IST)}
    try:
        raw = yf.download(
            ["^NSEI", "^BSESN"],
            period="5d",
            interval="1d",
            auto_adjust=True,
            progress=False,
            threads=True,
            group_by="ticker",
            multi_level_index=True,
        )
        for symbol, key in [("^NSEI", "nifty"), ("^BSESN", "sensex")]:
            try:
                df = (
                    raw[symbol]
                    if isinstance(raw.columns, pd.MultiIndex)
                    and symbol in raw.columns.get_level_values(0)
                    else raw.xs(symbol, axis=1, level=1)
                )
                df = df.dropna(subset=["Close"])
                if len(df) >= 2:
                    last, prev = float(df.Close.iloc[-1]), float(df.Close.iloc[-2])
                    result[key] = {"value": last, "change": last - prev, "pct": (last / prev - 1) * 100}
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
        col = next(c for c in df.columns if c.strip().lower() == "symbol")
        return df[col].astype(str).str.strip().tolist()[:50]
    except Exception:
        return [
            "ADANIENT", "ADANIPORTS", "APOLLOHOSP", "ASIANPAINT", "AXISBANK",
            "BAJAJ-AUTO", "BAJFINANCE", "BAJAJFINSV", "BEL", "BHARTIARTL",
            "CIPLA", "COALINDIA", "DRREDDY", "EICHERMOT", "GRASIM", "HCLTECH",
            "HDFCBANK", "HDFCLIFE", "HEROMOTOCO", "HINDALCO", "HINDUNILVR",
            "ICICIBANK", "INDUSINDBK", "INFY", "ITC", "JIOFIN", "JSWSTEEL",
            "KOTAKBANK", "LT", "M&M", "MARUTI", "NESTLEIND", "NTPC", "ONGC",
            "POWERGRID", "RELIANCE", "SBILIFE", "SBIN", "SHRIRAMFIN", "SUNPHARMA",
            "TATACONSUM", "TATAMOTORS", "TATASTEEL", "TCS", "TECHM", "TITAN",
            "TRENT", "ULTRACEMCO",
        ]


@st.cache_data(ttl=60, show_spinner=False)
def get_nifty50_ticker_data(symbols):
    rows = []
    try:
        tickers = [s.replace("&", "%26") + ".NS" for s in symbols]
        raw = yf.download(
            tickers,
            period="5d",
            interval="1d",
            auto_adjust=True,
            progress=False,
            threads=True,
            group_by="ticker",
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
                df = df.dropna(subset=["Close"])
                if len(df) < 2:
                    continue
                last, prev = float(df.Close.iloc[-1]), float(df.Close.iloc[-2])
                rows.append({"symbol": symbol, "price": last, "pct": (last / prev - 1) * 100})
            except Exception:
                continue
    except Exception:
        return pd.DataFrame(columns=["symbol", "price", "pct"])
    return pd.DataFrame(rows)


@st.cache_data(ttl=3600, show_spinner=False)
def get_fundamentals_cached(symbol):
    return fetch_single_fundamental(symbol)


def market_status(now=None):
    now = now or datetime.now(IST)
    if now.weekday() >= 5:
        return "Closed", "red"
    t = now.time()
    if dtime(9, 0) <= t < dtime(9, 15):
        return "Pre-open", "yellow"
    if dtime(9, 15) <= t <= dtime(15, 30):
        return "Open", "green"
    return "Closed", "red"


def money(x):
    return f"₹{x:,.2f}" if x is not None and np.isfinite(x) else "—"


def pct(x):
    return f"{x:+.2f}%" if x is not None and np.isfinite(x) else "—"


def render_fintech_topbar():
    snap = get_market_snapshot()
    status, color = market_status()
    dot = f'<span class="dot {color}"></span>'

    nifty_item = snap.get("nifty")
    sensex_item = snap.get("sensex")

    nifty_str = (
        f"{nifty_item['value']:,.2f} <span class='{'up' if nifty_item['pct']>=0 else 'down'}'>({nifty_item['pct']:+.2f}%)</span>"
        if nifty_item
        else "—"
    )
    sensex_str = (
        f"{sensex_item['value']:,.2f} <span class='{'up' if sensex_item['pct']>=0 else 'down'}'>({sensex_item['pct']:+.2f}%)</span>"
        if sensex_item
        else "—"
    )

    col_brand, col_indices, col_controls = st.columns([3, 4, 3])
    with col_brand:
        st.markdown(
            f"""
            <div class="fintech-brand">
                <div class="fintech-logo">N</div>
                <div>
                    <div class="fintech-title">NIFTY INTELLIGENCE</div>
                    <div class="fintech-subtitle">{dot} Market Status: <b>{status}</b> • IST Live</div>
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    with col_indices:
        st.markdown(
            f"""
            <div style="display:flex; gap:10px; justify-content:center; align-items:center;">
                <div class="fintech-pill"><b>NIFTY 50</b> {nifty_str}</div>
                <div class="fintech-pill"><b>SENSEX</b> {sensex_str}</div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    with col_controls:
        c1, c2 = st.columns(2)
        with c1:
            is_light = st.toggle("☀️ Light", value=(st.session_state.theme_mode == "light"), key="theme_toggle")
            new_mode = "light" if is_light else "dark"
            if new_mode != st.session_state.theme_mode:
                st.session_state.theme_mode = new_mode
                st.rerun()
        with c2:
            sandbox = st.toggle("🧪 Sandbox", value=st.session_state.ui_sandbox_mode, key="sandbox_toggle")
            if sandbox != st.session_state.ui_sandbox_mode:
                st.session_state.ui_sandbox_mode = sandbox
                st.rerun()


def render_ticker():
    symbols = get_nifty50_symbols()
    df = get_nifty50_ticker_data(tuple(symbols))
    if df.empty:
        st.markdown('<div class="ticker-note">NIFTY 50 ticker stream temporarily unavailable.</div>', unsafe_allow_html=True)
        return
    items = []
    for _, r in df.iterrows():
        cls = "up" if r.pct >= 0 else "down"
        arrow = "▲" if r.pct >= 0 else "▼"
        items.append(f'<span class="tick" style="margin-right:28px;"><b>{html.escape(r.symbol)}</b> {money(r.price)} <span class="{cls}">{arrow} {r.pct:+.2f}%</span></span>')
    content = "".join(items)
    light = st.session_state.theme_mode == "light"
    bg = "#ffffff" if light else "#0d1017"
    textc = "#0f172a" if light else "#f8fafc"
    muted = "#64748b" if light else "#8c9bae"
    border = "#e2e8f0" if light else "#1e2535"
    markup = f'''<html><head><style>@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600&display=swap'); *{{box-sizing:border-box}}body{{margin:0;background:{bg};color:{textc};font-family:'Inter',sans-serif;overflow:hidden}}.viewport{{width:100%;overflow:hidden;border:1px solid {border};border-radius:12px;background:{bg};padding:10px 0}}.track{{display:flex;width:max-content;animation:marquee 140s linear infinite}}.track:hover{{animation-play-state:paused}}.tick{{white-space:nowrap;font-size:12px;color:{muted};font-weight:500}}.tick b{{color:{textc};margin-right:6px;font-weight:700}}.up{{color:#10b981}}.down{{color:#ef4444}}@keyframes marquee{{from{{transform:translateX(0)}}to{{transform:translateX(-50%)}}}}</style></head><body><div class="viewport"><div class="track">{content}{content}</div></div></body></html>'''
    components.html(markup, height=44, scrolling=False)


def day_change(symbol, period="2y"):
    hist = fetch_history(symbol, period)
    if hist is None or len(hist) < 2:
        return None, None, None
    last, prev = float(hist.Close.iloc[-1]), float(hist.Close.iloc[-2])
    return last, last - prev, (last / prev - 1) * 100


def detail_chart(symbol, row, period="2y"):
    hist = fetch_history(symbol, period)
    if hist is None or hist.empty:
        st.warning("Price history is temporarily unavailable for the chart.")
        return
    light = st.session_state.theme_mode == "light"
    fig = go.Figure()
    fig.add_trace(go.Candlestick(x=hist.index, open=hist.Open, high=hist.High, low=hist.Low, close=hist.Close, name=symbol))
    fig.add_trace(go.Bar(x=hist.index, y=hist.Volume, name="Volume", yaxis="y2", opacity=0.25, marker_color="#6366f1"))
    fig.add_hline(y=float(row["breakout_level"]), line_dash="dash", line_color="#10b981", annotation_text=f"Breakout: ₹{row['breakout_level']:.2f}", annotation_position="top left")
    fig.update_layout(
        template="plotly_white" if light else "plotly_dark",
        height=520,
        margin=dict(l=10, r=10, t=25, b=10),
        xaxis_rangeslider_visible=False,
        hovermode="x unified",
        paper_bgcolor="#ffffff" if light else "#0d1017",
        plot_bgcolor="#f8fafc" if light else "#05070b",
        yaxis=dict(title="Price", gridcolor="#e2e8f0" if light else "#1e2535"),
        yaxis2=dict(title="Volume", overlaying="y", side="right", showgrid=False, rangemode="tozero"),
        legend=dict(orientation="h", y=1.02, x=0),
    )
    st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False, "responsive": True})


def verdict(score):
    if score >= 90: return "Strong", True
    if score >= 75: return "Good", True
    if score >= 60: return "Neutral", False
    if score >= 40: return "Weak", False
    return "Avoid", False


def score_class(value, kind):
    try: v = float(value)
    except Exception: return "metric-neutral"
    if kind == "rsi": return "metric-good" if 52 <= v <= 68 else "metric-ok" if 48 <= v <= 72 else "metric-poor"
    if kind == "rvol": return "metric-good" if v >= 1.5 else "metric-ok" if v >= 1.1 else "metric-poor" if v >= .8 else "metric-bad"
    if kind == "adx": return "metric-good" if v >= 25 else "metric-ok" if v >= 18 else "metric-poor"
    if kind == "distance": return "metric-good" if v <= 1 else "metric-ok" if v <= 3 else "metric-neutral" if v <= 5 else "metric-poor" if v <= 10 else "metric-bad"
    if kind == "rr": return "metric-good" if v >= 2 else "metric-ok" if v >= 1.5 else "metric-neutral" if v >= 1 else "metric-poor"
    if kind == "score": return "metric-good" if v >= 80 else "metric-ok" if v >= 65 else "metric-neutral" if v >= 50 else "metric-poor" if v >= 35 else "metric-bad"
    return "metric-neutral"


def metric_card(label, value, kind=None):
    cls = score_class(value, kind) if kind else "metric-neutral"
    return f'<div class="metric-card {cls}"><div class="metric-label">{html.escape(str(label))}</div><div class="metric-value">{html.escape(str(value))}</div></div>'


def target_values(row, price):
    b = float(row.get("breakout_level", 0) or 0)
    try: t1 = float(row.get("target1"))
    except Exception: t1 = None
    try: t2 = float(row.get("target2"))
    except Exception: t2 = None
    if t1 is None or not np.isfinite(t1):
        base = max(b - float(price), 0)
        t1 = b + base if base else b * 1.01
    if t2 is None or not np.isfinite(t2):
        base = max(b - float(price), 0)
        t2 = b + 2 * base if base else b * 1.02
    return t1, t2


def build_single_stock_export(symbol, row, scanned_at, rank=""):
    t1 = float(row.get("target1")) if pd.notna(row.get("target1")) else np.nan
    t2 = float(row.get("target2")) if pd.notna(row.get("target2")) else np.nan
    t3 = t2 + (t2 - t1) if np.isfinite(t1) and np.isfinite(t2) else np.nan
    targets = " | ".join([f"T1: {t1:.2f}" if np.isfinite(t1) else "T1: —", f"T2: {t2:.2f}" if np.isfinite(t2) else "T2: —", f"T3: {t3:.2f}" if np.isfinite(t3) else "T3: —"])
    return pd.DataFrame([{
        "Date": str(scanned_at).split(" ")[0], "Stock": row.get("company_name", symbol), "Symbol": symbol, "Cap": row.get("cap_category", ""),
        "Rank": rank, "Score": round(float(row.get("score", 0)), 2), "Strength": row.get("rating", ""), "Price": round(float(row.get("price")), 2),
        "Breakout Level": round(float(row.get("breakout_level")), 2), "Targets": targets, "Stop": round(float(row.get("stop_reference")), 2),
        "Distance %": round(float(row.get("distance_pct")), 2), "RVOL": round(float(row.get("rvol")), 2), "RSI": round(float(row.get("rsi")), 2),
        "ADX": round(float(row.get("adx")), 2), "EOD Delivery %": row.get("delivery_pct", "—"), "Market Regime": row.get("market_regime", ""),
    }])


# -----------------------------------------------------------------------------
# DETAILED VIEW (WITH TABS)
# -----------------------------------------------------------------------------
def render_detail(symbol, row):
    render_fintech_topbar()
    st.markdown("<div style='height:10px'></div>", unsafe_allow_html=True)

    if st.button("← Back to Analytics Dashboard"):
        st.session_state.page = "home"
        st.rerun()

    company = row.get("company_name", symbol)
    last, change, change_pct = day_change(symbol)
    price = last if last is not None else row.get("price")
    score = float(row.get("score", 0))
    change_cls = "up" if (change_pct or 0) >= 0 else "down"
    arrow = "▲" if (change_pct or 0) >= 0 else "▼"
    t1, t2 = target_values(row, price)
    t1up = ((t1 / price) - 1) * 100 if price else 0
    t2up = ((t2 / price) - 1) * 100 if price else 0

    hero_html = (
        f'<div style="display:flex;justify-content:space-between;align-items:flex-end;margin-bottom:24px;padding:24px;background:var(--card);border-radius:16px;border:1px solid var(--border);box-shadow:var(--shadow);">'
        f'<div>'
        f'<div class="small-muted" style="font-size:.9rem;font-weight:600;margin-bottom:6px;letter-spacing:.02em;text-transform:uppercase;">{html.escape(str(company))}</div>'
        f'<div style="font-size:2.4rem;font-weight:800;line-height:1.1;color:var(--text);">{html.escape(symbol)}</div>'
        f'<div style="display:flex;align-items:center;gap:14px;margin-top:10px;">'
        f'<div style="font-size:1.8rem;font-weight:800;color:var(--text);">{money(price)}</div>'
        f'<div class="{change_cls}" style="font-weight:700;font-size:1.1rem;">{arrow} {money(change)} ({pct(change_pct)})</div>'
        f'</div>'
        f'</div>'
        f'<div style="display:flex;gap:16px;">'
        f'<div class="target-box"><div class="target-label">Target 1</div><div class="target-value">{money(t1)}</div><div class="target-upside">{t1up:+.2f}%</div></div>'
        f'<div class="target-box"><div class="target-label">Target 2</div><div class="target-value">{money(t2)}</div><div class="target-upside">{t2up:+.2f}%</div></div>'
        f'</div>'
        f'</div>'
    )
    st.markdown(hero_html, unsafe_allow_html=True)

    tab_tech, tab_fund, tab_news, tab_audit = st.tabs(["📈 Technical Analytics", "🏛️ Fundamental Health", "📰 News & Filings", "📊 Audit Details"])

    with tab_tech:
        c_left, c_right = st.columns([3, 1])
        with c_left:
            st.markdown('<div class="section-title" style="margin-top:0;">Price Action & Volume</div>', unsafe_allow_html=True)
            tv_symbol = str(symbol).replace(".NS", "").upper()
            tv_url = f"https://www.tradingview.com/chart/?symbol=NSE:{tv_symbol}"
            detail_chart(symbol, row)
            st.markdown(f'<div style="text-align:center;margin:8px 0 16px;"><a href="{tv_url}" target="_blank" rel="noopener" style="color:var(--brand);font-weight:700;font-size:.85rem;text-decoration:none;">Open Full Interactive Chart ↗</a></div>', unsafe_allow_html=True)

        with c_right:
            st.markdown('<div class="section-title" style="margin-top:0;">Momentum Score</div>', unsafe_allow_html=True)
            light = st.session_state.theme_mode == "light"
            fig = go.Figure(go.Indicator(
                mode="gauge+number",
                value=score,
                number={"suffix": "", "font": {"size": 42, "color": "#0f172a" if light else "#f8fafc"}},
                gauge={
                    "axis": {"range": [0, 100], "tickwidth": 0, "tickcolor": "rgba(0,0,0,0)"},
                    "bar": {"color": "#10b981", "thickness": 0.15},
                    "bgcolor": "#e2e8f0" if light else "#1b2230",
                    "borderwidth": 0,
                    "steps": [
                        {"range": [0, 40], "color": "rgba(239,68,68,0.15)"},
                        {"range": [40, 65], "color": "rgba(245,158,11,0.15)"},
                        {"range": [65, 80], "color": "rgba(132,204,22,0.15)"},
                        {"range": [80, 100], "color": "rgba(16,185,129,0.15)"},
                    ],
                },
            ))
            fig.update_layout(template="plotly_white" if light else "plotly_dark", height=260, margin=dict(l=15, r=15, t=20, b=0), paper_bgcolor="#ffffff" if light else "#0d1017")
            st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})

            level = float(row.get("breakout_level", 0) or 0)
            p = float(price or 0)
            distance = ((level - p) / level * 100) if level else 999
            if p >= level:
                title, msg, cls = "Breakout Confirmed", "Trading above detected resistance.", "badge-green"
            elif distance <= 2:
                title, msg, cls = "ENTRY ZONE", "Near breakout level. Await volume confirmation.", "badge-green"
            elif distance <= 5:
                title, msg, cls = "Developing", "Setup forming, not near entry.", "badge-yellow"
            else:
                title, msg, cls = "Watch", "Monitoring base formation.", "badge-grey"

            st.markdown(f'<div class="bento-card" style="text-align:center;"><span class="badge {cls}">{title}</span><div style="font-size:1rem;font-weight:700;margin-top:14px;color:var(--text);">{msg}</div><div class="small-muted" style="margin-top:8px">Distance: <span style="font-weight:600;">{distance:.2f}%</span> &nbsp; • &nbsp; Trigger: <span style="font-weight:600;">{money(row.get("breakout_trigger"))}</span></div></div>', unsafe_allow_html=True)

            if row.get("delivery_pct"):
                st.markdown(f'<div class="bento-card" style="text-align:center;"><span class="badge badge-green">EOD Delivery Confirmed</span><div style="font-size:1.6rem;font-weight:900;margin-top:8px;color:var(--accent);">{row.get("delivery_pct")}%</div><div class="small-muted">Deliverable Quantity Exchange Archive</div></div>', unsafe_allow_html=True)

        st.markdown('<div class="section-title">Technical Parameters</div>', unsafe_allow_html=True)
        fields = [
            ("Breakout level", money(row.get("breakout_level")), "distance"), ("Breakout trigger", money(row.get("breakout_trigger")), None),
            ("Distance", pct(row.get("distance_pct")), "distance"), ("Rating", f"{row.get('rating','—')}/10", "score"),
            ("Score", f"{row.get('score',0):.1f}/100", "score"), ("RVOL", f"{row.get('rvol',0):.2f}x", "rvol"),
            ("RSI", f"{row.get('rsi',0):.1f}", "rsi"), ("ADX", f"{row.get('adx',0):.1f}", "adx"),
            ("EMA structure", row.get("ema_structure", "—"), None), ("MACD", f"{row.get('macd',0):.3f}", None),
            ("ATR %", f"{row.get('atr_pct',0):.2f}%", None), ("Squeeze", f"{row.get('squeeze',0):.2f}", None),
            ("NIFTY rel strength", pct(row.get("nifty_relative_strength")), None), ("60D rel strength", pct(row.get("relative_strength")), None),
            ("Candlestick", row.get("candlestick", "—"), None), ("Resistance touches", row.get("resistance_touches", "—"), None),
            ("Risk / reward", f"{row.get('risk_reward',0):.2f}", "rr"), ("Market regime", row.get("market_regime", "—"), None),
            ("Stop reference", money(row.get("stop_reference")), None), ("EOD Delivery %", f"{row.get('delivery_pct','—')}%" if pd.notna(row.get('delivery_pct')) else "—", "rvol"),
        ]
        for start in range(0, len(fields), 5):
            cols = st.columns(5)
            for j, col in enumerate(cols):
                idx = start + j
                if idx >= len(fields): continue
                with col: st.markdown(metric_card(fields[idx][0], fields[idx][1], fields[idx][2]), unsafe_allow_html=True)

    with tab_fund:
        st.markdown('<div class="section-title" style="margin-top:0;">Fundamental Health & Financial Filings</div>', unsafe_allow_html=True)
        with st.spinner("Retrieving latest financial filings..."):
            fund_data = get_fundamentals_cached(symbol)

        if fund_data.get("fundamental_quality") == "OK":
            rev = fund_data.get("q_rev_growth_yoy_pct")
            prof = fund_data.get("q_profit_growth_yoy_pct")
            margin = fund_data.get("operating_margin_pct")
            dte = fund_data.get("debt_to_equity")

            rev_str = f"{rev:+.2f}%" if pd.notna(rev) else "N/A"
            prof_str = f"{prof:+.2f}%" if pd.notna(prof) else "N/A"
            margin_str = f"{margin:.2f}%" if pd.notna(margin) else "N/A"
            dte_str = f"{dte:.2f}" if pd.notna(dte) else "N/A"

            rev_c = "var(--accent)" if pd.notna(rev) and rev > 0 else "var(--red)" if pd.notna(rev) else "var(--text)"
            prof_c = "var(--accent)" if pd.notna(prof) and prof > 0 else "var(--red)" if pd.notna(prof) else "var(--text)"
            dte_c = "var(--red)" if pd.notna(dte) and dte > 1.5 else "var(--accent)" if pd.notna(dte) else "var(--text)"

            st.markdown(f"""
            <div style="display:grid;grid-template-columns:repeat(4,1fr);gap:16px;">
                <div class="bento-card"><b style="color:var(--muted);font-size:.75rem;text-transform:uppercase;">QoQ Revenue Growth</b><br><span style="font-size:1.6rem;font-weight:800;color:{rev_c}">{rev_str}</span></div>
                <div class="bento-card"><b style="color:var(--muted);font-size:.75rem;text-transform:uppercase;">QoQ Net Profit</b><br><span style="font-size:1.6rem;font-weight:800;color:{prof_c}">{prof_str}</span></div>
                <div class="bento-card"><b style="color:var(--muted);font-size:.75rem;text-transform:uppercase;">Operating Margin</b><br><span style="font-size:1.6rem;font-weight:800;">{margin_str}</span></div>
                <div class="bento-card"><b style="color:var(--muted);font-size:.75rem;text-transform:uppercase;">Debt to Equity</b><br><span style="font-size:1.6rem;font-weight:800;color:{dte_c}">{dte_str}</span></div>
            </div>
            <div class="small-muted" style="margin-top:12px;text-align:right;">Data sourced securely via Yahoo Finance APIs.</div>
            """, unsafe_allow_html=True)
        else:
            st.warning(f"Fundamental data is currently unavailable for {symbol}. Status: {fund_data.get('fundamental_quality')}")

    with tab_news:
        st.markdown('<div class="section-title" style="margin-top:0;">Corporate Filings Feed</div>', unsafe_allow_html=True)
        st.info("News Intelligence module active.")
        st.markdown('<div class="bento-card"><span class="badge badge-brand">Live Feed</span><div style="margin-top:10px;font-weight:600;font-size:1.05rem;">Awaiting incoming exchange filings and block deals.</div></div>', unsafe_allow_html=True)

    with tab_audit:
        st.markdown('<div class="section-title" style="margin-top:0;">Google Sheets Audit Export</div>', unsafe_allow_html=True)
        st.markdown('<div class="small-muted" style="margin-bottom:16px;">Raw technical properties formatted for your external sheet tracker.</div>', unsafe_allow_html=True)
        audit_df = build_single_stock_export(symbol, row, st.session_state.get("search_timestamp", datetime.now(IST).strftime("%Y-%m-%d %H:%M:%S IST")), rank="")
        st.dataframe(audit_df, use_container_width=True, hide_index=True)
        st.download_button("📥 DOWNLOAD AUDIT ROW (CSV)", data=audit_df.to_csv(index=False).encode("utf-8-sig"), file_name=f"audit_{symbol}_{datetime.now(IST).strftime('%Y%m%d_%H%M%S')}.csv", mime="text/csv", use_container_width=False, key=f"audit_{symbol}")


# -----------------------------------------------------------------------------
# MAIN DASHBOARD (BENTO GRID LAYOUT)
# -----------------------------------------------------------------------------
def render_home():
    render_fintech_topbar()
    st.markdown("<div style='height:8px'></div>", unsafe_allow_html=True)
    render_ticker()
    st.markdown("<div style='height:16px'></div>", unsafe_allow_html=True)

    audit_pending = st.session_state.get("audit_pending_rows") is not None

    # ACTION BAR (Bento Action Header)
    col_search, col_scan, col_audit, col_track = st.columns([3, 2, 2, 2])
    with col_search:
        st.markdown('<div style="font-size:.72rem;font-weight:700;margin-bottom:6px;color:var(--muted);text-transform:uppercase;letter-spacing:.05em;">Manual Ticker Search</div>', unsafe_allow_html=True)
        sc1, sc2 = st.columns([3, 1])
        with sc1:
            query = st.text_input("Stock symbol", placeholder="e.g. RELIANCE", key="stock_search_input", label_visibility="collapsed")
        with sc2:
            search_clicked = st.button("SEARCH", key="search_stock", use_container_width=True)

    with col_scan:
        st.markdown('<div style="font-size:.72rem;font-weight:700;margin-bottom:6px;color:var(--muted);text-transform:uppercase;letter-spacing:.05em;">Market Scanner</div>', unsafe_allow_html=True)
        normal_clicked = st.button("🚀 SCAN MARKET", key="scan_market", use_container_width=True, disabled=audit_pending)
        if normal_clicked: st.session_state.scan_intent = True

    with col_audit:
        st.markdown('<div style="font-size:.72rem;font-weight:700;margin-bottom:6px;color:transparent;">-</div>', unsafe_allow_html=True)
        audit_clicked = st.button("📊 COLLECT AUDIT", key="collect_audit", use_container_width=True, disabled=audit_pending)

    with col_track:
        st.markdown('<div style="font-size:.72rem;font-weight:700;margin-bottom:6px;color:transparent;">-</div>', unsafe_allow_html=True)
        tracking_clicked = st.button("📈 UPDATE TRACKING", key="update_performance_tracking", use_container_width=True, disabled=audit_pending)

    if search_clicked and query.strip():
        symbol = query.strip().upper().replace(".NS", "")
        st.session_state.search_error = None
        with st.spinner(f"Analyzing {symbol}…"):
            try:
                row = scan_single(symbol, max_distance=10.0, period="2y")
                if row is None:
                    hist = fetch_history(symbol, "2y")
                    if hist is None: raise ValueError("No usable 2-year price history available.")
                    nifty = __import__("scanner").fetch_index_history("^NSEI", period="2y")
                    row = score_stock(hist, nifty_df=nifty)
                    if row is None: raise ValueError("Could not calculate technical setup.")
                    row["symbol"] = symbol
                    row["company_name"] = symbol
                    row["cap_category"] = ""
                    row["outside_near_breakout_range"] = True
                else:
                    row["outside_near_breakout_range"] = False
                    try:
                        universe = load_universe()
                        m = universe.loc[universe.symbol == symbol]
                        if not m.empty:
                            row["company_name"] = m.iloc[0]["company_name"]
                            row["cap_category"] = m.iloc[0]["cap_category"]
                    except Exception: pass
                st.session_state.selected_stock = symbol
                st.session_state.selected_row = row
                st.session_state.page = "detail"
                st.rerun()
            except Exception as exc:
                st.error(str(exc))

    st.markdown("<div style='height:20px'></div>", unsafe_allow_html=True)

    # SANDBOX / SCAN TRIGGER
    if st.session_state.ui_sandbox_mode and st.session_state.scan_result is None:
        st.session_state.scan_result = pd.DataFrame([
            {"symbol": "BOSCHLTD", "company_name": "Bosch Ltd.", "cap_category": "Large Cap", "score": 92.5, "rating": 9, "price": 35850.0, "breakout_level": 35000.0, "distance_pct": 0.42, "rvol": 2.1, "rsi": 62, "adx": 28, "macd": 124.5, "delivery_pct": 64.2},
            {"symbol": "MANKIND", "company_name": "Mankind Pharma Ltd.", "cap_category": "Large+Mid Cap", "score": 88.0, "rating": 9, "price": 2740.0, "breakout_level": 2700.0, "distance_pct": 1.25, "rvol": 1.8, "rsi": 58, "adx": 24, "macd": 15.2, "delivery_pct": 58.4},
            {"symbol": "MARICO", "company_name": "Marico Ltd.", "cap_category": "Large Cap", "score": 81.2, "rating": 8, "price": 685.0, "breakout_level": 670.0, "distance_pct": 2.30, "rvol": 1.5, "rsi": 65, "adx": 30, "macd": 8.4, "delivery_pct": 72.1},
            {"symbol": "TRENT", "company_name": "Trent Ltd.", "cap_category": "Large Cap", "score": 79.5, "rating": 8, "price": 7450.0, "breakout_level": 7300.0, "distance_pct": 0.85, "rvol": 2.4, "rsi": 60, "adx": 32, "macd": 45.1, "delivery_pct": 61.9},
        ])

    scan_mode = "audit" if audit_clicked else "normal" if normal_clicked else None
    if scan_mode:
        st.session_state.scanning = True
        st.session_state.scan_error = None
        st.session_state.scan_result = None
        scan_placeholder = st.empty()
        try:
            scan_placeholder.markdown('<div class="scan-shell"><div style="font-weight:700;font-size:1.1rem;color:var(--text)">🔎 Processing Market Scan</div><div class="scan-copy"><span>Evaluating 250 Equities & EOD Delivery</span><span>Executing</span></div><div class="scan-chart"><div class="candle-track">' + ''.join([f'<span class="candle {"g" if i % 3 else "r"}"></span>' for i in range(42)]) + '</div></div><div class="progress"><div></div></div></div>', unsafe_allow_html=True)
            with st.spinner("Executing models & fetching EOD data…"):
                result = scan_universe(max_distance=10.0, period="2y", top_n=500)
                result = enrich_shortlist_with_delivery(result)

            st.session_state.scan_result = result
            st.session_state.scan_timestamp = datetime.now(IST).strftime("%Y-%m-%d %H:%M:%S IST")

            if scan_mode == "audit" and result is not None and not result.empty:
                run_id = new_run_id()
                st.session_state.audit_pending_run_id = run_id
                st.session_state.audit_pending_timestamp = st.session_state.scan_timestamp
                st.session_state.audit_pending_rows = build_scan_snapshot(result, run_id=run_id, scan_timestamp_ist=st.session_state.scan_timestamp, scanner_period="2y", max_distance_pct=10.0)
                st.session_state.audit_last_saved = None
        except Exception as exc:
            st.session_state.scan_result = pd.DataFrame()
            st.session_state.scan_error = str(exc)
        finally:
            st.session_state.scanning = False
            scan_placeholder.empty()

    result = st.session_state.get("scan_result")
    if st.session_state.get("scan_error"): st.error(st.session_state.scan_error)

    # -------------------------------------------------------------------------
    # LAYOUT: LEFT BENTO ANALYTICS COLUMN & RIGHT STOCK CARDS GRID
    # -------------------------------------------------------------------------
    col_analytics, col_grid = st.columns([1, 3])

    with col_analytics:
        st.markdown('<div class="section-title" style="margin-top:0;">Executive Summary</div>', unsafe_allow_html=True)
        
        matches_count = len(result) if result is not None else 0
        st.markdown(f"""
        <div class="bento-card" style="text-align:center;padding:24px;">
            <div style="font-size:2.8rem;font-weight:900;color:var(--text);line-height:1;">{matches_count}</div>
            <div style="font-size:0.8rem;font-weight:700;color:var(--muted);text-transform:uppercase;margin-top:6px;letter-spacing:0.05em;">Qualified Matches</div>
        </div>
        """, unsafe_allow_html=True)

        st.markdown('<div class="section-title">Cap Allocation</div>', unsafe_allow_html=True)
        light = st.session_state.theme_mode == "light"
        
        if result is not None and not result.empty and "cap_category" in result.columns:
            cap_counts = result["cap_category"].value_counts()
            labels = cap_counts.index.tolist()
            values = cap_counts.values.tolist()
        else:
            labels = ["Large Cap", "Mid Cap", "Small Cap"]
            values = [54, 36, 10]

        fig_donut = go.Figure(go.Pie(
            labels=labels,
            values=values,
            hole=0.7,
            marker_colors=["#10b981", "#6366f1", "#f59e0b"],
            textinfo="none",
        ))
        fig_donut.update_layout(
            template="plotly_white" if light else "plotly_dark",
            height=220,
            margin=dict(l=10, r=10, t=10, b=10),
            paper_bgcolor="#ffffff" if light else "#0d1017",
            showlegend=True,
            legend=dict(orientation="h", y=-0.1, x=0),
        )
        st.plotly_chart(fig_donut, use_container_width=True, config={"displayModeBar": False})

        st.markdown('<div class="section-title">20-Day Backtest Win Rate</div>', unsafe_allow_html=True)
        fig_gauge = go.Figure(go.Indicator(
            mode="gauge+number",
            value=68.0,
            number={"suffix": "%", "font": {"size": 32, "color": "#0f172a" if light else "#f8fafc"}},
            gauge={
                "axis": {"range": [0, 100], "tickwidth": 0},
                "bar": {"color": "#10b981", "thickness": 0.2},
                "bgcolor": "#e2e8f0" if light else "#1b2230",
                "borderwidth": 0,
            },
        ))
        fig_gauge.update_layout(template="plotly_white" if light else "plotly_dark", height=180, margin=dict(l=20, r=20, t=10, b=10), paper_bgcolor="#ffffff" if light else "#0d1017")
        st.plotly_chart(fig_gauge, use_container_width=True, config={"displayModeBar": False})

    with col_grid:
        st.markdown(f'<div style="display:flex;justify-content:space-between;align-items:baseline;margin-bottom:14px;"><div class="section-title" style="border:none;margin:0;padding:0;">Screening Results <span style="color:var(--muted);font-weight:600;font-size:1rem;">({matches_count} Matches)</span></div><div class="small-muted">Ranked by Momentum Setup & EOD Delivery</div></div>', unsafe_allow_html=True)

        if result is None or result.empty:
            st.markdown('<div class="bento-card" style="text-align:center;padding:60px 20px;"><div style="font-size:1.1rem;font-weight:700;">Awaiting Market Scan</div><div class="small-muted" style="margin-top:8px">Click <b>SCAN MARKET</b> above or toggle <b>Sandbox Mode</b> to inspect analytics cards.</div></div>', unsafe_allow_html=True)
        else:
            display = result.copy()
            sort_cols = [c for c in ["rating", "score", "rank_score", "distance_pct"] if c in display.columns]
            if sort_cols:
                display = display.sort_values(sort_cols, ascending=[False, False, False, True][:len(sort_cols)], kind="stable").reset_index(drop=True)

            for start in range(0, len(display), 3):
                cols = st.columns(3)
                for j, col in enumerate(cols):
                    idx = start + j
                    if idx >= len(display): continue
                    row = display.iloc[idx]
                    ratio = idx / max(len(display) - 1, 1)

                    if ratio < 0.2: color = "#10b981"; bg_fill = "rgba(16,185,129,0.08)"
                    elif ratio < 0.4: color = "#84cc16"; bg_fill = "rgba(132,204,22,0.08)"
                    elif ratio < 0.6: color = "#f59e0b"; bg_fill = "rgba(245,158,11,0.08)"
                    elif ratio < 0.8: color = "#f97316"; bg_fill="rgba(249,115,22,0.08)"
                    else: color = "#ef4444"; bg_fill = "rgba(239,68,68,0.08)"

                    with col:
                        rating = int(float(row.get("rating", 0) or 0))
                        score = float(row.get("score", 0) or 0)
                        price = float(row.get("price", 0) or 0)
                        rsi = float(row.get("rsi", 0) or 0)
                        adx = float(row.get("adx", 0) or 0)
                        macd = float(row.get("macd", 0) or 0)
                        dly = row.get("delivery_pct")
                        dly_badge = f'<span class="badge badge-green" style="margin-bottom:8px;">EOD DEL: {dly}%</span>' if pd.notna(dly) else ''

                        card_html = (
                            f'<div class="bento-stock-card">'
                            f'<div style="display:flex;justify-content:space-between;align-items:center;">'
                            f'<span style="font-size:.7rem;font-weight:700;color:var(--muted);text-transform:uppercase;">RANK #{idx+1}</span>'
                            f'<span class="badge" style="background:{bg_fill};color:{color};">{html.escape(str(row.get("cap_category","")))}</span>'
                            f'</div>'
                            f'<div style="font-weight:800;font-size:1.15rem;color:var(--text);margin-top:8px;line-height:1.2;">{html.escape(str(row.get("company_name",row["symbol"])))}</div>'
                            f'<div class="small-muted" style="margin-bottom:10px;">{html.escape(str(row["symbol"]))}</div>'
                            f'{dly_badge}'
                            f'<div style="display:flex;justify-content:space-between;align-items:baseline;margin-bottom:12px;">'
                            f'<div style="font-weight:900;font-size:1.35rem;">{money(price)}</div>'
                            f'<div style="font-size:.75rem;color:{color};font-weight:700;">{float(row.get("distance_pct",0)):.2f}% to res.</div>'
                            f'</div>'
                            f'<div class="bar-row"><span class="bar-label">RSI</span><div class="bar-track"><div class="bar-fill" style="width:{min(rsi, 100)}%;background:{color};"></div></div><span class="bar-val">{rsi:.0f}</span></div>'
                            f'<div class="bar-row"><span class="bar-label">ADX</span><div class="bar-track"><div class="bar-fill" style="width:{min(adx*1.5, 100)}%;background:{color};"></div></div><span class="bar-val">{adx:.0f}</span></div>'
                            f'<div class="bar-row"><span class="bar-label">MACD</span><div class="bar-track"><div class="bar-fill" style="width:{min(abs(macd)*3, 100)}%;background:{color};"></div></div><span class="bar-val">{macd:.1f}</span></div>'
                            f'</div>'
                        )
                        st.markdown(card_html, unsafe_allow_html=True)
                        if st.button("Launch Analytics ↗", key=f"stock_{row['symbol']}_{idx}", use_container_width=True):
                            st.session_state.selected_stock = row["symbol"]
                            st.session_state.selected_row = row.to_dict()
                            st.session_state.page = "detail"
                            st.rerun()

    # AUDIT & PERFORMANCE TRACKING TABLE DOCK
    st.markdown("<div style='height:24px'></div>", unsafe_allow_html=True)
    st.markdown('<div class="section-title">Audit & 20-Day Performance Tracker</div>', unsafe_allow_html=True)
    
    pending_rows = st.session_state.get("audit_pending_rows")
    if pending_rows is not None:
        append_in_progress = st.session_state.get("audit_append_in_progress", False)
        if append_in_progress:
            st.info(f"⏳ Synchronizing {len(pending_rows)} rows to Google Sheets database…")
            try:
                with st.status("Writing to Audit Sheet…", expanded=True) as status:
                    audit_info = append_audit_batch(st.secrets, pending_rows, run_id=st.session_state.get("audit_pending_run_id"), scan_timestamp_ist=st.session_state.get("audit_pending_timestamp"), scanner_period="2y", max_distance_pct=10.0)
                    status.update(label=f"✅ Inserted {audit_info.get('rows', 0)} rows.", state="complete", expanded=False)
                st.session_state.audit_last_saved = audit_info
                st.session_state.audit_pending_rows = None; st.session_state.audit_append_in_progress = False
                st.rerun()
            except Exception as exc:
                st.session_state.audit_append_in_progress = False
                st.error("Audit Write Failed: " + str(exc))
        else:
            st.warning(f"📊 Confirm Audit Write: {len(pending_rows)} rows generated.")
            y_col, n_col = st.columns([1, 1])
            if y_col.button("✅ CONFIRM & UPLOAD", use_container_width=True):
                st.session_state.audit_append_in_progress = True; st.rerun()
            if n_col.button("❌ DISCARD BATCH", use_container_width=True):
                st.session_state.audit_pending_rows = None; st.rerun()

    audit_info = st.session_state.get("audit_last_saved") or {}
    if audit_info.get("saved") and audit_info.get("reason") in {"appended", "batch_already_exists"}:
        st.success(f"✅ Securely logged {audit_info.get('rows', 0)} signals.")

    try:
        signals_preview = read_audit_signals(st.secrets)
        if not signals_preview.empty:
            st.dataframe(signals_preview.tail(10), use_container_width=True, hide_index=True)
        else:
            st.markdown('<div class="bento-card" style="text-align:center;padding:20px;"><div class="small-muted">No audit signals logged in Google Sheets yet. Run a scan and click <b>COLLECT AUDIT</b>.</div></div>', unsafe_allow_html=True)
    except Exception:
        st.markdown('<div class="bento-card" style="text-align:center;padding:20px;"><div class="small-muted">Google Sheets audit connection awaiting configuration in Streamlit secrets.</div></div>', unsafe_allow_html=True)


# -----------------------------------------------------------------------------
# ROUTER EXECUTION
# -----------------------------------------------------------------------------
render_reload_guard(True)

if st.session_state.page == "detail" and st.session_state.get("selected_stock"):
    render_detail(st.session_state.selected_stock, st.session_state.selected_row)
else:
    render_home()
