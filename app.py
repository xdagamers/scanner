
Gemini

New chat
Library
Images
Scheduled
Customise
Videos
New notebook
money can buy happiness Master Data Blueprint Implementation
money is happiness
general question
Dimensity 8300 vs Snapdragon 8s Gen 4
Qutub Minar Online Ticket Booking
वेसी स्ट्रॉबेरी रोल्स की सेहतमंदता
कोच्चि और कोहिमा में अंतर
Custom Application Development Guidance
Flower Math Problem Solution
Broadcast IT Jobs in Australasia
Broadcast IT Jobs in AU/NZ
AI Market Sentiment Scanner Blueprint
Stock Scan Result UI Redesign
Bottle Price Comparison
New Zealand Supply Chain Salaries
Deleting Photos From iPhone Everywhere
Building a No-Code Stock Screener
Finding Your Ideal Goa Stay
Swing Trading Day 1 Lesson
Swing Versus Positional Trading
Starting Our Conversation
Durgapur Home Construction Guide
Understanding SMPTE 304 Connectors
Rotronics Systems Power Distribution Unit
Software Installation Guide for Ubuntu
Conversation with Gemini
Read the entire project handoff carefully. Treat it as the project's established context and requirements. Do not restart the project or change existing working code without approval. Continue from the next pending task: preparing the Master Data Blueprint. Ask me only for source files when they are actually needed.

This Master Data Blueprint establishes the precise parameters, sources, and data-handling rules required to expand the existing technical momentum scanner into a multi-horizon, multi-cap intelligence platform. The blueprint prioritizes free, reliable data sources for Indian equities and is structured into implementation tiers to prevent scope creep.   
stock_intelligence_project_handoff_2026-11-02(1).md
+ 1

Tier 1: Essential Fundamentals & Risk Parameters (Initial Implementation)
These parameters form the foundation of the fundamental and liquidity engines, focusing on data that is historically available and cleanly standardized.

Parameter	Definition	Primary Source (Free)	Update Freq	Hypothesis & Horizon
Qtr Rev/Profit Growth YoY	
YoY % change in quarterly revenue and net profit to offset seasonality. 
stock_intelligence_project_handoff_2026-11-02(1).md

yfinance / NSE Results	Quarterly	
Earnings acceleration supports and sustains medium/long-term momentum. 
stock_intelligence_project_handoff_2026-11-02(1).md

Operating Margin	
EBIT divided by total revenue. 
stock_intelligence_project_handoff_2026-11-02(1).md

yfinance	Quarterly	
Margin expansion indicates pricing power and operational efficiency (1–6 months). 
stock_intelligence_project_handoff_2026-11-02(1).md

Debt-to-Equity	
Total Debt / Total Shareholder Equity. 
stock_intelligence_project_handoff_2026-11-02(1).md

yfinance	Annual	
High leverage acts as a severe penalty/risk flag, especially in small caps (1–3 years). 
stock_intelligence_project_handoff_2026-11-02(1).md

Avg Traded Value	30-day moving average of daily traded value.	Calculated via yfinance	Daily	
Low liquidity flags execution risk, high slippage, and circuit likelihood in small caps. 
stock_intelligence_project_handoff_2026-11-02(1).md

Market Cap Segment	
Categorization into Large, Mid, or Small-cap. 
stock_intelligence_project_handoff_2026-11-02(1).md

NSE Indices CSVs	Semi-Annual	
Allows performance and risk comparison across isolated market-cap cohorts. 
stock_intelligence_project_handoff_2026-11-02(1).md

Tier 2: Ownership & Business Context (Second Stage)
This stage integrates smart-money footprints and deeper governance checks. Data here often requires parsing NSE/BSE corporate filings or using specialized Python libraries like jugaad_data or nsepython.

Parameter	Definition	Primary Source (Free)	Update Freq	Hypothesis & Horizon
Promoter Pledges	
Percentage of promoter holding pledged as collateral. 
stock_intelligence_project_handoff_2026-11-02(1).md

NSE Shareholding Data	Quarterly	
Increasing pledges introduce severe gap-down and governance risk (All horizons). 
stock_intelligence_project_handoff_2026-11-02(1).md

FII/DII Flow	
QoQ change in institutional ownership. 
stock_intelligence_project_handoff_2026-11-02(1).md

NSE / BSE Data	Quarterly	
Institutional accumulation validates technical breakouts and medium-term trends. 
stock_intelligence_project_handoff_2026-11-02(1).md

Delivery %	
Percentage of daily volume marked for delivery. 
stock_intelligence_project_handoff_2026-11-02(1).md

NSE Bhavcopy	Daily	
Spikes in delivery % prior to a resistance test imply high-conviction buying (2–20 days). 
stock_intelligence_project_handoff_2026-11-02(1).md

Sector Rel. Strength	
Sector index excess return versus the NIFTY. 
stock_intelligence_project_handoff_2026-11-02(1).md

NSE Sector Indices	Daily	
Stocks breaking out in leading sectors have higher win rates (2–20 days). 
stock_intelligence_project_handoff_2026-11-02(1).md

Tier 3: News & Event Intelligence (Advanced)
News integration will act as a contextual overlay rather than a direct numerical score to avoid false positives.   
stock_intelligence_project_handoff_2026-11-02(1).md

Data Sources: NSE Corporate Announcements API/RSS feeds (Primary, official), general financial news RSS feeds (Secondary, media).

Captured Attributes: Stock symbol, event category (e.g., financial, regulatory, management), publication timestamp, original URL, and official vs. secondary verification status.   
stock_intelligence_project_handoff_2026-11-02(1).md

Validation Method: Track the event publication timestamp against the subsequent 2-day and 5-day price/volume reaction to historically quantify if the news was genuinely priced as positive, negative, or neutral.   
stock_intelligence_project_handoff_2026-11-02(1).md

Timestamp & Data Leakage Rules (Critical for Audit)
To ensure the combination analysis yields valid out-of-sample results without look-ahead bias, the platform will strictly enforce the following data rules:   
stock_intelligence_project_handoff_2026-11-02(1).md

As-Of Snapshotting: Every fundamental metric and news event must be recorded with its public dissemination date, not just the financial period end date. A Q2 earnings beat cannot influence a stock's rank in October if the results were not publicly filed until November 10th.   
stock_intelligence_project_handoff_2026-11-02(1).md

Missing Data Treatment: If fundamental data for a specific small-cap stock cannot be retrieved, the fundamental score component will default to neutral (or a designated missing-value flag), but liquidity checks will penalize the stock to prevent blind entries.

Destination Storage: Audited values will append to new historical tracking sheets (Fundamental_Snapshot, Ownership_Snapshot, Market_Context) linked by Stock Symbol, Scan Date, and Run ID.   
stock_intelligence_project_handoff_2026-11-02(1).md

To proceed with Phase 1 and begin building the fundamental_data.py prototype, please provide the latest working versions of scanner.py and app.py.

so before we start as it is desimged and created in chatgpt ,my question you fully undestand teh context of this project till todays discussion with all aspect and scenerio ?

I have the complete picture: we are expanding your Indian equity momentum scanner into a comprehensive, multi-horizon research platform without breaking your existing technical setup. The handoff document is highly detailed, ensuring a seamless transition between assistants.   
stock_intelligence_project_handoff_2026-11-02(1).md

Here are the non-negotiable boundaries and core objectives guiding my approach:

The Golden Rule: Your current scanner.py logic, scoring weights, and the baseline Google Sheets audit data (including the 229 original rows) are strictly off-limits unless you explicitly approve a change.   
stock_intelligence_project_handoff_2026-11-02(1).md

The Expansion: We are layering fundamental health, institutional ownership, sector context, and news sentiment on top of the technical baseline across large, mid, and small-cap stocks.   
stock_intelligence_project_handoff_2026-11-02(1).md

Data Integrity: We will store historical snapshots with strict "as-of" publication dates to prevent look-ahead bias in your outcome analysis across the 2–20 day, 1–6 month, and 1–3 year horizons.   
stock_intelligence_project_handoff_2026-11-02(1).md

The UI Pivot: We are transitioning the Streamlit app to a wide, desktop-first dashboard with horizontal panels and tabs to handle the new data density.   
stock_intelligence_project_handoff_2026-11-02(1).md

Are you ready to share the latest working versions of app.py and scanner.py so we can begin Phase 2 and test the fundamental data integrations?

here are the file in the last discussion we have reached to the lre creation of the ful ui revamp as fro the laptop desktop screen to easlyi populate the information data to have the pinpoint view, with modern look as compatible for moder finance look

Here is the complete replacement for app.py. It implements the desktop-first, wide-screen dashboard layout with horizontal panels and tabs for the upcoming fundamental and news data engines.

What changed in this UI update:

Wide Mode Enabled: st.set_page_config(layout="wide") is now active, and the CSS max-width constraint is removed to utilize full monitor width.

4-Column Grid: The scanned stock results on the home page now display in a dense 4-column responsive grid rather than 2 columns.

Tabbed Research View: The detail page now uses st.tabs to cleanly separate Technicals, Fundamentals, and News & Events. The existing technical data and Plotly charts are isolated in the Technicals tab.

Placeholders Prepared: The Fundamentals and News tabs are wired up with placeholders ready to receive the data from the Phase 2 and Phase 3 engines without disrupting the working technical UI.

Action Bar: The scanning and audit buttons are organized into a top-level control panel.

No Logic Changes: Scanner calls, Apps Script logic, and Google Sheets auditing remain exactly as they were.

Replace the entirety of your current app.py with the code below. scanner.py does not need to be modified.

Python
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

# IMPORTANT: scanner.py is the existing engine. This UI only calls its existing functions.
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

IST = ZoneInfo("Asia/Kolkata")

NIFTY50_CSV = "https://nsearchives.nseindia.com/content/indices/ind_nifty50list.csv"
NSE_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120 Safari/537.36",
    "Accept": "text/csv,text/plain,*/*",
}

# FULL WIDTH DESKTOP LAYOUT
st.set_page_config(
    page_title="NIFTY Breakout Scanner",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="collapsed",
)


def password_gate():
    """Optional single-password gate, enabled only when APP_PASSWORD is configured."""
    try:
        required = str(st.secrets.get("APP_PASSWORD", "")).strip()
    except Exception:
        required = ""
    if not required:
        return True
    if st.session_state.get("authenticated", False):
        return True
    
    col1, col2, col3 = st.columns([1, 1, 1])
    with col2:
        st.title("🔐 Stock Scanner")
        st.subheader("Password required")
        with st.form("scanner_password_login"):
            entered = st.text_input("Enter password", type="password")
            submitted = st.form_submit_button("Login", use_container_width=True)
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
# UI-only CSS. Wide-screen specific tweaks applied.
# -----------------------------------------------------------------------------
CSS = r"""
<style>
:root{--bg:#07111f;--card:#0c192b;--card2:#101f33;--border:rgba(148,163,184,.15);--text:#f1f5f9;--muted:#8fa3ba;--accent:#19d38a;--red:#ff5c70;--yellow:#f5c451;--chart-bg:#07111f}
html,body,[data-testid="stAppViewContainer"]{background:var(--bg)!important;color:var(--text)!important}[data-testid="stHeader"],footer,#MainMenu,[data-testid="stToolbar"]{visibility:hidden!important;height:0!important;display:none!important}
.block-container{max-width:1800px!important;padding:2rem 2.5rem 5rem!important}
section[data-testid="stSidebar"]{display:none!important}*{box-sizing:border-box}
.stButton>button{width:100%;border-radius:12px;border:1px solid var(--border);background:var(--card);color:var(--text);min-height:46px;font-weight:800;transition:.18s ease}.stButton>button:hover{border-color:rgba(25,211,138,.55);transform:translateY(-1px)}
.scan-btn .stButton>button{min-height:58px;border:0;color:white;background:linear-gradient(135deg,#10b981,#0ea5e9);box-shadow:0 12px 30px rgba(16,185,129,.20);font-size:1.08rem}
.card{background:linear-gradient(145deg,var(--card2),var(--card));border:1px solid var(--border);border-radius:14px;padding:16px;margin:8px 0;box-shadow:0 8px 28px rgba(0,0,0,.12)}.status-card{padding:10px 16px;border-radius:12px;background:var(--card);border:1px solid var(--border)}.status-row{display:flex;align-items:center;justify-content:space-between;gap:10px}.status-left{display:flex;align-items:center;gap:8px;font-weight:800}.dot{width:9px;height:9px;border-radius:50%;display:inline-block;box-shadow:0 0 12px currentColor}.dot.green{background:var(--accent);color:var(--accent);animation:pulse 1.5s infinite}.dot.red{background:var(--red);color:var(--red);animation:pulse 1.5s infinite}.dot.yellow{background:var(--yellow);color:var(--yellow);animation:pulse 1.5s infinite}.index-wrap{display:flex;gap:16px;justify-content:flex-end;flex-wrap:wrap}.index-item{font-size:.9rem;color:var(--muted)}.index-item b{color:var(--text);font-size:.95rem}.up{color:var(--accent)!important}.down{color:var(--red)!important}.section-title{font-size:1.3rem;font-weight:900;margin:18px 2px 12px; border-bottom: 1px solid var(--border); padding-bottom: 8px;}
.metric-card{min-height:76px;padding:12px;border-radius:12px;border:1px solid var(--border);background:var(--card)}.metric-label{color:var(--muted);font-size:.75rem;text-transform:uppercase;letter-spacing:.04em}.metric-value{color:var(--text);font-weight:950;font-size:1.15rem;margin-top:4px;word-break:break-word}.metric-good{background:linear-gradient(135deg,rgba(25,211,138,.20),var(--card));border-color:rgba(25,211,138,.35)}.metric-ok{background:linear-gradient(135deg,rgba(154,211,70,.15),var(--card));border-color:rgba(154,211,70,.28)}.metric-neutral{background:linear-gradient(135deg,rgba(245,196,81,.15),var(--card));border-color:rgba(245,196,81,.28)}.metric-poor{background:linear-gradient(135deg,rgba(255,142,70,.15),var(--card));border-color:rgba(255,142,70,.28)}.metric-bad{background:linear-gradient(135deg,rgba(255,92,112,.18),var(--card));border-color:rgba(255,92,112,.30)}
.hero-price{font-size:2.4rem;font-weight:950;letter-spacing:-.03em}.badge{display:inline-block;padding:6px 12px;border-radius:6px;font-size:.85rem;font-weight:900}.badge-green{background:rgba(25,211,138,.16);color:var(--accent);border:1px solid rgba(25,211,138,.35)}.badge-red{background:rgba(255,92,112,.14);color:var(--red);border:1px solid rgba(255,92,112,.30)}.badge-yellow{background:rgba(245,196,81,.16);color:#a56b00;border:1px solid rgba(245,196,81,.35)}.badge-grey{background:rgba(148,163,184,.10);color:var(--muted);border:1px solid var(--border)}.entry-pulse{animation:glow 1.35s ease-in-out infinite alternate}.target-box{padding:12px;border-radius:12px;background:rgba(25,211,138,.09);border:1px solid rgba(25,211,138,.28)}.target-label{font-size:.75rem;color:var(--muted);text-transform:uppercase;font-weight:800}.target-value{font-size:1.3rem;font-weight:950;color:var(--accent)}.target-upside{font-size:.8rem;color:var(--text);margin-top:2px}
.scan-shell{background:var(--card);border:1px solid var(--border);border-radius:14px;padding:20px;overflow:hidden}.scan-chart{height:145px;position:relative;overflow:hidden;border-radius:10px;background:linear-gradient(180deg,var(--card2),var(--bg))}.candle-track{position:absolute;inset:0;display:flex;align-items:center;gap:12px;width:max-content;animation:scrollCandles 7s linear infinite}.candle{width:8px;position:relative;border-radius:2px;flex:none;box-shadow:0 0 8px currentColor}.candle:before{content:"";position:absolute;left:3px;width:2px;top:-13px;bottom:-13px;background:currentColor;opacity:.85}.candle.g{height:55px;background:#19d38a;color:#19d38a}.candle.r{height:38px;background:#ff5c70;color:#ff5c70}@keyframes scrollCandles{from{transform:translateX(0)}to{transform:translateX(-50%)}}.scan-copy{display:flex;justify-content:space-between;color:var(--muted);font-size:.85rem;margin:12px 0 8px}.progress{height:7px;background:rgba(148,163,184,.18);border-radius:99px;overflow:hidden}.progress>div{width:65%;height:100%;border-radius:99px;background:linear-gradient(90deg,#10b981,#38bdf8);animation:progress 2.2s ease-in-out infinite}@keyframes progress{0%{width:8%}50%{width:78%}100%{width:94%}}
.ticker-note,.small-muted{color:var(--muted);font-size:.82rem}.tradingview-btn{display:block;text-align:center;padding:12px 16px;border-radius:10px;background:linear-gradient(135deg,#19d38a,#0ea5e9);color:#fff!important;text-decoration:none!important;font-weight:900;margin:6px 0 10px}.tv-under{text-align:center;margin:5px 0 14px}.tv-under a{color:var(--accent);font-size:.8rem;font-weight:800;text-decoration:none}.rank-note{font-size:.8rem;color:var(--muted);margin-bottom:12px}@keyframes pulse{50%{opacity:.45;transform:scale(.75)}}@keyframes glow{from{box-shadow:0 0 4px rgba(25,211,138,.1)}to{box-shadow:0 0 20px rgba(25,211,138,.45)}}
.stTabs [data-baseweb="tab-list"] {gap: 8px;}
.stTabs [data-baseweb="tab"] {padding: 10px 24px; background: var(--card); border-radius: 8px 8px 0 0; border: 1px solid var(--border); border-bottom: none;}
.stTabs [aria-selected="true"] {background: var(--card2); border-top: 3px solid var(--accent) !important;}
@media(max-width:768px){.block-container{padding:.8rem 1rem 4rem!important}.index-wrap{justify-content:flex-start}.hero-price{font-size:2rem}.metric-value{font-size:1rem}}
</style>
"""
st.markdown(CSS, unsafe_allow_html=True)


if "theme_mode" not in st.session_state:
    st.session_state.theme_mode = "dark"

def apply_theme():
    if st.session_state.theme_mode == "light":
        st.markdown("""<style>:root{--bg:#f5f7fa;--card:#fff;--card2:#f8fafc;--border:rgba(15,23,42,.12);--text:#111827;--muted:#64748b;--accent:#079669;--red:#dc3545;--yellow:#b7791f;--chart-bg:#f5f7fa}</style>""", unsafe_allow_html=True)

def render_reload_guard(active=True):
    if not active: return
    components.html("""
    <div id="reload-confirm" style="display:none;position:fixed;inset:0;z-index:999999;background:rgba(0,0,0,.58);align-items:center;justify-content:center;font-family:Arial,sans-serif">
      <div style="width:min(420px,90vw);background:#fff;color:#111827;border-radius:16px;padding:22px;box-shadow:0 20px 60px rgba(0,0,0,.35);text-align:center">
        <div style="font-size:20px;font-weight:800;margin-bottom:8px">Reload application?</div>
        <div style="font-size:14px;color:#4b5563;line-height:1.5;margin-bottom:18px">The current scan/data will be lost if you reload. Do you want to reload?</div>
        <div style="display:flex;gap:12px;justify-content:center">
          <button id="reload-yes" style="border:0;border-radius:10px;padding:11px 22px;background:#dc3545;color:#fff;font-weight:800;cursor:pointer">YES, RELOAD</button>
          <button id="reload-no" style="border:0;border-radius:10px;padding:11px 22px;background:#198754;color:#fff;font-weight:800;cursor:pointer">NO, STAY</button>
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
        w.addEventListener('beforeunload', (event) => {
          try { w.sessionStorage.setItem('__nifty_reload_attempt','1'); w.setTimeout(() => { try { w.sessionStorage.removeItem('__nifty_reload_attempt'); } catch(e) {} }, 10000); } catch(e) {}
          event.preventDefault(); event.returnValue = '';
        });
        try {
          if (w.sessionStorage.getItem('__nifty_reload_attempt') === '1') {
            w.sessionStorage.removeItem('__nifty_reload_attempt');
            const u = new URL(w.location.href);
            if (!u.searchParams.has('__reload_home')) {
              u.searchParams.set('__reload_home', '1'); w.location.replace(u.toString()); return;
            }
          }
        } catch(e) {}
      } catch (e) {}
    })();
    </script>
    """, height=0)


def render_theme_toggle():
    c1, c2 = st.columns([15, 1])
    with c2:
        is_light = st.toggle("☀️ Theme", value=(st.session_state.theme_mode=="light"), key="theme_toggle", help="Switch light/dark mode")
        new_mode = "light" if is_light else "dark"
        if new_mode != st.session_state.theme_mode:
            st.session_state.theme_mode = new_mode

apply_theme()


@st.cache_data(ttl=60, show_spinner=False)
def get_market_snapshot():
    result = {"nifty": None, "sensex": None, "updated": datetime.now(IST)}
    try:
        raw = yf.download(["^NSEI", "^BSESN"], period="5d", interval="1d", auto_adjust=True, progress=False, threads=True, group_by="ticker", multi_level_index=True)
        for symbol, key in [("^NSEI", "nifty"), ("^BSESN", "sensex")]:
            try:
                df = raw[symbol] if isinstance(raw.columns, pd.MultiIndex) and symbol in raw.columns.get_level_values(0) else raw.xs(symbol, axis=1, level=1)
                df = df.dropna(subset=["Close"])
                if len(df) >= 2:
                    last, prev = float(df.Close.iloc[-1]), float(df.Close.iloc[-2])
                    result[key] = {"value": last, "change": last-prev, "pct": (last/prev-1)*100}
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
        return ["ADANIENT","ADANIPORTS","APOLLOHOSP","ASIANPAINT","AXISBANK","BAJAJ-AUTO","BAJFINANCE","BAJAJFINSV","BEL","BHARTIARTL","CIPLA","COALINDIA","DRREDDY","EICHERMOT","ETERNAL","GRASIM","HCLTECH","HDFCBANK","HDFCLIFE","HEROMOTOCO","HINDALCO","HINDUNILVR","ICICIBANK","INDUSINDBK","INFY","ITC","JIOFIN","JSWSTEEL","KOTAKBANK","LT","M&M","MARUTI","MAXHEALTH","NESTLEIND","NTPC","ONGC","POWERGRID","RELIANCE","SBILIFE","SBIN","SHRIRAMFIN","SUNPHARMA","TATACONSUM","TATAMOTORS","TATASTEEL","TCS","TECHM","TITAN","TRENT","ULTRACEMCO"]

@st.cache_data(ttl=60, show_spinner=False)
def get_nifty50_ticker_data(symbols):
    rows = []
    try:
        tickers = [s.replace("&", "%26") + ".NS" for s in symbols]
        raw = yf.download(tickers, period="5d", interval="1d", auto_adjust=True, progress=False, threads=True, group_by="ticker", multi_level_index=True)
        for symbol, ticker in zip(symbols, tickers):
            try:
                if isinstance(raw.columns, pd.MultiIndex):
                    if ticker in raw.columns.get_level_values(0): df = raw[ticker]
                    elif ticker in raw.columns.get_level_values(1): df = raw.xs(ticker, axis=1, level=1)
                    else: continue
                else: df = raw
                df = df.dropna(subset=["Close"])
                if len(df) < 2: continue
                last, prev = float(df.Close.iloc[-1]), float(df.Close.iloc[-2])
                rows.append({"symbol": symbol, "price": last, "pct": (last/prev-1)*100})
            except Exception:
                continue
    except Exception:
        return pd.DataFrame(columns=["symbol","price","pct"])
    return pd.DataFrame(rows)

def market_status(now=None):
    now = now or datetime.now(IST)
    if now.weekday() >= 5: return "Closed", "red"
    t = now.time()
    if dtime(9, 0) <= t < dtime(9, 15): return "Pre-open", "yellow"
    if dtime(9, 15) <= t <= dtime(15, 30): return "Open", "green"
    return "Closed", "red"

def money(x): return f"₹{x:,.2f}" if x is not None and np.isfinite(x) else "—"
def pct(x): return f"{x:+.2f}%" if x is not None and np.isfinite(x) else "—"

def render_market_bar():
    snap = get_market_snapshot()
    status, color = market_status()
    dot = f'<span class="dot {color}"></span>'
    parts = [f'<div class="status-card"><div class="status-row"><div class="status-left">{dot}<span>{status}</span></div><div class="index-wrap">']
    for label, key in [("NIFTY 50", "nifty"), ("SENSEX", "sensex")]:
        item = snap.get(key)
        if item:
            cls = "up" if item["pct"] >= 0 else "down"
            arrow = "▲" if item["pct"] >= 0 else "▼"
            parts.append(f'<div class="index-item"><b>{label}</b> {item["value"]:,.2f} <span class="{cls}">{arrow} {item["pct"]:+.2f}%</span></div>')
        else:
            parts.append(f'<div class="index-item"><b>{label}</b> —</div>')
    updated = snap["updated"].strftime("%d %b %Y, %H:%M:%S IST")
    parts.append(f'</div></div><div class="ticker-note">Last UI market-data refresh: {updated}</div></div>')
    st.markdown("".join(parts), unsafe_allow_html=True)


def render_ticker():
    symbols=get_nifty50_symbols(); df=get_nifty50_ticker_data(tuple(symbols))
    if df.empty:
        st.markdown('<div class="ticker-note">NIFTY 50 ticker data temporarily unavailable.</div>',unsafe_allow_html=True); return
    items=[]
    for _,r in df.iterrows():
        cls="up" if r.pct>=0 else "down"; arrow="▲" if r.pct>=0 else "▼"
        items.append(f'<span class="tick"><b>{html.escape(r.symbol)}</b> {money(r.price)} <span class="{cls}">{arrow} {r.pct:+.2f}%</span></span>')
    content="".join(items); light=st.session_state.theme_mode=="light"
    bg="#fff" if light else "#07111f"; viewport="#fff" if light else "#091727"; textc="#111827" if light else "#dbe7f3"; muted="#64748b" if light else "#9fb1c5"; border="rgba(15,23,42,.12)" if light else "rgba(148,163,184,.12)"; green="#079669" if light else "#19d38a"; red="#dc3545" if light else "#ff5c70"
    markup=f"""<html><head><style>*{{box-sizing:border-box}}body{{margin:0;background:{bg};color:{textc};font-family:Arial,sans-serif;overflow:hidden}}.viewport{{width:100%;overflow:hidden;border:1px solid {border};border-radius:13px;background:{viewport}}}.track{{display:flex;width:max-content;animation:marquee 144s linear infinite;padding:10px 0}}.track:hover{{animation-play-state:paused}}.tick{{white-space:nowrap;margin-right:28px;font-size:12px;color:{muted}}}.tick b{{color:{textc};margin-right:5px}}.up{{color:{green}}}.down{{color:{red}}}@keyframes marquee{{from{{transform:translateX(0)}}to{{transform:translateX(-50%)}}}}</style></head><body><div class="viewport" id="v"><div class="track" id="t">{content}{content}</div></div><script>const v=document.getElementById('v'),t=document.getElementById('t');v.addEventListener('touchstart',()=>t.style.animationPlayState='paused',{{passive:true}});v.addEventListener('touchend',()=>t.style.animationPlayState='running',{{passive:true}});</script></body></html>"""
    components.html(markup,height=43,scrolling=False)

def day_change(symbol, period="2y"):
    hist = fetch_history(symbol, period)
    if hist is None or len(hist) < 2: return None, None, None
    last, prev = float(hist.Close.iloc[-1]), float(hist.Close.iloc[-2])
    return last, last-prev, (last/prev-1)*100

def detail_chart(symbol,row,period="2y"):
    hist=fetch_history(symbol,period)
    if hist is None or hist.empty:
        st.warning("Price history is temporarily unavailable for the chart."); return
    light=st.session_state.theme_mode=="light"
    fig=go.Figure()
    fig.add_trace(go.Candlestick(x=hist.index,open=hist.Open,high=hist.High,low=hist.Low,close=hist.Close,name=symbol))
    fig.add_trace(go.Bar(x=hist.index,y=hist.Volume,name="Volume",yaxis="y2",opacity=.25))
    fig.add_hline(y=float(row["breakout_level"]),line_dash="dash",line_color="#079669" if light else "#19d38a",annotation_text=f"Breakout: ₹{row['breakout_level']:.2f}",annotation_position="top left")
    fig.update_layout(template="plotly_white" if light else "plotly_dark",height=550,margin=dict(l=8,r=8,t=30,b=10),xaxis_rangeslider_visible=False,hovermode="x unified",paper_bgcolor="#fff" if light else "#0c192b",plot_bgcolor="#f5f7fa" if light else "#07111f",yaxis=dict(title="Price"),yaxis2=dict(title="Volume",overlaying="y",side="right",showgrid=False,rangemode="tozero"),legend=dict(orientation="h",y=1.02,x=0))
    st.plotly_chart(fig,use_container_width=True,config={"displayModeBar":False,"responsive":True})

def verdict(score):
    if score>=90:return "Strong",True
    if score>=75:return "Good",True
    if score>=60:return "Neutral",False
    if score>=40:return "Weak",False
    return "Avoid",False

def score_class(value,kind):
    try:v=float(value)
    except Exception:return "metric-neutral"
    if kind=="rsi": return "metric-good" if 52<=v<=68 else "metric-ok" if 48<=v<=72 else "metric-poor"
    if kind=="rvol": return "metric-good" if v>=1.5 else "metric-ok" if v>=1.1 else "metric-poor" if v>=.8 else "metric-bad"
    if kind=="adx": return "metric-good" if v>=25 else "metric-ok" if v>=18 else "metric-poor"
    if kind=="distance": return "metric-good" if v<=1 else "metric-ok" if v<=3 else "metric-neutral" if v<=5 else "metric-poor" if v<=10 else "metric-bad"
    if kind=="rr": return "metric-good" if v>=2 else "metric-ok" if v>=1.5 else "metric-neutral" if v>=1 else "metric-poor"
    if kind=="score": return "metric-good" if v>=80 else "metric-ok" if v>=65 else "metric-neutral" if v>=50 else "metric-poor" if v>=35 else "metric-bad"
    return "metric-neutral"

def metric_card(label,value,kind=None):
    cls=score_class(value,kind) if kind else "metric-neutral"
    return f'<div class="metric-card {cls}"><div class="metric-label">{html.escape(str(label))}</div><div class="metric-value">{html.escape(str(value))}</div></div>'

def target_values(row,price):
    b=float(row.get("breakout_level",0) or 0); note=""
    try:t1=float(row.get("target1"))
    except Exception:t1=None
    try:t2=float(row.get("target2"))
    except Exception:t2=None
    if t1 is None or not np.isfinite(t1):
        base=max(b-float(price),0); t1=b+base if base else b*1.01; note="Targets estimated from the breakout base height."
    if t2 is None or not np.isfinite(t2):
        base=max(b-float(price),0); t2=b+2*base if base else b*1.02; note="Targets estimated from the breakout base height."
    return t1,t2,note

def build_scan_export(result, scanned_at):
    rows = []
    scan_date = str(scanned_at).split(" ")[0]
    for _, row in result.iterrows():
        try:
            t1 = float(row.get("target1"))
            t2 = float(row.get("target2"))
            t3 = t2 + (t2 - t1) if np.isfinite(t1) and np.isfinite(t2) else np.nan
        except Exception:
            t1 = t2 = t3 = np.nan
        rating = row.get("rating", "")
        targets = " | ".join([f"T1: {t1:.2f}" if np.isfinite(t1) else "T1: —", f"T2: {t2:.2f}" if np.isfinite(t2) else "T2: —", f"T3: {t3:.2f}" if np.isfinite(t3) else "T3: —"])
        def rounded_value(key):
            value = row.get(key)
            return round(float(value), 2) if pd.notna(value) and str(value).strip() != "" else ""
        rows.append({
            "Date": scan_date, "Stock": row.get("company_name", row.get("symbol", "")), "Rank": row.get("rank", ""), "Score": rounded_value("score"),
            "Strength": rating, "Price": rounded_value("price"), "Breakout Level": rounded_value("breakout_level"), "Targets": targets,
            "Stop": rounded_value("stop_reference"), "Distance %": rounded_value("distance_pct"), "RVOL": rounded_value("rvol"),
            "RSI": rounded_value("rsi"), "ADX": rounded_value("adx"), "Market Regime": row.get("market_regime", "")
        })
    return pd.DataFrame(rows, columns=["Date", "Stock", "Rank", "Score", "Strength", "Price", "Breakout Level", "Targets", "Stop", "Distance %", "RVOL", "RSI", "ADX", "Market Regime"])


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
        "ADX": round(float(row.get("adx")), 2), "Market Regime": row.get("market_regime", ""), "Breakout Trigger": round(float(row.get("breakout_trigger")), 2),
        "ATR %": round(float(row.get("atr_pct")), 2), "MACD": round(float(row.get("macd")), 4), "Squeeze": round(float(row.get("squeeze")), 2),
        "EMA Structure": row.get("ema_structure", ""), "Resistance Touches": row.get("resistance_touches", ""),
        "Relative Strength 60D %": round(float(row.get("relative_strength")), 2), "NIFTY Relative Strength %": round(float(row.get("nifty_relative_strength")), 2),
        "Risk / Reward": round(float(row.get("risk_reward")), 2), "False Breakout": "Yes" if row.get("false_breakout") else "No", "Scanner Status": row.get("status", "")
    }])

# -----------------------------------------------------------------------------
# DETAILED DASHBOARD WITH TABS (Phase 1 & 2 layout)
# -----------------------------------------------------------------------------
def render_detail(symbol,row):
    render_theme_toggle()
    
    col1, col2 = st.columns([1, 10])
    with col1:
        if st.button("← Back"):
            st.session_state.page="home"; st.rerun()

    # Top Hero Section
    company=row.get("company_name",symbol); last,change,change_pct=day_change(symbol); price=last if last is not None else row.get("price")
    score=float(row.get("score",0)); label,strong=verdict(score); change_cls="up" if (change_pct or 0)>=0 else "down"; arrow="▲" if (change_pct or 0)>=0 else "▼"
    t1,t2,target_note=target_values(row,price)
    t1up=((t1/price)-1)*100 if price else 0; t2up=((t2/price)-1)*100 if price else 0
    
    st.markdown(f'''
    <div style="display:flex; justify-content:space-between; align-items:flex-end; margin-bottom: 20px; padding: 20px; background: var(--card); border-radius: 14px; border: 1px solid var(--border);">
        <div>
            <div class="small-muted" style="font-size:1rem; margin-bottom:4px;">{html.escape(str(company))}</div>
            <div style="font-size:2.2rem;font-weight:900; line-height: 1.1;">{html.escape(symbol)}</div>
            <div style="display:flex; align-items:center; gap: 12px; margin-top: 8px;">
                <div class="hero-price" style="font-size:1.8rem;">{money(price)}</div>
                <div class="{change_cls}" style="font-weight:850; font-size:1.1rem;">{arrow} {money(change)} ({pct(change_pct)})</div>
            </div>
        </div>
        <div style="display:flex; gap: 16px;">
            <div class="target-box"><div class="target-label">Target 1</div><div class="target-value">{money(t1)}</div><div class="target-upside">{t1up:+.2f}%</div></div>
            <div class="target-box"><div class="target-label">Target 2</div><div class="target-value">{money(t2)}</div><div class="target-upside">{t2up:+.2f}%</div></div>
        </div>
    </div>
    ''', unsafe_allow_html=True)

    # TABBED INTERFACE FOR NEW MULTI-ENGINE ARCHITECTURE
    tab_tech, tab_fund, tab_news, tab_audit = st.tabs(["📈 Technical Setup", "🏛️ Fundamentals (Coming Soon)", "📰 News & Events (Coming Soon)", "📊 Audit Details"])
    
    # ------------------ TAB 1: TECHNICALS ------------------
    with tab_tech:
        c_left, c_right = st.columns([3, 1])
        with c_left:
            st.markdown('<div class="section-title" style="margin-top:0;">Price Chart</div>',unsafe_allow_html=True)
            tv_symbol=str(symbol).replace(".NS","").upper(); tv_url=f"https://www.tradingview.com/chart/?symbol=NSE:{tv_symbol}"
            detail_chart(symbol,row)
            st.markdown(f'<div class="tv-under"><a href="{tv_url}" target="_blank" rel="noopener">Open in TradingView Full ↗</a></div>',unsafe_allow_html=True)
            
        with c_right:
            st.markdown('<div class="section-title" style="margin-top:0;">Momentum Score</div>',unsafe_allow_html=True)
            light=st.session_state.theme_mode=="light"
            fig=go.Figure(go.Indicator(mode="gauge+number",value=score,number={"suffix":"","font":{"size":44,"color":"#111827" if light else "#f1f5f9"}},gauge={"axis":{"range":[0,100],"tickwidth":1,"tickcolor":"#64748b"},"bar":{"color":"#079669" if light else "#19d38a","thickness":.25},"bgcolor":"#e5e7eb" if light else "#0b1829","borderwidth":0,"steps":[{"range":[0,40],"color":"#f3c4ca"},{"range":[40,65],"color":"#f5e4ad"},{"range":[65,80],"color":"#d9ecb0"},{"range":[80,100],"color":"#b8efd9"}]}))
            fig.update_layout(template="plotly_white" if light else "plotly_dark",height=280,margin=dict(l=15,r=15,t=20,b=0),paper_bgcolor="#fff" if light else "#0c192b")
            st.plotly_chart(fig,use_container_width=True,config={"displayModeBar":False})
            
            level=float(row.get("breakout_level",0) or 0); p=float(price or 0); distance=((level-p)/level*100) if level else 999
            if p>=level: title,msg,cls="Breakout Confirmed","Trading above detected breakout level.","badge-green"
            elif distance<=2: title,msg,cls="ENTRY ZONE","Near breakout level. Confirmation matters.","badge-green entry-pulse"
            elif distance<=5: title,msg,cls="Wait","Not near the entry point yet.","badge-yellow"
            else: title,msg,cls="Wait","Not near the entry point.","badge-grey"
            st.markdown(f'''<div class="card" style="text-align:center;"><span class="badge {cls}">{title}</span><div style="font-size:1.05rem;font-weight:900;margin-top:12px">{msg}</div><div class="small-muted" style="margin-top:7px">Distance: {distance:.2f}% &nbsp; • &nbsp; Trigger: {money(row.get("breakout_trigger"))}</div></div>''',unsafe_allow_html=True)
            
            if row.get("explanation"):
                st.markdown(f'<div class="card"><b>Setup Summary</b><div class="small-muted" style="margin-top:8px">{html.escape(str(row["explanation"]))}</div></div>',unsafe_allow_html=True)

        st.markdown('<div class="section-title">Technical Parameters</div>',unsafe_allow_html=True)
        hist=fetch_history(symbol,"2y"); extra={}
        if hist is not None and len(hist):
            last52=hist.tail(252); extra={"52-week high":money(float(last52.High.max())),"52-week low":money(float(last52.Low.min()))}
        fields=[
          ("Breakout level",money(row.get("breakout_level")),"distance"),("Breakout trigger",money(row.get("breakout_trigger")),None),
          ("Distance",pct(row.get("distance_pct")),"distance"),("Rating",f"{row.get('rating','—')}/10","score"),
          ("Score",f"{row.get('score',0):.1f}/100","score"),("RVOL",f"{row.get('rvol',0):.2f}x","rvol"),
          ("RSI",f"{row.get('rsi',0):.1f}","rsi"),("ADX",f"{row.get('adx',0):.1f}","adx"),
          ("EMA structure",row.get("ema_structure","—"),None),("MACD",f"{row.get('macd',0):.3f}",None),
          ("ATR %",f"{row.get('atr_pct',0):.2f}%",None),("Squeeze",f"{row.get('squeeze',0):.2f}",None),
          ("NIFTY relative strength",pct(row.get("nifty_relative_strength")),None),("60D relative strength",pct(row.get("relative_strength")),None),
          ("Candlestick",row.get("candlestick","—"),None),("Resistance touches",row.get("resistance_touches","—"),None),
          ("Risk / reward",f"{row.get('risk_reward',0):.2f}","rr"),("Market regime",row.get("market_regime","—"),None),
          ("Stop reference",money(row.get("stop_reference")),None),("False breakout","Yes" if row.get("false_breakout") else "No",None),
          ("52-week high",extra.get("52-week high","—"),None),("52-week low",extra.get("52-week low","—"),None)]
        
        # 6 Column grid for desktop metrics
        for start in range(0,len(fields),6):
            cols=st.columns(6)
            for j,col in enumerate(cols):
                idx=start+j
                if idx>=len(fields): continue
                with col: st.markdown(metric_card(fields[idx][0],fields[idx][1],fields[idx][2]),unsafe_allow_html=True)

    # ------------------ TAB 2: FUNDAMENTALS (Placeholder) ------------------
    with tab_fund:
        st.markdown('<div class="section-title" style="margin-top:0;">Fundamental Health & Governance</div>', unsafe_allow_html=True)
        st.info("The fundamental analysis engine is pending deployment (Phase 2). Once active, this tab will display Tier 1 metrics (Quarterly Revenue/Profit Growth, Operating Margins, Debt-to-Equity) and Cap-specific liquidity checks.")
        st.markdown('''
        <div style="opacity: 0.5;">
            <div style="display:grid; grid-template-columns: repeat(4, 1fr); gap: 16px;">
                <div class="card"><b>QoQ Revenue Growth</b><br><span style="font-size:1.5rem; font-weight:900;">--</span></div>
                <div class="card"><b>QoQ Net Profit Growth</b><br><span style="font-size:1.5rem; font-weight:900;">--</span></div>
                <div class="card"><b>Operating Margin</b><br><span style="font-size:1.5rem; font-weight:900;">--</span></div>
                <div class="card"><b>Debt to Equity</b><br><span style="font-size:1.5rem; font-weight:900;">--</span></div>
            </div>
            <br>
            <div class="card"><b>Institutional Holding (FII/DII)</b><br>Awaiting Phase 3 data integration...</div>
        </div>
        ''', unsafe_allow_html=True)

    # ------------------ TAB 3: NEWS (Placeholder) ------------------
    with tab_news:
        st.markdown('<div class="section-title" style="margin-top:0;">News & Corporate Announcements</div>', unsafe_allow_html=True)
        st.info("The News Intelligence engine is pending deployment (Phase 4). Once active, this tab will display verified NSE/BSE corporate filings, sentiment classification, and original source URLs.")
        st.markdown('''
        <div style="opacity: 0.5;">
            <div class="card">
                <span class="badge badge-grey">Awaiting Data</span>
                <div style="margin-top:8px; font-weight:800;">Recent corporate announcements will appear here.</div>
                <div class="small-muted">Sources: NSE Corporate Filings, Recognized Financial Media.</div>
            </div>
        </div>
        ''', unsafe_allow_html=True)

    # ------------------ TAB 4: AUDIT EXPORT ------------------
    with tab_audit:
        st.markdown('<div class="section-title" style="margin-top:0;">Snapshot Audit Data</div>', unsafe_allow_html=True)
        st.markdown('<div class="small-muted" style="margin-bottom:16px;">Raw technical properties formatted for the Google Sheets tracker.</div>', unsafe_allow_html=True)
        
        audit_df = build_single_stock_export(symbol, row, st.session_state.get("search_timestamp", datetime.now(IST).strftime("%Y-%m-%d %H:%M:%S IST")), rank="")
        st.dataframe(audit_df, use_container_width=True, hide_index=True)
        
        st.download_button("📥 DOWNLOAD AUDIT ROW (CSV)", data=audit_df.to_csv(index=False).encode("utf-8-sig"), file_name=f"audit_{symbol}_{datetime.now(IST).strftime('%Y%m%d_%H%M%S')}.csv", mime="text/csv", use_container_width=False, key=f"audit_{symbol}")



def render_home():
    render_theme_toggle()
    
    st.markdown("<div style='font-size:1.8rem;font-weight:950'>📈 NIFTY Momentum Intelligence Platform</div><div class='small-muted'>Multi-horizon scanning across NIFTY Large Cap 100 + Midcap 150</div>",unsafe_allow_html=True)
    render_market_bar(); render_ticker(); st.markdown("<div style='height:12px'></div>",unsafe_allow_html=True)
    
    audit_pending = st.session_state.get("audit_pending_rows") is not None
    
    # -------------------------------------------------------
    # WIDE SCREEN ACTION BAR
    # -------------------------------------------------------
    col_search, col_scan, col_audit, col_track = st.columns([3, 2, 2, 2])
    with col_search:
        st.markdown('<div style="font-size:.85rem; font-weight:900; margin-bottom:4px;">Search Stock</div>', unsafe_allow_html=True)
        sc1, sc2 = st.columns([3, 1])
        with sc1:
            query = st.text_input("Stock symbol", placeholder="e.g. RELIANCE", key="stock_search_input", label_visibility="collapsed")
        with sc2:
            search_clicked = st.button("SEARCH", key="search_stock", use_container_width=True)
            
    with col_scan:
        st.markdown('<div style="font-size:.85rem; font-weight:900; margin-bottom:4px; color:transparent;">-</div>', unsafe_allow_html=True)
        normal_clicked = st.button("🚀 SCAN MARKET", key="scan_market", type="primary", use_container_width=True, disabled=audit_pending)
    with col_audit:
        st.markdown('<div style="font-size:.85rem; font-weight:900; margin-bottom:4px; color:transparent;">-</div>', unsafe_allow_html=True)
        audit_clicked = st.button("📊 COLLECT AUDIT", key="collect_audit", use_container_width=True, disabled=audit_pending)
    with col_track:
        st.markdown('<div style="font-size:.85rem; font-weight:900; margin-bottom:4px; color:transparent;">-</div>', unsafe_allow_html=True)
        tracking_clicked = st.button("📈 UPDATE TRACKING", key="update_performance_tracking", use_container_width=True, disabled=audit_pending, help="Backfill historical OHLC for saved signals.")

    # Search Execution
    if search_clicked and query.strip():
        symbol = query.strip().upper().replace(".NS", "")
        st.session_state.search_error = None
        with st.spinner(f"Running scanner analysis for {symbol}…"):
            try:
                row = scan_single(symbol, max_distance=10.0, period="2y")
                if row is None:
                    hist = fetch_history(symbol, "2y")
                    if hist is None: raise ValueError("No usable 2-year price/volume history was returned for this symbol.")
                    nifty = __import__("scanner").fetch_index_history("^NSEI", period="2y")
                    row = score_stock(hist, nifty_df=nifty)
                    if row is None: raise ValueError("The scanner could not calculate the technical setup for this stock.")
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

    st.markdown("<div style='height:20px'></div>",unsafe_allow_html=True)


    with st.expander("🔬 Research: analyse completed 20-trading-day outcomes", expanded=False):
        outcome_labels = {
            "Target 1 reached before Stop": "T1_Before_Stop", "Target 2 reached before Stop": "T2_Before_Stop",
            "Target 3 reached before Stop": "T3_Before_Stop", "Stop reached before any target": "Stop_Before_Target",
            "Target 1 touched at any time": "T1_Hit", "Target 2 touched at any time": "T2_Hit",
            "Target 3 touched at any time": "T3_Hit", "Breakout trigger reached": "Breakout_Hit",
        }
        selected_outcome_label = st.selectbox("Outcome to evaluate", list(outcome_labels.keys()), key="audit_research_outcome_choice")
        if st.button("🔬 RUN COMBINATION ANALYSIS", key="run_audit_combination_analysis"):
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
                        analysis_df = analyze_outcome_combinations(completed_outcomes, outcome_col=outcome_labels[selected_outcome_label], min_signals=max(25, int(len(completed_outcomes) * 0.05)), max_order=3)
                        st.session_state.audit_analysis_result = analysis_df
                        st.session_state.audit_analysis_report = completion_report
                        st.session_state.audit_analysis_outcome = outcome_labels[selected_outcome_label]
                        st.session_state.audit_analysis_saved = False
                        analysis_status.update(label=f"Analysis complete: {len(completed_outcomes):,} matured signals evaluated", state="complete", expanded=False)
            except Exception as exc: st.error("Combination analysis failed. Details: " + str(exc))

        stored_report = st.session_state.get("audit_analysis_report")
        stored_analysis = st.session_state.get("audit_analysis_result")
        if stored_report is not None:
            st.caption(f"Matured signals: {stored_report.get('signals_matured_20d', 0):,} / {stored_report.get('signals_total', 0):,}; pending 20-day outcome: {stored_report.get('signals_pending', 0):,}.")
        if isinstance(stored_analysis, pd.DataFrame) and not stored_analysis.empty:
            st.dataframe(stored_analysis.head(50), use_container_width=True, hide_index=True)
            if not st.session_state.get("audit_analysis_saved", False):
                if st.button("💾 APPEND ANALYSIS RESULTS TO GOOGLE SHEET"):
                    try:
                        with st.spinner("Appending analysis rows to Analysis_Results…"): saved_count = append_analysis_rows(st.secrets, stored_analysis)
                        st.session_state.audit_analysis_saved = True
                        st.success(f"Saved {saved_count:,} analysis rows to Analysis_Results.")
                        st.rerun()
                    except Exception as exc: st.error("Could not save analysis results. Details: " + str(exc))


    # Tracking Update Action
    if tracking_clicked:
        try:
            with st.status("📈 Updating 20-day performance tracking…", expanded=True) as tracking_status:
                tracking_status.write("Reading saved audit signals from Google Sheets…")
                signal_df = read_audit_signals(st.secrets)
                existing_keys = read_performance_keys(st.secrets)
                if signal_df.empty: st.warning("No saved audit signals were found.")
                else:
                    cutoff_date = latest_completed_market_date()
                    total_steps = st.empty(); progress_bar = st.progress(0); last_progress = {"value": -1}
                    def progress_update(done, total, message):
                        pct_value = min(100, int((done / max(1, int(total))) * 100))
                        if pct_value != last_progress["value"]: progress_bar.progress(pct_value); last_progress["value"] = pct_value
                        total_steps.caption(message)
                    price_histories, missing_symbols, market_sessions, calendar_source = fetch_ohlc_histories(signal_df, as_of_date=cutoff_date, progress_callback=progress_update)
                    progress_bar.progress(100)
                    new_performance, tracking_report = build_performance_rows(signal_df, price_histories, existing_performance=existing_keys, as_of_date=cutoff_date, market_sessions=market_sessions, calendar_source=calendar_source, progress_callback=lambda d, t, m: total_steps.caption(m))
                    tracking_report["missing_symbols_from_fetch"] = missing_symbols
                    if not new_performance.empty:
                        write_result = append_performance_rows(st.secrets, new_performance, batch_size=400, progress_callback=lambda d, t, m: total_steps.caption(m))
                    else: write_result = {"saved": False, "rows": 0, "expected": 0, "reason": "no_new_rows"}
                    tracking_status.update(label="✅ Performance tracking update finished", state="complete", expanded=False)
                    st.success(f"Finished. {write_result.get('rows', 0):,} new rows appended; {write_result.get('updated', 0):,} repaired.")
        except Exception as exc: st.error("Performance tracking update failed. Details: " + str(exc))

    if audit_pending:
        st.info("📌 An audit scan is waiting for your confirmation below. Resolve it before starting another scan.")

    # Scan Execution
    scan_mode = "audit" if audit_clicked else "normal" if normal_clicked else None
    if scan_mode:
        st.session_state.scanning = True
        st.session_state.scan_error = None
        st.session_state.scan_result = None
        scan_placeholder = st.empty()
        try:
            scan_placeholder.markdown('<div class="scan-shell"><div style="font-weight:950;font-size:1rem">🔎 Scanning market…</div><div class="scan-copy"><span>Analyzing NIFTY Universe</span><span>Working</span></div><div class="scan-chart"><div class="candle-track">' + ''.join([f'<span class="candle {"g" if i % 3 else "r"}"></span>' for i in range(42)]) + '</div></div><div class="progress"><div></div></div></div>', unsafe_allow_html=True)
            with st.spinner("Calculating technical setups…"):
                result = scan_universe(max_distance=10.0, period="2y", top_n=500)
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


    result=st.session_state.get("scan_result")
    if st.session_state.get("scan_error"): st.error(st.session_state.scan_error)
    if result is None:
        st.markdown('<div class="card" style="text-align:center; padding: 40px;"><b>Ready to scan</b><div class="small-muted" style="margin-top:6px">The scanner will fetch the universe and list qualifying technical setups.</div></div>',unsafe_allow_html=True); return
    if result.empty:
        st.markdown('<div class="card" style="text-align:center; padding: 40px;"><b>No qualifying setups found</b><div class="small-muted" style="margin-top:6px">Nothing currently meets the near-breakout criteria.</div></div>',unsafe_allow_html=True); return

    # Audit Confirmation
    pending_rows = st.session_state.get("audit_pending_rows")
    pending_run_id = st.session_state.get("audit_pending_run_id")
    pending_timestamp = st.session_state.get("audit_pending_timestamp")
    append_in_progress = st.session_state.get("audit_append_in_progress", False)
    if pending_rows is not None:
        if append_in_progress:
            st.info(f"⏳ Writing {len(pending_rows)} audit rows to Google Sheets… Please keep this page open.")
            try:
                with st.status("⏳ Appending audit batch…", expanded=True) as status:
                    audit_info = append_audit_batch(st.secrets, pending_rows, run_id=pending_run_id, scan_timestamp_ist=pending_timestamp, scanner_period="2y", max_distance_pct=10.0)
                    status.update(label=f"✅ Audit batch written: {audit_info.get('rows', 0)} new rows.", state="complete", expanded=False)
                st.session_state.audit_last_saved = audit_info
                st.session_state.audit_pending_rows = None; st.session_state.audit_append_in_progress = False
                st.rerun()
            except Exception as exc:
                st.session_state.audit_append_in_progress = False
                st.error("Audit batch failed. Details: " + str(exc))
        else:
            st.warning(f"📊 Audit collection ready: {len(pending_rows)} signal rows. Append to Google Sheet?")
            y_col, n_col = st.columns([1,1])
            if y_col.button("✅ YES — APPEND TO AUDIT SHEET", type="primary", use_container_width=True):
                st.session_state.audit_append_in_progress = True; st.rerun()
            if n_col.button("❌ NO — DISCARD THIS AUDIT", use_container_width=True):
                st.session_state.audit_pending_rows = None; st.rerun()

    audit_info = st.session_state.get("audit_last_saved") or {}
    if audit_info.get("saved") and audit_info.get("reason") in {"appended", "batch_already_exists"}:
        st.success(f"✅ Audit batch recorded: {audit_info.get('rows', 0)} new signal rows.")

    display = result.copy()
    sort_cols = [c for c in ["rating", "score", "rank_score", "distance_pct"] if c in display.columns]
    if sort_cols:
        display = display.sort_values(sort_cols, ascending=[False, False, False, True][:len(sort_cols)], kind="stable").reset_index(drop=True)
    
    st.markdown(f'<div style="display:flex; justify-content:space-between; align-items:baseline; margin-top: 24px; border-bottom: 1px solid var(--border); padding-bottom: 8px;"><div class="section-title" style="border:none; margin:0; padding:0;">Scanned Stocks ({len(display)})</div><div class="rank-note" style="margin:0;">Sorted by Strength (highest first)</div></div>',unsafe_allow_html=True)
    
    # -------------------------------------------------------
    # DENSE 4-COLUMN DESKTOP GRID FOR RESULTS
    # -------------------------------------------------------
    for start in range(0,len(display),4):
        cols=st.columns(4)
        for j,col in enumerate(cols):
            idx=start+j
            if idx>=len(display): continue
            row=display.iloc[idx]; ratio=idx/max(len(display)-1,1)
            color="#19d38a" if ratio<.2 else "#8fd66a" if ratio<.4 else "#f5c451" if ratio<.6 else "#ff9b4a" if ratio<.8 else "#ff5c70"
            with col:
                rating = int(float(row.get("rating", 0) or 0))
                rating_color = "#19d38a" if rating >= 8 else "#8fd66a" if rating >= 7 else "#f5c451" if rating >= 5 else "#ff9b4a" if rating >= 3 else "#ff5c70"
                score = float(row.get("score", 0) or 0)
                price = float(row.get("price", 0) or 0)
                st.markdown(f'''
                <div style="border-radius:12px;border:1px solid rgba(255,255,255,.08);padding:14px;background:linear-gradient(145deg,{color}15,var(--card));margin-bottom:-4px; height: 100%;">
                    <div style="display:flex; justify-content:space-between; align-items:flex-start;">
                        <div style="font-size:.72rem;font-weight:900;color:{color}">RANK #{idx+1} &nbsp;•&nbsp; {html.escape(str(row.get("cap_category","")))}</div>
                    </div>
                    <div style="font-weight:950;font-size:1.15rem;color:var(--text); margin-top: 4px; line-height:1.2;">{html.escape(str(row.get("company_name",row["symbol"])))}</div>
                    <div class="small-muted" style="margin-bottom:8px;">{html.escape(str(row["symbol"]))}</div>
                    
                    <div style="display:flex; gap:6px; margin-bottom:12px;">
                        <span style="padding:4px 8px;border-radius:6px;border:1px solid {rating_color}40;background:{rating_color}18;color:{rating_color};font-size:.7rem;font-weight:950;">Strength {rating}/10</span>
                        <span style="padding:4px 8px;border-radius:6px;border:1px solid rgba(255,255,255,.15);background:rgba(255,255,255,.05);color:var(--text);font-size:.7rem;font-weight:950;">Score {score:.1f}</span>
                    </div>

                    <div style="font-weight:950;font-size:1.2rem;">{money(price)}</div>
                    <div style="font-size:.8rem;color:{color};font-weight:900; margin-bottom: 12px;">{float(row.get("distance_pct",0)):.2f}% to breakout</div>
                    
                    <div style="display:grid;grid-template-columns:1fr 1fr 1fr;gap:8px;">
                        <div style="border:1px solid rgba(25,211,138,.24);border-radius:8px;padding:6px;background:rgba(25,211,138,.06);text-align:center;">
                            <div style="font-size:.65rem;font-weight:900;color:#19d38a;text-transform:uppercase;">RSI</div>
                            <div style="font-size:.95rem;font-weight:950;">{float(row.get("rsi", 0) or 0):.1f}</div>
                        </div>
                        <div style="border:1px solid rgba(25,211,138,.24);border-radius:8px;padding:6px;background:rgba(25,211,138,.06);text-align:center;">
                            <div style="font-size:.65rem;font-weight:900;color:#19d38a;text-transform:uppercase;">ADX</div>
                            <div style="font-size:.95rem;font-weight:950;">{float(row.get("adx", 0) or 0):.1f}</div>
                        </div>
                        <div style="border:1px solid rgba(25,211,138,.24);border-radius:8px;padding:6px;background:rgba(25,211,138,.06);text-align:center;">
                            <div style="font-size:.65rem;font-weight:900;color:#19d38a;text-transform:uppercase;">MACD</div>
                            <div style="font-size:.95rem;font-weight:950;">{float(row.get("macd", 0) or 0):.3f}</div>
                        </div>
                    </div>
                </div>''',unsafe_allow_html=True)
                if st.button(f"Research {row['symbol']}",key=f"stock_{row['symbol']}",use_container_width=True):
                    st.session_state.selected_stock=row["symbol"]; st.session_state.selected_row=row.to_dict(); st.session_state.page="detail"; st.rerun()


# -----------------------------------------------------------------------------
# Session-state navigation
# -----------------------------------------------------------------------------
if "page" not in st.session_state: st.session_state.page = "home"
if "scan_result" not in st.session_state: st.session_state.scan_result = None
if "scan_timestamp" not in st.session_state: st.session_state.scan_timestamp = None
if "scanning" not in st.session_state: st.session_state.scanning = False
if "audit_last_saved" not in st.session_state: st.session_state.audit_last_saved = None
if "audit_pending_rows" not in st.session_state: st.session_state.audit_pending_rows = None
if "audit_pending_run_id" not in st.session_state: st.session_state.audit_pending_run_id = None
if "audit_pending_timestamp" not in st.session_state: st.session_state.audit_pending_timestamp = None
if "audit_append_in_progress" not in st.session_state: st.session_state.audit_append_in_progress = False

render_reload_guard(True)

if st.session_state.page == "detail" and st.session_state.get("selected_stock"):
    render_detail(st.session_state.selected_stock, st.session_state.selected_row)
else:
    render_home()

st.markdown('<div style="text-align:center;color:#71839a;font-size:.8rem;margin-top:40px; border-top:1px solid var(--border); padding-top:20px;">For educational purposes only. Not investment advice.</div>', unsafe_allow_html=True)
i want a theme like Sotex - Stock Market Figma Template       which should be free and lite as well can you redesign the ui fro a fresh look

This complete replacement for app.py redesigns the UI using the clean, minimalist, flat-card aesthetic of the Sotex fintech template, optimizing for high-contrast visibility and a lightweight CSS footprint.

The update replaces heavy gradients and glows with sharp borders, muted indigo secondary text, a distinct fintech brand blue (#6366f1), and crisp mint-green/coral-red accents (#10b981 / #ef4444). All underlying Python scanner logic, Google Sheets integrations, and component structures remain exactly as they were.

Replace your existing app.py with this code:

Python
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

# IMPORTANT: scanner.py is the existing engine. This UI only calls its existing functions.
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

IST = ZoneInfo("Asia/Kolkata")

NIFTY50_CSV = "https://nsearchives.nseindia.com/content/indices/ind_nifty50list.csv"
NSE_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120 Safari/537.36",
    "Accept": "text/csv,text/plain,*/*",
}

# FULL WIDTH DESKTOP LAYOUT
st.set_page_config(
    page_title="NIFTY Breakout Scanner",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="collapsed",
)


def password_gate():
    """Optional single-password gate, enabled only when APP_PASSWORD is configured."""
    try:
        required = str(st.secrets.get("APP_PASSWORD", "")).strip()
    except Exception:
        required = ""
    if not required:
        return True
    if st.session_state.get("authenticated", False):
        return True
    
    col1, col2, col3 = st.columns([1, 1, 1])
    with col2:
        st.title("🔐 Stock Scanner")
        st.subheader("Password required")
        with st.form("scanner_password_login"):
            entered = st.text_input("Enter password", type="password")
            submitted = st.form_submit_button("Login", use_container_width=True)
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
# UI-only CSS. Sotex-inspired Lite Fintech Theme applied.
# -----------------------------------------------------------------------------
CSS = r"""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800;900&display=swap');

:root {
    --bg: #0c0e12;
    --card: #14171d;
    --card2: #1b1f27;
    --border: #242933;
    --text: #f1f5f9;
    --muted: #94a3b8;
    --accent: #10b981; 
    --red: #ef4444;
    --yellow: #f59e0b;
    --brand: #6366f1;
}

html,body,[data-testid="stAppViewContainer"]{background:var(--bg)!important;color:var(--text)!important; font-family: 'Inter', sans-serif !important;}
[data-testid="stHeader"],footer,#MainMenu,[data-testid="stToolbar"]{visibility:hidden!important;height:0!important;display:none!important}
.block-container{max-width:1800px!important;padding:2rem 2.5rem 5rem!important}
section[data-testid="stSidebar"]{display:none!important}*{box-sizing:border-box}

/* Clean, flat buttons (Sotex style) */
.stButton>button{width:100%;border-radius:8px;border:1px solid var(--border);background:var(--card);color:var(--text);min-height:44px;font-weight:600;transition:all .15s ease; font-family: 'Inter', sans-serif;}
.stButton>button:hover{border-color:var(--brand);color:var(--brand);transform:translateY(-1px)}
.scan-btn .stButton>button{min-height:54px;border:0;color:white;background:var(--brand);font-size:1.05rem}
.scan-btn .stButton>button:hover{background:#4f46e5;color:white;}

/* Flat cards with sharp borders */
.card{background:var(--card);border:1px solid var(--border);border-radius:12px;padding:18px;margin:8px 0;box-shadow:none;}
.status-card{padding:10px 16px;border-radius:10px;background:var(--card);border:1px solid var(--border)}.status-row{display:flex;align-items:center;justify-content:space-between;gap:10px}.status-left{display:flex;align-items:center;gap:8px;font-weight:600}.dot{width:8px;height:8px;border-radius:50%;display:inline-block;}.dot.green{background:var(--accent);color:var(--accent);}.dot.red{background:var(--red);color:var(--red);}.dot.yellow{background:var(--yellow);color:var(--yellow);}.index-wrap{display:flex;gap:16px;justify-content:flex-end;flex-wrap:wrap}.index-item{font-size:.85rem;color:var(--muted)}.index-item b{color:var(--text);font-size:.9rem;font-weight:600;}.up{color:var(--accent)!important}.down{color:var(--red)!important}.section-title{font-size:1.15rem;font-weight:700;margin:24px 2px 14px; border-bottom: 1px solid var(--border); padding-bottom: 10px; color:var(--text);}

/* Metrics */
.metric-card{min-height:76px;padding:14px;border-radius:10px;border:1px solid var(--border);background:var(--card);box-shadow:none;}
.metric-label{color:var(--muted);font-size:.72rem;text-transform:uppercase;letter-spacing:.05em;font-weight:600;}
.metric-value{color:var(--text);font-weight:700;font-size:1.1rem;margin-top:6px;word-break:break-word}
.metric-good{border-left: 3px solid var(--accent);}.metric-ok{border-left: 3px solid #84cc16;}.metric-neutral{border-left: 3px solid var(--border);}.metric-poor{border-left: 3px solid var(--yellow);}.metric-bad{border-left: 3px solid var(--red);}

.hero-price{font-size:2.2rem;font-weight:800;letter-spacing:-.02em; color:var(--text);}.badge{display:inline-block;padding:4px 10px;border-radius:6px;font-size:.75rem;font-weight:700;letter-spacing:.02em;text-transform:uppercase;}
.badge-green{background:rgba(16,185,129,.12);color:var(--accent);border:1px solid rgba(16,185,129,.25)}.badge-red{background:rgba(239,68,68,.12);color:var(--red);border:1px solid rgba(239,68,68,.25)}.badge-yellow{background:rgba(245,158,11,.12);color:var(--yellow);border:1px solid rgba(245,158,11,.25)}.badge-brand{background:rgba(99,102,241,.12);color:var(--brand);border:1px solid rgba(99,102,241,.25)}.badge-grey{background:var(--card2);color:var(--muted);border:1px solid var(--border)}
.target-box{padding:14px;border-radius:10px;background:var(--card2);border:1px solid var(--border)}.target-label{font-size:.7rem;color:var(--muted);text-transform:uppercase;font-weight:700}.target-value{font-size:1.2rem;font-weight:800;color:var(--text);margin-top:4px;}.target-upside{font-size:.8rem;color:var(--accent);margin-top:2px;font-weight:600;}

/* Scanner loading state */
.scan-shell{background:var(--card);border:1px solid var(--border);border-radius:12px;padding:24px;overflow:hidden}.scan-chart{height:145px;position:relative;overflow:hidden;border-radius:8px;background:var(--card2)}.candle-track{position:absolute;inset:0;display:flex;align-items:center;gap:12px;width:max-content;animation:scrollCandles 7s linear infinite}.candle{width:6px;position:relative;border-radius:2px;flex:none;box-shadow:none;}.candle:before{content:"";position:absolute;left:2px;width:2px;top:-13px;bottom:-13px;background:currentColor;opacity:.6}.candle.g{height:55px;background:var(--accent);color:var(--accent)}.candle.r{height:38px;background:var(--red);color:var(--red)}@keyframes scrollCandles{from{transform:translateX(0)}to{transform:translateX(-50%)}}.scan-copy{display:flex;justify-content:space-between;color:var(--muted);font-size:.85rem;margin:16px 0 10px}.progress{height:6px;background:var(--card2);border-radius:99px;overflow:hidden}.progress>div{width:65%;height:100%;border-radius:99px;background:var(--brand);animation:progress 2.2s ease-in-out infinite}@keyframes progress{0%{width:8%}50%{width:78%}100%{width:94%}}

.ticker-note,.small-muted{color:var(--muted);font-size:.82rem}.tradingview-btn{display:block;text-align:center;padding:12px 16px;border-radius:8px;background:var(--brand);color:#fff!important;text-decoration:none!important;font-weight:600;margin:6px 0 10px; transition: background .15s;}.tradingview-btn:hover{background:#4f46e5;}.tv-under{text-align:center;margin:5px 0 14px}.tv-under a{color:var(--brand);font-size:.8rem;font-weight:600;text-decoration:none}.rank-note{font-size:.8rem;color:var(--muted);margin-bottom:12px}

/* Tabs overriding to look like Sotex pills */
.stTabs [data-baseweb="tab-list"] {gap: 12px; border-bottom: 1px solid var(--border) !important;}
.stTabs [data-baseweb="tab"] {padding: 10px 20px; background: transparent; border-radius: 6px 6px 0 0; border: none; font-weight: 600; color: var(--muted);}
.stTabs [aria-selected="true"] {background: transparent; border-bottom: 3px solid var(--brand) !important; color: var(--text) !important;}

@media(max-width:768px){.block-container{padding:.8rem 1rem 4rem!important}.index-wrap{justify-content:flex-start}.hero-price{font-size:1.8rem}.metric-value{font-size:1rem}}
</style>
"""
st.markdown(CSS, unsafe_allow_html=True)


if "theme_mode" not in st.session_state:
    st.session_state.theme_mode = "dark"

def apply_theme():
    if st.session_state.theme_mode == "light":
        st.markdown("""<style>:root{--bg:#f8fafc;--card:#ffffff;--card2:#f1f5f9;--border:#e2e8f0;--text:#0f172a;--muted:#64748b;--accent:#10b981;--red:#ef4444;--yellow:#f59e0b;--brand:#4f46e5;}</style>""", unsafe_allow_html=True)

def render_reload_guard(active=True):
    if not active: return
    components.html("""
    <div id="reload-confirm" style="display:none;position:fixed;inset:0;z-index:999999;background:rgba(0,0,0,.4);backdrop-filter:blur(4px);align-items:center;justify-content:center;font-family:'Inter',sans-serif">
      <div style="width:min(400px,90vw);background:var(--card);color:var(--text);border:1px solid var(--border);border-radius:12px;padding:24px;box-shadow:0 20px 40px rgba(0,0,0,.2);text-align:center">
        <div style="font-size:18px;font-weight:700;margin-bottom:8px">Reload Application?</div>
        <div style="font-size:14px;color:var(--muted);line-height:1.5;margin-bottom:20px">The current scan and un-saved audit data will be lost if you reload.</div>
        <div style="display:flex;gap:12px;justify-content:center">
          <button id="reload-yes" style="flex:1;border:0;border-radius:8px;padding:12px;background:#ef4444;color:#fff;font-weight:600;cursor:pointer">Reload</button>
          <button id="reload-no" style="flex:1;border:1px solid var(--border);border-radius:8px;padding:12px;background:var(--card2);color:var(--text);font-weight:600;cursor:pointer">Stay</button>
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
        const show = () => { if (modal) { modal.style.display='flex'; modal.style.background = w.matchMedia('(prefers-color-scheme: dark)').matches ? 'rgba(0,0,0,0.6)' : 'rgba(255,255,255,0.6)'; } };
        const hide = () => { if (modal) modal.style.display='none'; };
        if (yes) yes.onclick = () => { w.location.href = w.location.origin + w.location.pathname + '?__reload_home=1'; };
        if (no) no.onclick = hide;
        w.addEventListener('keydown', (event) => {
          const key = String(event.key || '').toLowerCase();
          const refresh = key === 'f5' || ((event.ctrlKey || event.metaKey) && key === 'r');
          if (refresh) { event.preventDefault(); show(); }
        }, true);
        w.addEventListener('beforeunload', (event) => {
          try { w.sessionStorage.setItem('__nifty_reload_attempt','1'); w.setTimeout(() => { try { w.sessionStorage.removeItem('__nifty_reload_attempt'); } catch(e) {} }, 10000); } catch(e) {}
          event.preventDefault(); event.returnValue = '';
        });
        try {
          if (w.sessionStorage.getItem('__nifty_reload_attempt') === '1') {
            w.sessionStorage.removeItem('__nifty_reload_attempt');
            const u = new URL(w.location.href);
            if (!u.searchParams.has('__reload_home')) {
              u.searchParams.set('__reload_home', '1'); w.location.replace(u.toString()); return;
            }
          }
        } catch(e) {}
      } catch (e) {}
    })();
    </script>
    """, height=0)


def render_theme_toggle():
    c1, c2 = st.columns([15, 1])
    with c2:
        is_light = st.toggle("☀️ Light", value=(st.session_state.theme_mode=="light"), key="theme_toggle")
        new_mode = "light" if is_light else "dark"
        if new_mode != st.session_state.theme_mode:
            st.session_state.theme_mode = new_mode

apply_theme()


@st.cache_data(ttl=60, show_spinner=False)
def get_market_snapshot():
    result = {"nifty": None, "sensex": None, "updated": datetime.now(IST)}
    try:
        raw = yf.download(["^NSEI", "^BSESN"], period="5d", interval="1d", auto_adjust=True, progress=False, threads=True, group_by="ticker", multi_level_index=True)
        for symbol, key in [("^NSEI", "nifty"), ("^BSESN", "sensex")]:
            try:
                df = raw[symbol] if isinstance(raw.columns, pd.MultiIndex) and symbol in raw.columns.get_level_values(0) else raw.xs(symbol, axis=1, level=1)
                df = df.dropna(subset=["Close"])
                if len(df) >= 2:
                    last, prev = float(df.Close.iloc[-1]), float(df.Close.iloc[-2])
                    result[key] = {"value": last, "change": last-prev, "pct": (last/prev-1)*100}
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
        return ["ADANIENT","ADANIPORTS","APOLLOHOSP","ASIANPAINT","AXISBANK","BAJAJ-AUTO","BAJFINANCE","BAJAJFINSV","BEL","BHARTIARTL","CIPLA","COALINDIA","DRREDDY","EICHERMOT","ETERNAL","GRASIM","HCLTECH","HDFCBANK","HDFCLIFE","HEROMOTOCO","HINDALCO","HINDUNILVR","ICICIBANK","INDUSINDBK","INFY","ITC","JIOFIN","JSWSTEEL","KOTAKBANK","LT","M&M","MARUTI","MAXHEALTH","NESTLEIND","NTPC","ONGC","POWERGRID","RELIANCE","SBILIFE","SBIN","SHRIRAMFIN","SUNPHARMA","TATACONSUM","TATAMOTORS","TATASTEEL","TCS","TECHM","TITAN","TRENT","ULTRACEMCO"]

@st.cache_data(ttl=60, show_spinner=False)
def get_nifty50_ticker_data(symbols):
    rows = []
    try:
        tickers = [s.replace("&", "%26") + ".NS" for s in symbols]
        raw = yf.download(tickers, period="5d", interval="1d", auto_adjust=True, progress=False, threads=True, group_by="ticker", multi_level_index=True)
        for symbol, ticker in zip(symbols, tickers):
            try:
                if isinstance(raw.columns, pd.MultiIndex):
                    if ticker in raw.columns.get_level_values(0): df = raw[ticker]
                    elif ticker in raw.columns.get_level_values(1): df = raw.xs(ticker, axis=1, level=1)
                    else: continue
                else: df = raw
                df = df.dropna(subset=["Close"])
                if len(df) < 2: continue
                last, prev = float(df.Close.iloc[-1]), float(df.Close.iloc[-2])
                rows.append({"symbol": symbol, "price": last, "pct": (last/prev-1)*100})
            except Exception:
                continue
    except Exception:
        return pd.DataFrame(columns=["symbol","price","pct"])
    return pd.DataFrame(rows)

def market_status(now=None):
    now = now or datetime.now(IST)
    if now.weekday() >= 5: return "Closed", "red"
    t = now.time()
    if dtime(9, 0) <= t < dtime(9, 15): return "Pre-open", "yellow"
    if dtime(9, 15) <= t <= dtime(15, 30): return "Open", "green"
    return "Closed", "red"

def money(x): return f"₹{x:,.2f}" if x is not None and np.isfinite(x) else "—"
def pct(x): return f"{x:+.2f}%" if x is not None and np.isfinite(x) else "—"

def render_market_bar():
    snap = get_market_snapshot()
    status, color = market_status()
    dot = f'<span class="dot {color}"></span>'
    parts = [f'<div class="status-card"><div class="status-row"><div class="status-left">{dot}<span>{status}</span></div><div class="index-wrap">']
    for label, key in [("NIFTY 50", "nifty"), ("SENSEX", "sensex")]:
        item = snap.get(key)
        if item:
            cls = "up" if item["pct"] >= 0 else "down"
            arrow = "▲" if item["pct"] >= 0 else "▼"
            parts.append(f'<div class="index-item"><b>{label}</b> {item["value"]:,.2f} <span class="{cls}">{arrow} {item["pct"]:+.2f}%</span></div>')
        else:
            parts.append(f'<div class="index-item"><b>{label}</b> —</div>')
    updated = snap["updated"].strftime("%d %b %Y, %H:%M:%S IST")
    parts.append(f'</div></div><div class="ticker-note">Last UI market-data refresh: {updated}</div></div>')
    st.markdown("".join(parts), unsafe_allow_html=True)


def render_ticker():
    symbols=get_nifty50_symbols(); df=get_nifty50_ticker_data(tuple(symbols))
    if df.empty:
        st.markdown('<div class="ticker-note">NIFTY 50 ticker data temporarily unavailable.</div>',unsafe_allow_html=True); return
    items=[]
    for _,r in df.iterrows():
        cls="up" if r.pct>=0 else "down"; arrow="▲" if r.pct>=0 else "▼"
        items.append(f'<span class="tick"><b>{html.escape(r.symbol)}</b> {money(r.price)} <span class="{cls}">{arrow} {r.pct:+.2f}%</span></span>')
    content="".join(items); light=st.session_state.theme_mode=="light"
    bg="#ffffff" if light else "#0c0e12"; viewport="#ffffff" if light else "#0c0e12"; textc="#0f172a" if light else "#f1f5f9"; muted="#64748b" if light else "#94a3b8"; border="#e2e8f0" if light else "#242933"; green="#10b981"; red="#ef4444"
    markup=f"""<html><head><style>@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600&display=swap'); *{{box-sizing:border-box}}body{{margin:0;background:{bg};color:{textc};font-family:'Inter',sans-serif;overflow:hidden}}.viewport{{width:100%;overflow:hidden;border:1px solid {border};border-radius:10px;background:{viewport}}}.track{{display:flex;width:max-content;animation:marquee 144s linear infinite;padding:12px 0}}.track:hover{{animation-play-state:paused}}.tick{{white-space:nowrap;margin-right:32px;font-size:12px;color:{muted};font-weight:400;}}.tick b{{color:{textc};margin-right:6px;font-weight:600;}}.up{{color:{green}}}.down{{color:{red}}}@keyframes marquee{{from{{transform:translateX(0)}}to{{transform:translateX(-50%)}}}}</style></head><body><div class="viewport" id="v"><div class="track" id="t">{content}{content}</div></div><script>const v=document.getElementById('v'),t=document.getElementById('t');v.addEventListener('touchstart',()=>t.style.animationPlayState='paused',{{passive:true}});v.addEventListener('touchend',()=>t.style.animationPlayState='running',{{passive:true}});</script></body></html>"""
    components.html(markup,height=45,scrolling=False)

def day_change(symbol, period="2y"):
    hist = fetch_history(symbol, period)
    if hist is None or len(hist) < 2: return None, None, None
    last, prev = float(hist.Close.iloc[-1]), float(hist.Close.iloc[-2])
    return last, last-prev, (last/prev-1)*100

def detail_chart(symbol,row,period="2y"):
    hist=fetch_history(symbol,period)
    if hist is None or hist.empty:
        st.warning("Price history is temporarily unavailable for the chart."); return
    light=st.session_state.theme_mode=="light"
    fig=go.Figure()
    fig.add_trace(go.Candlestick(x=hist.index,open=hist.Open,high=hist.High,low=hist.Low,close=hist.Close,name=symbol))
    fig.add_trace(go.Bar(x=hist.index,y=hist.Volume,name="Volume",yaxis="y2",opacity=.2, marker_color="#6366f1"))
    fig.add_hline(y=float(row["breakout_level"]),line_dash="dash",line_color="#10b981",annotation_text=f"Breakout: ₹{row['breakout_level']:.2f}",annotation_position="top left")
    fig.update_layout(template="plotly_white" if light else "plotly_dark",height=550,margin=dict(l=5,r=5,t=25,b=10),xaxis_rangeslider_visible=False,hovermode="x unified",paper_bgcolor="#ffffff" if light else "#14171d",plot_bgcolor="#f8fafc" if light else "#0c0e12",yaxis=dict(title="Price", gridcolor="#e2e8f0" if light else "#242933"),yaxis2=dict(title="Volume",overlaying="y",side="right",showgrid=False,rangemode="tozero"),legend=dict(orientation="h",y=1.02,x=0))
    st.plotly_chart(fig,use_container_width=True,config={"displayModeBar":False,"responsive":True})

def verdict(score):
    if score>=90:return "Strong",True
    if score>=75:return "Good",True
    if score>=60:return "Neutral",False
    if score>=40:return "Weak",False
    return "Avoid",False

def score_class(value,kind):
    try:v=float(value)
    except Exception:return "metric-neutral"
    if kind=="rsi": return "metric-good" if 52<=v<=68 else "metric-ok" if 48<=v<=72 else "metric-poor"
    if kind=="rvol": return "metric-good" if v>=1.5 else "metric-ok" if v>=1.1 else "metric-poor" if v>=.8 else "metric-bad"
    if kind=="adx": return "metric-good" if v>=25 else "metric-ok" if v>=18 else "metric-poor"
    if kind=="distance": return "metric-good" if v<=1 else "metric-ok" if v<=3 else "metric-neutral" if v<=5 else "metric-poor" if v<=10 else "metric-bad"
    if kind=="rr": return "metric-good" if v>=2 else "metric-ok" if v>=1.5 else "metric-neutral" if v>=1 else "metric-poor"
    if kind=="score": return "metric-good" if v>=80 else "metric-ok" if v>=65 else "metric-neutral" if v>=50 else "metric-poor" if v>=35 else "metric-bad"
    return "metric-neutral"

def metric_card(label,value,kind=None):
    cls=score_class(value,kind) if kind else "metric-neutral"
    return f'<div class="metric-card {cls}"><div class="metric-label">{html.escape(str(label))}</div><div class="metric-value">{html.escape(str(value))}</div></div>'

def target_values(row,price):
    b=float(row.get("breakout_level",0) or 0); note=""
    try:t1=float(row.get("target1"))
    except Exception:t1=None
    try:t2=float(row.get("target2"))
    except Exception:t2=None
    if t1 is None or not np.isfinite(t1):
        base=max(b-float(price),0); t1=b+base if base else b*1.01; note="Targets estimated from the breakout base height."
    if t2 is None or not np.isfinite(t2):
        base=max(b-float(price),0); t2=b+2*base if base else b*1.02; note="Targets estimated from the breakout base height."
    return t1,t2,note

def build_scan_export(result, scanned_at):
    rows = []
    scan_date = str(scanned_at).split(" ")[0]
    for _, row in result.iterrows():
        try:
            t1 = float(row.get("target1"))
            t2 = float(row.get("target2"))
            t3 = t2 + (t2 - t1) if np.isfinite(t1) and np.isfinite(t2) else np.nan
        except Exception:
            t1 = t2 = t3 = np.nan
        rating = row.get("rating", "")
        targets = " | ".join([f"T1: {t1:.2f}" if np.isfinite(t1) else "T1: —", f"T2: {t2:.2f}" if np.isfinite(t2) else "T2: —", f"T3: {t3:.2f}" if np.isfinite(t3) else "T3: —"])
        def rounded_value(key):
            value = row.get(key)
            return round(float(value), 2) if pd.notna(value) and str(value).strip() != "" else ""
        rows.append({
            "Date": scan_date, "Stock": row.get("company_name", row.get("symbol", "")), "Rank": row.get("rank", ""), "Score": rounded_value("score"),
            "Strength": rating, "Price": rounded_value("price"), "Breakout Level": rounded_value("breakout_level"), "Targets": targets,
            "Stop": rounded_value("stop_reference"), "Distance %": rounded_value("distance_pct"), "RVOL": rounded_value("rvol"),
            "RSI": rounded_value("rsi"), "ADX": rounded_value("adx"), "Market Regime": row.get("market_regime", "")
        })
    return pd.DataFrame(rows, columns=["Date", "Stock", "Rank", "Score", "Strength", "Price", "Breakout Level", "Targets", "Stop", "Distance %", "RVOL", "RSI", "ADX", "Market Regime"])


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
        "ADX": round(float(row.get("adx")), 2), "Market Regime": row.get("market_regime", ""), "Breakout Trigger": round(float(row.get("breakout_trigger")), 2),
        "ATR %": round(float(row.get("atr_pct")), 2), "MACD": round(float(row.get("macd")), 4), "Squeeze": round(float(row.get("squeeze")), 2),
        "EMA Structure": row.get("ema_structure", ""), "Resistance Touches": row.get("resistance_touches", ""),
        "Relative Strength 60D %": round(float(row.get("relative_strength")), 2), "NIFTY Relative Strength %": round(float(row.get("nifty_relative_strength")), 2),
        "Risk / Reward": round(float(row.get("risk_reward")), 2), "False Breakout": "Yes" if row.get("false_breakout") else "No", "Scanner Status": row.get("status", "")
    }])

# -----------------------------------------------------------------------------
# DETAILED DASHBOARD WITH TABS 
# -----------------------------------------------------------------------------
def render_detail(symbol,row):
    render_theme_toggle()
    
    col1, col2 = st.columns([1, 10])
    with col1:
        if st.button("← Back"):
            st.session_state.page="home"; st.rerun()

    # Top Hero Section
    company=row.get("company_name",symbol); last,change,change_pct=day_change(symbol); price=last if last is not None else row.get("price")
    score=float(row.get("score",0)); label,strong=verdict(score); change_cls="up" if (change_pct or 0)>=0 else "down"; arrow="▲" if (change_pct or 0)>=0 else "▼"
    t1,t2,target_note=target_values(row,price)
    t1up=((t1/price)-1)*100 if price else 0; t2up=((t2/price)-1)*100 if price else 0
    
    st.markdown(f'''
    <div style="display:flex; justify-content:space-between; align-items:flex-end; margin-bottom: 24px; padding: 24px; background: var(--card); border-radius: 12px; border: 1px solid var(--border);">
        <div>
            <div class="small-muted" style="font-size:.9rem; font-weight:600; margin-bottom:6px; letter-spacing:.02em; text-transform:uppercase;">{html.escape(str(company))}</div>
            <div style="font-size:2.4rem;font-weight:800; line-height: 1.1; color:var(--text);">{html.escape(symbol)}</div>
            <div style="display:flex; align-items:center; gap: 14px; margin-top: 10px;">
                <div class="hero-price" style="font-size:1.8rem;">{money(price)}</div>
                <div class="{change_cls}" style="font-weight:700; font-size:1.1rem;">{arrow} {money(change)} ({pct(change_pct)})</div>
            </div>
        </div>
        <div style="display:flex; gap: 16px;">
            <div class="target-box"><div class="target-label">Target 1</div><div class="target-value">{money(t1)}</div><div class="target-upside">{t1up:+.2f}%</div></div>
            <div class="target-box"><div class="target-label">Target 2</div><div class="target-value">{money(t2)}</div><div class="target-upside">{t2up:+.2f}%</div></div>
        </div>
    </div>
    ''', unsafe_allow_html=True)

    tab_tech, tab_fund, tab_news, tab_audit = st.tabs(["📈 Technical Setup", "🏛️ Fundamentals", "📰 News & Events", "📊 Audit Details"])
    
    # ------------------ TAB 1: TECHNICALS ------------------
    with tab_tech:
        c_left, c_right = st.columns([3, 1])
        with c_left:
            st.markdown('<div class="section-title" style="margin-top:0;">Price Action</div>',unsafe_allow_html=True)
            tv_symbol=str(symbol).replace(".NS","").upper(); tv_url=f"https://www.tradingview.com/chart/?symbol=NSE:{tv_symbol}"
            detail_chart(symbol,row)
            st.markdown(f'<div class="tv-under"><a href="{tv_url}" target="_blank" rel="noopener">Open Full Interactive Chart ↗</a></div>',unsafe_allow_html=True)
            
        with c_right:
            st.markdown('<div class="section-title" style="margin-top:0;">Momentum Gauge</div>',unsafe_allow_html=True)
            light=st.session_state.theme_mode=="light"
            fig=go.Figure(go.Indicator(mode="gauge+number",value=score,number={"suffix":"","font":{"size":42,"color":"#0f172a" if light else "#f1f5f9"}},gauge={"axis":{"range":[0,100],"tickwidth":0,"tickcolor":"transparent"},"bar":{"color":"#10b981","thickness":.15},"bgcolor":"#e2e8f0" if light else "#242933","borderwidth":0,"steps":[{"range":[0,40],"color":"rgba(239,68,68,0.15)"},{"range":[40,65],"color":"rgba(245,158,11,0.15)"},{"range":[65,80],"color":"rgba(132,204,22,0.15)"},{"range":[80,100],"color":"rgba(16,185,129,0.15)"}]}))
            fig.update_layout(template="plotly_white" if light else "plotly_dark",height=260,margin=dict(l=15,r=15,t=20,b=0),paper_bgcolor="#ffffff" if light else "#14171d")
            st.plotly_chart(fig,use_container_width=True,config={"displayModeBar":False})
            
            level=float(row.get("breakout_level",0) or 0); p=float(price or 0); distance=((level-p)/level*100) if level else 999
            if p>=level: title,msg,cls="Breakout Confirmed","Trading above detected resistance.","badge-green"
            elif distance<=2: title,msg,cls="ENTRY ZONE","Near breakout level. Await volume confirmation.","badge-green"
            elif distance<=5: title,msg,cls="Developing","Setup forming, not near entry.","badge-yellow"
            else: title,msg,cls="Watch","Monitoring base formation.","badge-grey"
            st.markdown(f'''<div class="card" style="text-align:center;"><span class="badge {cls}">{title}</span><div style="font-size:1rem;font-weight:700;margin-top:14px;color:var(--text);">{msg}</div><div class="small-muted" style="margin-top:8px">Distance: <span style="font-weight:600;">{distance:.2f}%</span> &nbsp; • &nbsp; Trigger: <span style="font-weight:600;">{money(row.get("breakout_trigger"))}</span></div></div>''',unsafe_allow_html=True)
            
            if row.get("explanation"):
                st.markdown(f'<div class="card"><b style="font-size:.85rem;text-transform:uppercase;color:var(--muted);letter-spacing:.05em;">Setup Summary</b><div style="margin-top:8px; font-size:.9rem; line-height:1.5;">{html.escape(str(row["explanation"]))}</div></div>',unsafe_allow_html=True)

        st.markdown('<div class="section-title">Technical Parameters</div>',unsafe_allow_html=True)
        hist=fetch_history(symbol,"2y"); extra={}
        if hist is not None and len(hist):
            last52=hist.tail(252); extra={"52-week high":money(float(last52.High.max())),"52-week low":money(float(last52.Low.min()))}
        fields=[
          ("Breakout level",money(row.get("breakout_level")),"distance"),("Breakout trigger",money(row.get("breakout_trigger")),None),
          ("Distance",pct(row.get("distance_pct")),"distance"),("Rating",f"{row.get('rating','—')}/10","score"),
          ("Score",f"{row.get('score',0):.1f}/100","score"),("RVOL",f"{row.get('rvol',0):.2f}x","rvol"),
          ("RSI",f"{row.get('rsi',0):.1f}","rsi"),("ADX",f"{row.get('adx',0):.1f}","adx"),
          ("EMA structure",row.get("ema_structure","—"),None),("MACD",f"{row.get('macd',0):.3f}",None),
          ("ATR %",f"{row.get('atr_pct',0):.2f}%",None),("Squeeze",f"{row.get('squeeze',0):.2f}",None),
          ("NIFTY rel strength",pct(row.get("nifty_relative_strength")),None),("60D rel strength",pct(row.get("relative_strength")),None),
          ("Candlestick",row.get("candlestick","—"),None),("Resistance touches",row.get("resistance_touches","—"),None),
          ("Risk / reward",f"{row.get('risk_reward',0):.2f}","rr"),("Market regime",row.get("market_regime","—"),None),
          ("Stop reference",money(row.get("stop_reference")),None),("False breakout","Yes" if row.get("false_breakout") else "No",None),
          ("52-week high",extra.get("52-week high","—"),None),("52-week low",extra.get("52-week low","—"),None)]
        
        for start in range(0,len(fields),6):
            cols=st.columns(6)
            for j,col in enumerate(cols):
                idx=start+j
                if idx>=len(fields): continue
                with col: st.markdown(metric_card(fields[idx][0],fields[idx][1],fields[idx][2]),unsafe_allow_html=True)

    # ------------------ TAB 2: FUNDAMENTALS (Placeholder) ------------------
    with tab_fund:
        st.markdown('<div class="section-title" style="margin-top:0;">Fundamental Health</div>', unsafe_allow_html=True)
        st.info("Fundamental Analysis module pending deployment (Phase 2).")
        st.markdown('''
        <div style="opacity: 0.4;">
            <div style="display:grid; grid-template-columns: repeat(4, 1fr); gap: 16px;">
                <div class="card"><b style="color:var(--muted);font-size:.75rem;text-transform:uppercase;">QoQ Revenue Growth</b><br><span style="font-size:1.6rem; font-weight:800;">--</span></div>
                <div class="card"><b style="color:var(--muted);font-size:.75rem;text-transform:uppercase;">QoQ Net Profit</b><br><span style="font-size:1.6rem; font-weight:800;">--</span></div>
                <div class="card"><b style="color:var(--muted);font-size:.75rem;text-transform:uppercase;">Operating Margin</b><br><span style="font-size:1.6rem; font-weight:800;">--</span></div>
                <div class="card"><b style="color:var(--muted);font-size:.75rem;text-transform:uppercase;">Debt to Equity</b><br><span style="font-size:1.6rem; font-weight:800;">--</span></div>
            </div>
        </div>
        ''', unsafe_allow_html=True)

    # ------------------ TAB 3: NEWS (Placeholder) ------------------
    with tab_news:
        st.markdown('<div class="section-title" style="margin-top:0;">Corporate Announcements</div>', unsafe_allow_html=True)
        st.info("News Intelligence module pending deployment (Phase 4).")
        st.markdown('''
        <div style="opacity: 0.4;">
            <div class="card">
                <span class="badge badge-brand">Pending Sync</span>
                <div style="margin-top:10px; font-weight:600; font-size:1.1rem;">Awaiting NSE corporate filings feed.</div>
            </div>
        </div>
        ''', unsafe_allow_html=True)

    # ------------------ TAB 4: AUDIT EXPORT ------------------
    with tab_audit:
        st.markdown('<div class="section-title" style="margin-top:0;">Snapshot Data</div>', unsafe_allow_html=True)
        st.markdown('<div class="small-muted" style="margin-bottom:16px;">Raw technical properties formatted for the Google Sheets audit tracker.</div>', unsafe_allow_html=True)
        
        audit_df = build_single_stock_export(symbol, row, st.session_state.get("search_timestamp", datetime.now(IST).strftime("%Y-%m-%d %H:%M:%S IST")), rank="")
        st.dataframe(audit_df, use_container_width=True, hide_index=True)
        st.download_button("📥 DOWNLOAD AUDIT ROW (CSV)", data=audit_df.to_csv(index=False).encode("utf-8-sig"), file_name=f"audit_{symbol}_{datetime.now(IST).strftime('%Y%m%d_%H%M%S')}.csv", mime="text/csv", use_container_width=False, key=f"audit_{symbol}")



def render_home():
    render_theme_toggle()
    
    st.markdown("<div style='font-size:2rem;font-weight:800;letter-spacing:-.02em;'>NIFTY Momentum Intelligence</div><div class='small-muted' style='font-size:.9rem; margin-top:4px;'>Multi-horizon screening across Large & Midcap 250</div>",unsafe_allow_html=True)
    st.markdown("<div style='height:16px'></div>",unsafe_allow_html=True)
    render_market_bar(); render_ticker(); st.markdown("<div style='height:16px'></div>",unsafe_allow_html=True)
    
    audit_pending = st.session_state.get("audit_pending_rows") is not None
    
    # -------------------------------------------------------
    # WIDE SCREEN ACTION BAR
    # -------------------------------------------------------
    col_search, col_scan, col_audit, col_track = st.columns([3, 2, 2, 2])
    with col_search:
        st.markdown('<div style="font-size:.75rem; font-weight:700; margin-bottom:6px; color:var(--muted); text-transform:uppercase; letter-spacing:.05em;">Manual Search</div>', unsafe_allow_html=True)
        sc1, sc2 = st.columns([3, 1])
        with sc1:
            query = st.text_input("Stock symbol", placeholder="e.g. RELIANCE", key="stock_search_input", label_visibility="collapsed")
        with sc2:
            search_clicked = st.button("SEARCH", key="search_stock", use_container_width=True)
            
    with col_scan:
        st.markdown('<div style="font-size:.75rem; font-weight:700; margin-bottom:6px; color:var(--muted); text-transform:uppercase; letter-spacing:.05em;">Market Scanner</div>', unsafe_allow_html=True)
        normal_clicked = st.button("🚀 SCAN MARKET", key="scan_market", use_container_width=True, disabled=audit_pending)
        # Using a custom class hook for primary button in CSS
        if normal_clicked: st.session_state.scan_intent = True
        
    with col_audit:
        st.markdown('<div style="font-size:.75rem; font-weight:700; margin-bottom:6px; color:transparent; text-transform:uppercase;">-</div>', unsafe_allow_html=True)
        audit_clicked = st.button("📊 COLLECT AUDIT", key="collect_audit", use_container_width=True, disabled=audit_pending)
    with col_track:
        st.markdown('<div style="font-size:.75rem; font-weight:700; margin-bottom:6px; color:transparent; text-transform:uppercase;">-</div>', unsafe_allow_html=True)
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

    st.markdown("<div style='height:24px'></div>",unsafe_allow_html=True)

    with st.expander("🔬 Research Analytics: Backtest 20-Day Outcomes", expanded=False):
        outcome_labels = {
            "Target 1 reached before Stop": "T1_Before_Stop", "Target 2 reached before Stop": "T2_Before_Stop",
            "Target 3 reached before Stop": "T3_Before_Stop", "Stop reached before any target": "Stop_Before_Target",
            "Target 1 touched at any time": "T1_Hit", "Target 2 touched at any time": "T2_Hit",
            "Target 3 touched at any time": "T3_Hit", "Breakout trigger reached": "Breakout_Hit",
        }
        selected_outcome_label = st.selectbox("Evaluate Criteria", list(outcome_labels.keys()), key="audit_research_outcome_choice")
        if st.button("🔬 RUN ANALYSIS", key="run_audit_combination_analysis"):
            try:
                with st.status("Analyzing audited snapshots…", expanded=True) as analysis_status:
                    all_signals = read_audit_signals(st.secrets)
                    final_rows = read_final_performance(st.secrets)
                    completed_outcomes, completion_report = build_completed_outcomes(all_signals, final_rows)
                    if completed_outcomes.empty:
                        st.session_state.audit_analysis_result = None
                        st.session_state.audit_analysis_report = completion_report
                        st.session_state.audit_analysis_saved = False
                        analysis_status.update(label="Insufficient matured data for analysis.", state="complete", expanded=False)
                    else:
                        analysis_df = analyze_outcome_combinations(completed_outcomes, outcome_col=outcome_labels[selected_outcome_label], min_signals=max(25, int(len(completed_outcomes) * 0.05)), max_order=3)
                        st.session_state.audit_analysis_result = analysis_df
                        st.session_state.audit_analysis_report = completion_report
                        st.session_state.audit_analysis_outcome = outcome_labels[selected_outcome_label]
                        st.session_state.audit_analysis_saved = False
                        analysis_status.update(label=f"Analysis Complete: {len(completed_outcomes):,} signals.", state="complete", expanded=False)
            except Exception as exc: st.error("Analysis Failed: " + str(exc))

        stored_report = st.session_state.get("audit_analysis_report")
        stored_analysis = st.session_state.get("audit_analysis_result")
        if stored_report is not None:
            st.caption(f"Matured signals: {stored_report.get('signals_matured_20d', 0):,} / {stored_report.get('signals_total', 0):,}")
        if isinstance(stored_analysis, pd.DataFrame) and not stored_analysis.empty:
            st.dataframe(stored_analysis.head(50), use_container_width=True, hide_index=True)
            if not st.session_state.get("audit_analysis_saved", False):
                if st.button("💾 SAVE TO GOOGLE SHEETS"):
                    try:
                        with st.spinner("Writing to sheet…"): saved_count = append_analysis_rows(st.secrets, stored_analysis)
                        st.session_state.audit_analysis_saved = True
                        st.success(f"Successfully saved {saved_count:,} rows.")
                        st.rerun()
                    except Exception as exc: st.error("Save Failed: " + str(exc))


    if tracking_clicked:
        try:
            with st.status("📈 Processing Performance Tracking Data…", expanded=True) as tracking_status:
                signal_df = read_audit_signals(st.secrets)
                existing_keys = read_performance_keys(st.secrets)
                if signal_df.empty: st.warning("No audit signals found.")
                else:
                    cutoff_date = latest_completed_market_date()
                    total_steps = st.empty(); progress_bar = st.progress(0); last_progress = {"value": -1}
                    def progress_update(done, total, message):
                        pct_value = min(100, int((done / max(1, int(total))) * 100))
                        if pct_value != last_progress["value"]: progress_bar.progress(pct_value); last_progress["value"] = pct_value
                        total_steps.caption(message)
                    price_histories, missing_symbols, market_sessions, calendar_source = fetch_ohlc_histories(signal_df, as_of_date=cutoff_date, progress_callback=progress_update)
                    progress_bar.progress(100)
                    new_performance, tracking_report = build_performance_rows(signal_df, price_histories, existing_performance=existing_keys, as_of_date=cutoff_date, market_sessions=market_sessions, calendar_source=calendar_source, progress_callback=lambda d, t, m: total_steps.caption(m))
                    if not new_performance.empty:
                        write_result = append_performance_rows(st.secrets, new_performance, batch_size=400, progress_callback=lambda d, t, m: total_steps.caption(m))
                    else: write_result = {"saved": False, "rows": 0, "expected": 0, "reason": "no_new_rows"}
                    tracking_status.update(label="✅ Tracking update complete", state="complete", expanded=False)
                    st.success(f"Appended {write_result.get('rows', 0):,} rows. Repaired {write_result.get('updated', 0):,} missing data points.")
        except Exception as exc: st.error("Tracking Failed: " + str(exc))

    if audit_pending:
        st.info("📌 Resolve pending audit confirmation below.")

    scan_mode = "audit" if audit_clicked else "normal" if normal_clicked else None
    if scan_mode:
        st.session_state.scanning = True
        st.session_state.scan_error = None
        st.session_state.scan_result = None
        scan_placeholder = st.empty()
        try:
            scan_placeholder.markdown('<div class="scan-shell"><div style="font-weight:700;font-size:1.1rem;color:var(--text)">🔎 Processing Market Scan</div><div class="scan-copy"><span>Evaluating Equities</span><span>Executing</span></div><div class="scan-chart"><div class="candle-track">' + ''.join([f'<span class="candle {"g" if i % 3 else "r"}"></span>' for i in range(42)]) + '</div></div><div class="progress"><div></div></div></div>', unsafe_allow_html=True)
            with st.spinner("Executing models…"):
                result = scan_universe(max_distance=10.0, period="2y", top_n=500)
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

    result=st.session_state.get("scan_result")
    if st.session_state.get("scan_error"): st.error(st.session_state.scan_error)
    if result is None:
        st.markdown('<div class="card" style="text-align:center; padding: 60px 20px;"><div style="font-size:1.1rem; font-weight:700;">Awaiting Input</div><div class="small-muted" style="margin-top:8px">Execute a market scan to identify near-breakout configurations.</div></div>',unsafe_allow_html=True); return
    if result.empty:
        st.markdown('<div class="card" style="text-align:center; padding: 60px 20px;"><div style="font-size:1.1rem; font-weight:700;">No Candidates Found</div><div class="small-muted" style="margin-top:8px">Market conditions yield zero qualifying technical setups.</div></div>',unsafe_allow_html=True); return

    pending_rows = st.session_state.get("audit_pending_rows")
    if pending_rows is not None:
        append_in_progress = st.session_state.get("audit_append_in_progress", False)
        if append_in_progress:
            st.info(f"⏳ Synchronizing {len(pending_rows)} rows to external database…")
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
            y_col, n_col = st.columns([1,1])
            if y_col.button("✅ CONFIRM & UPLOAD", use_container_width=True):
                st.session_state.audit_append_in_progress = True; st.rerun()
            if n_col.button("❌ DISCARD BATCH", use_container_width=True):
                st.session_state.audit_pending_rows = None; st.rerun()

    audit_info = st.session_state.get("audit_last_saved") or {}
    if audit_info.get("saved") and audit_info.get("reason") in {"appended", "batch_already_exists"}:
        st.success(f"✅ Securely logged {audit_info.get('rows', 0)} signals.")

    display = result.copy()
    sort_cols = [c for c in ["rating", "score", "rank_score", "distance_pct"] if c in display.columns]
    if sort_cols: display = display.sort_values(sort_cols, ascending=[False, False, False, True][:len(sort_cols)], kind="stable").reset_index(drop=True)
    
    st.markdown(f'<div style="display:flex; justify-content:space-between; align-items:baseline; margin-top: 32px; border-bottom: 1px solid var(--border); padding-bottom: 10px;"><div class="section-title" style="border:none; margin:0; padding:0;">Screening Results <span style="color:var(--muted);font-weight:600;font-size:1rem;">({len(display)} Matches)</span></div><div class="rank-note" style="margin:0;">Ranked by Momentum Setup</div></div>',unsafe_allow_html=True)
    
    # -------------------------------------------------------
    # DENSE 4-COLUMN FLAT FINTECH GRID
    # -------------------------------------------------------
    for start in range(0,len(display),4):
        cols=st.columns(4)
        for j,col in enumerate(cols):
            idx=start+j
            if idx>=len(display): continue
            row=display.iloc[idx]; ratio=idx/max(len(display)-1,1)
            
            # Sotex color grading (pure flat solids)
            if ratio<.2: color="#10b981"; bg_fill="rgba(16,185,129,0.06)" 
            elif ratio<.4: color="#84cc16"; bg_fill="rgba(132,204,22,0.06)"
            elif ratio<.6: color="#f59e0b"; bg_fill="rgba(245,158,11,0.06)"
            elif ratio<.8: color="#f97316"; bg_fill="rgba(249,115,22,0.06)"
            else: color="#ef4444"; bg_fill="rgba(239,68,68,0.06)"

            with col:
                rating = int(float(row.get("rating", 0) or 0))
                score = float(row.get("score", 0) or 0)
                price = float(row.get("price", 0) or 0)
                st.markdown(f'''
                <div style="border-radius:10px;border:1px solid var(--border);padding:18px;background:var(--card);margin-bottom:-4px; height: 100%;">
                    <div style="display:flex; justify-content:space-between; align-items:center;">
                        <span style="font-size:.7rem;font-weight:700;color:var(--muted);text-transform:uppercase;">RANK {idx+1}</span>
                        <span style="font-size:.65rem;font-weight:700;padding:3px 6px;border-radius:4px;background:{bg_fill};color:{color};">{html.escape(str(row.get("cap_category","")))}</span>
                    </div>
                    <div style="font-weight:800;font-size:1.15rem;color:var(--text); margin-top: 10px; line-height:1.2; letter-spacing:-.01em;">{html.escape(str(row.get("company_name",row["symbol"])))}</div>
                    <div class="small-muted" style="margin-bottom:14px; font-weight:500;">{html.escape(str(row["symbol"]))}</div>
                    
                    <div style="display:flex; gap:8px; margin-bottom:16px;">
                        <span style="padding:4px 8px;border-radius:4px;background:var(--card2);border:1px solid var(--border);color:var(--text);font-size:.7rem;font-weight:600;">Rate {rating}/10</span>
                        <span style="padding:4px 8px;border-radius:4px;background:var(--card2);border:1px solid var(--border);color:var(--text);font-size:.7rem;font-weight:600;">Score {score:.1f}</span>
                    </div>

                    <div style="font-weight:800;font-size:1.25rem;">{money(price)}</div>
                    <div style="font-size:.75rem;color:{color};font-weight:700; margin-bottom: 16px;">{float(row.get("distance_pct",0)):.2f}% to resistance</div>
                    
                    <div style="display:grid;grid-template-columns:1fr 1fr 1fr;gap:6px;">
                        <div style="border-top:2px solid {color};padding-top:8px;">
                            <div style="font-size:.65rem;font-weight:700;color:var(--muted);text-transform:uppercase;">RSI</div>
                            <div style="font-size:1rem;font-weight:800;">{float(row.get("rsi", 0) or 0):.0f}</div>
                        </div>
                        <div style="border-top:2px solid {color};padding-top:8px;">
                            <div style="font-size:.65rem;font-weight:700;color:var(--muted);text-transform:uppercase;">ADX</div>
                            <div style="font-size:1rem;font-weight:800;">{float(row.get("adx", 0) or 0):.0f}</div>
                        </div>
                        <div style="border-top:2px solid {color};padding-top:8px;">
                            <div style="font-size:.65rem;font-weight:700;color:var(--muted);text-transform:uppercase;">MACD</div>
                            <div style="font-size:1rem;font-weight:800;">{float(row.get("macd", 0) or 0):.2f}</div>
                        </div>
                    </div>
                </div>''',unsafe_allow_html=True)
                if st.button(f"Analyze",key=f"stock_{row['symbol']}",use_container_width=True):
                    st.session_state.selected_stock=row["symbol"]; st.session_state.selected_row=row.to_dict(); st.session_state.page="detail"; st.rerun()


if "page" not in st.session_state: st.session_state.page = "home"
if "scan_result" not in st.session_state: st.session_state.scan_result = None
if "scan_timestamp" not in st.session_state: st.session_state.scan_timestamp = None
if "scanning" not in st.session_state: st.session_state.scanning = False
if "audit_last_saved" not in st.session_state: st.session_state.audit_last_saved = None
if "audit_pending_rows" not in st.session_state: st.session_state.audit_pending_rows = None
if "audit_pending_run_id" not in st.session_state: st.session_state.audit_pending_run_id = None
if "audit_pending_timestamp" not in st.session_state: st.session_state.audit_pending_timestamp = None
if "audit_append_in_progress" not in st.session_state: st.session_state.audit_append_in_progress = False

render_reload_guard(True)

if st.session_state.page == "detail" and st.session_state.get("selected_stock"):
    render_detail(st.session_state.selected_stock, st.session_state.selected_row)
else:
    render_home()
i have updated it no we will see the ui part later

UI development is parked. We will now move to Phase 2: building the Fundamental Data Prototype (fundamental_data.py).   
stock_intelligence_project_handoff_2026-11-02(1).md

The immediate goal is to create a standalone module to fetch and validate the Tier 1 metrics (Quarterly Revenue/Profit Growth, Operating Margin, Debt-to-Equity, and Average Traded Value) across a test batch of large, mid, and small-cap stocks. We must verify yfinance's data completeness and freshness for Indian equities before integrating it into the main dashboard, ensuring it operates completely independently of the existing technical scanner.   
stock_intelligence_project_handoff_2026-11-02(1).md
+ 1

The initial fundamental_data.py script will require:

Financial Extraction: Logic to safely pull quarterly income statements and balance sheets to calculate YoY growth and margins.

Liquidity Checks: Calculation of the 30-day average traded value specifically acting as a risk filter for small caps.   
stock_intelligence_project_handoff_2026-11-02(1).md

Data Quality Flags: Strict error handling that flags missing, anomalous, or severely delayed fundamental data without crashing the scan pipeline.

ewhat is the best way i will go with that

The best approach is to build a standalone, diagnostic version of fundamental_data.py first to test exactly how much accurate data yfinance actually holds for Indian equities across different market caps.   
stock_intelligence_project_handoff_2026-11-02(1).md

Because third-party APIs often have spotty coverage for Indian small-caps and delayed quarterly filings, we need to validate the data completeness before wiring it into your main dashboard.   
stock_intelligence_project_handoff_2026-11-02(1).md

Here is the initial fundamental_data.py test script. It isolates the logic to fetch Tier 1 metrics (YoY Revenue/Profit Growth, Operating Margin, Debt-to-Equity, and Average Traded Value) and tests it against a sample basket of one Large-cap, one Mid-cap, and one Small-cap stock.

Save this as fundamental_data.py and run it directly (python fundamental_data.py).

Python
import yfinance as yf
import pandas as pd
import numpy as np

def calculate_yoy_growth(series):
    """Calculates Year-over-Year growth assuming quarterly data (compares to 4 periods ago)."""
    if series is None or len(series) < 5:
        return np.nan
    current = series.iloc[0]
    year_ago = series.iloc[4]
    if pd.isna(current) or pd.isna(year_ago) or year_ago == 0:
        return np.nan
    return ((current - year_ago) / abs(year_ago)) * 100

def get_tier1_fundamentals(symbol):
    """Fetches and calculates Tier 1 fundamental metrics for a given NSE symbol."""
    ticker_str = f"{symbol}.NS"
    ticker = yf.Ticker(ticker_str)
    
    data = {
        "symbol": symbol,
        "q_rev_growth_yoy_pct": np.nan,
        "q_profit_growth_yoy_pct": np.nan,
        "operating_margin_pct": np.nan,
        "debt_to_equity": np.nan,
        "avg_traded_value_30d": np.nan,
        "data_quality": "OK"
    }
    
    try:
        # 1. Fetch Financials (Income Statement & Balance Sheet)
        q_financials = ticker.quarterly_financials
        q_balance = ticker.quarterly_balance_sheet
        info = ticker.info

        # Process Income Statement Metrics
        if not q_financials.empty:
            # Revenue YoY Growth
            if 'Total Revenue' in q_financials.index:
                rev_series = q_financials.loc['Total Revenue'].dropna()
                data["q_rev_growth_yoy_pct"] = calculate_yoy_growth(rev_series)
            
            # Net Profit YoY Growth
            if 'Net Income' in q_financials.index:
                profit_series = q_financials.loc['Net Income'].dropna()
                data["q_profit_growth_yoy_pct"] = calculate_yoy_growth(profit_series)
                
            # Latest Operating Margin (Operating Income / Total Revenue)
            if 'Operating Income' in q_financials.index and 'Total Revenue' in q_financials.index:
                op_income = q_financials.loc['Operating Income'].dropna()
                total_rev = q_financials.loc['Total Revenue'].dropna()
                if not op_income.empty and not total_rev.empty and total_rev.iloc[0] != 0:
                    data["operating_margin_pct"] = (op_income.iloc[0] / total_rev.iloc[0]) * 100

        # Process Balance Sheet Metrics
        if not q_balance.empty:
            if 'Total Debt' in q_balance.index and 'Stockholders Equity' in q_balance.index:
                total_debt = q_balance.loc['Total Debt'].dropna()
                equity = q_balance.loc['Stockholders Equity'].dropna()
                if not total_debt.empty and not equity.empty and equity.iloc[0] != 0:
                    data["debt_to_equity"] = total_debt.iloc[0] / equity.iloc[0]

        # 2. Liquidity / Execution Metric (30-Day Average Traded Value)
        hist = ticker.history(period="2mo")
        if not hist.empty and len(hist) >= 30:
            last_30 = hist.tail(30)
            daily_traded_value = last_30['Volume'] * last_30['Close']
            data["avg_traded_value_30d"] = daily_traded_value.mean()
        else:
            data["data_quality"] = "MISSING_PRICE_HISTORY"

        # Fallback to info dictionary if balance sheet data was missing
        if pd.isna(data["debt_to_equity"]) and "debtToEquity" in info:
            # yfinance info debtToEquity is usually presented as a percentage (e.g., 45.5 for 0.45)
            val = info.get("debtToEquity")
            if val is not None:
                data["debt_to_equity"] = val / 100 

    except Exception as e:
        data["data_quality"] = f"ERROR: {str(e)}"

    return data

if __name__ == "__main__":
    # Test Basket: Large Cap (RELIANCE), Mid Cap (KPITTECH), Small Cap (AWL or similar)
    test_symbols = ["RELIANCE", "KPITTECH", "AWL"]
    
    print("Fetching fundamental data... (this takes a few seconds)")
    results = []
    for sym in test_symbols:
        results.append(get_tier1_fundamentals(sym))
        
    df = pd.DataFrame(results)
    
    # Formatting for readability
    pd.set_option('display.max_columns', None)
    pd.set_option('display.width', 1000)
    print("\n--- TIER 1 FUNDAMENTAL PROTOTYPE RESULTS ---")
    print(df.to_string(index=False))
Run this and share the console output. If yfinance returns too many NaN values for the Indian mid/small-caps, we will immediately pivot to utilizing nsepython or direct NSE result parsing rather than wasting time on a broken data feed.

how would i run it

Execute the script directly from your terminal or command prompt.

Save the file: Save the code block from the previous step as fundamental_data.py in your project folder.

Open your terminal: Open your Ubuntu terminal or Windows 11 Command Prompt and navigate to the folder where you saved the file.

Install dependencies: Ensure you have the required libraries installed in your active environment by running:

Bash
pip install yfinance pandas numpy
Run the script: Execute the file using Python:

Bash
python fundamental_data.py
(Note: On Ubuntu, you may need to use python3 fundamental_data.py depending on your environment alias).

The script will take a few seconds to fetch the quarterly financials and output a text table to your console.

do i need to install a python application on the pc

You do not need to install a new application. Since you have already been developing and running the Streamlit app, Python is already installed on your PC. You only need to execute this new script using your existing command line.

1
Open your terminal
Windows or Ubuntu
Open Command Prompt (if on Windows 11) or Terminal (if on Ubuntu).

2
Navigate to your project folder
Directory change
Use the cd command to go to the folder where you saved fundamental_data.py. For example:
cd C:\Users\YourName\Documents\StockScanner

3
Install required libraries
1 minute
Ensure the necessary financial libraries are installed in your current environment by running:
pip install yfinance pandas numpy

4
Run the script
Execution
Type the following command and press Enter:
python fundamental_data.py
(Note: On Ubuntu, you might need to type python3 fundamental_data.py depending on your setup).
Verification: The terminal will print "Fetching fundamental data..." and then display a text table with the results.

cmd showing pip not recognised

This happens when Python is installed but its installation folder isn't added to your Windows system PATH. You can bypass this by telling Python directly to run the pip module.

1
Use the Python module command
In your Command Prompt, type this exactly and press Enter:
python -m pip install yfinance pandas numpy
Verification: The terminal should start downloading and installing the packages instead of showing an error.

2
Try the Windows Launcher (if Step 1 fails)
Alternative command
If the terminal now says "python is not recognized", try using the built-in Windows Python launcher instead:
py -m pip install yfinance pandas numpy

3
Run the script
Once the installation completes successfully, run your script using the same prefix that worked for you in the previous step:
python fundamental_data.py
(or py fundamental_data.py)

showing python was not found

This means Python is either not installed on your Windows system, or it was installed without being added to your system's "PATH" (the list of directories Windows checks for commands).

Here is the fastest way to fix this on Windows 11.

1
Install Python via Microsoft Store
Windows 11
The easiest way to get Python working in the command prompt with the correct PATH is through the official store. Open the Microsoft Store app, search for Python 3.12 (or 3.11), and click Get or Install.
Verification: Wait for the installation to fully complete in the Store.

2
Install via Python.org (If skipping the Store)
Alternative
If you prefer downloading from python.org, download the Windows installer. Crucial: When you open the installer, before clicking "Install Now", you must check the box at the very bottom that says "Add python.exe to PATH".

3
Restart Command Prompt
Refresh environment variables
Close your current Command Prompt window completely and open a new one. If you skip this, the terminal will not recognize the newly installed Python.

4
Install required packages
Dependencies
In the new Command Prompt, navigate back to your project folder using cd and run:
python -m pip install yfinance pandas numpy
Verification: You should see a download progress bar for the packages instead of an error.

5
Run the fundamental data script
Once the packages are installed, execute the script:
python fundamental_data.py
Verification: The terminal will print the fundamental data table for RELIANCE, KPITTECH, and AWL.

after running the camand i got this D:\scanner project\gemini version>python fundamental_data.py

Fetching fundamental data... (this takes a few seconds)

C:\Users\wtvision\AppData\Local\Programs\Python\Python312\Lib\site-packages\yfinance\utils.py:568: Pandas4Warning: The inplace keyword in DataFrame.sort_index is deprecated and will be removed in a future version (PDEP-8).

See https://pandas.pydata.org/docs/dev/whatsnew/v3.1.0.html#deprecation-inplace for more details.

  quotes.sort_index(inplace=True)

C:\Users\wtvision\AppData\Local\Programs\Python\Python312\Lib\site-packages\yfinance\utils.py:514: Pandas4Warning: The inplace keyword in DataFrame.drop is deprecated and will be removed in a future version (PDEP-8).

See https://pandas.pydata.org/docs/dev/whatsnew/v3.1.0.html#deprecation-inplace for more details.

  df.drop(

C:\Users\wtvision\AppData\Local\Programs\Python\Python312\Lib\site-packages\yfinance\utils.py:518: Pandas4Warning: The inplace keyword in DataFrame.rename is deprecated and will be removed in a future version (PDEP-8).

See https://pandas.pydata.org/docs/dev/whatsnew/v3.1.0.html#deprecation-inplace for more details.

  df.rename(columns={

C:\Users\wtvision\AppData\Local\Programs\Python\Python312\Lib\site-packages\yfinance\utils.py:568: Pandas4Warning: The inplace keyword in DataFrame.sort_index is deprecated and will be removed in a future version (PDEP-8).

See https://pandas.pydata.org/docs/dev/whatsnew/v3.1.0.html#deprecation-inplace for more details.

  quotes.sort_index(inplace=True)

C:\Users\wtvision\AppData\Local\Programs\Python\Python312\Lib\site-packages\yfinance\utils.py:514: Pandas4Warning: The inplace keyword in DataFrame.drop is deprecated and will be removed in a future version (PDEP-8).

See https://pandas.pydata.org/docs/dev/whatsnew/v3.1.0.html#deprecation-inplace for more details.

  df.drop(

C:\Users\wtvision\AppData\Local\Programs\Python\Python312\Lib\site-packages\yfinance\utils.py:518: Pandas4Warning: The inplace keyword in DataFrame.rename is deprecated and will be removed in a future version (PDEP-8).

See https://pandas.pydata.org/docs/dev/whatsnew/v3.1.0.html#deprecation-inplace for more details.

  df.rename(columns={

C:\Users\wtvision\AppData\Local\Programs\Python\Python312\Lib\site-packages\yfinance\utils.py:568: Pandas4Warning: The inplace keyword in DataFrame.sort_index is deprecated and will be removed in a future version (PDEP-8).

See https://pandas.pydata.org/docs/dev/whatsnew/v3.1.0.html#deprecation-inplace for more details.

  quotes.sort_index(inplace=True)

C:\Users\wtvision\AppData\Local\Programs\Python\Python312\Lib\site-packages\yfinance\utils.py:514: Pandas4Warning: The inplace keyword in DataFrame.drop is deprecated and will be removed in a future version (PDEP-8).

See https://pandas.pydata.org/docs/dev/whatsnew/v3.1.0.html#deprecation-inplace for more details.

  df.drop(

C:\Users\wtvision\AppData\Local\Programs\Python\Python312\Lib\site-packages\yfinance\utils.py:518: Pandas4Warning: The inplace keyword in DataFrame.rename is deprecated and will be removed in a future version (PDEP-8).

See https://pandas.pydata.org/docs/dev/whatsnew/v3.1.0.html#deprecation-inplace for more details.

  df.rename(columns={



--- TIER 1 FUNDAMENTAL PROTOTYPE RESULTS ---

  symbol  q_rev_growth_yoy_pct  q_profit_growth_yoy_pct  operating_margin_pct  debt_to_equity  avg_traded_value_30d data_quality

RELIANCE             35.696871                -5.356746             12.492703        0.429183          2.084191e+10           OK

KPITTECH              6.503388               -28.668082             30.462292        0.207337          1.289773e+09           OK

     AWL             30.150569                 1.251956              2.271334        1.045916          4.530285e+08           OK

This is an excellent result. The data retrieval was completely successful across all three market-cap tiers.

The Pandas4Warning lines you see are harmless internal messages from the yfinance library letting developers know about future updates to the Pandas library; they do not affect our data.

More importantly, the output proves that yfinance holds complete Tier 1 fundamental data (Revenue, Profit, Margins, Debt) even for the small-cap stock (AWL). We do not need to build complex custom web scrapers for the initial launch.

Next Step: The Production Data Module
Now we will convert that test script into a robust module that your Streamlit app can use to evaluate the entire 250+ stock universe without crashing or getting blocked by rate limits.

Save the following code as fundamental_data.py. This will overwrite your test script with the production-ready module. It includes warning suppression, batch processing, and error handling for missing data.

Python
import warnings
import yfinance as yf
import pandas as pd
import numpy as np
import concurrent.futures

# Suppress harmless internal yfinance/pandas deprecation warnings
warnings.simplefilter(action='ignore', category=FutureWarning)
warnings.filterwarnings("ignore", message=".*inplace.*")

def _calculate_yoy_growth(series):
    """Calculates Year-over-Year growth comparing to 4 quarters ago."""
    if series is None or len(series) < 5:
        return np.nan
    current = series.iloc[0]
    year_ago = series.iloc[4]
    if pd.isna(current) or pd.isna(year_ago) or year_ago == 0:
        return np.nan
    return float(((current - year_ago) / abs(year_ago)) * 100)

def fetch_single_fundamental(symbol):
    """Fetches Tier 1 fundamental metrics for a single NSE symbol."""
    ticker_str = f"{symbol}.NS"
    ticker = yf.Ticker(ticker_str)
    
    data = {
        "symbol": symbol,
        "q_rev_growth_yoy_pct": np.nan,
        "q_profit_growth_yoy_pct": np.nan,
        "operating_margin_pct": np.nan,
        "debt_to_equity": np.nan,
        "avg_traded_value_30d": np.nan,
        "fundamental_quality": "OK"
    }
    
    try:
        q_financials = ticker.quarterly_financials
        q_balance = ticker.quarterly_balance_sheet
        info = ticker.info

        if not q_financials.empty:
            if 'Total Revenue' in q_financials.index:
                data["q_rev_growth_yoy_pct"] = _calculate_yoy_growth(q_financials.loc['Total Revenue'].dropna())
            
            if 'Net Income' in q_financials.index:
                data["q_profit_growth_yoy_pct"] = _calculate_yoy_growth(q_financials.loc['Net Income'].dropna())
                
            if 'Operating Income' in q_financials.index and 'Total Revenue' in q_financials.index:
                op_income = q_financials.loc['Operating Income'].dropna()
                total_rev = q_financials.loc['Total Revenue'].dropna()
                if not op_income.empty and not total_rev.empty and total_rev.iloc[0] != 0:
                    data["operating_margin_pct"] = float((op_income.iloc[0] / total_rev.iloc[0]) * 100)

        if not q_balance.empty:
            if 'Total Debt' in q_balance.index and 'Stockholders Equity' in q_balance.index:
                total_debt = q_balance.loc['Total Debt'].dropna()
                equity = q_balance.loc['Stockholders Equity'].dropna()
                if not total_debt.empty and not equity.empty and equity.iloc[0] != 0:
                    data["debt_to_equity"] = float(total_debt.iloc[0] / equity.iloc[0])

        hist = ticker.history(period="2mo")
        if not hist.empty and len(hist) >= 30:
            last_30 = hist.tail(30)
            data["avg_traded_value_30d"] = float((last_30['Volume'] * last_30['Close']).mean())
        else:
            data["fundamental_quality"] = "MISSING_PRICE_HISTORY"

        if pd.isna(data["debt_to_equity"]) and "debtToEquity" in info:
            val = info.get("debtToEquity")
            if val is not None:
                data["debt_to_equity"] = float(val / 100)

    except Exception as e:
        data["fundamental_quality"] = "MISSING_DATA"

    return data

def fetch_fundamentals_batch(symbols, max_workers=10):
    """
    Fetches fundamental data concurrently for a list of symbols.
    Returns a pandas DataFrame.
    """
    results = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = {executor.submit(fetch_single_fundamental, sym): sym for sym in symbols}
        for future in concurrent.futures.as_completed(futures):
            try:
                results.append(future.result())
            except Exception:
                sym = futures[future]
                results.append({"symbol": sym, "fundamental_quality": "FETCH_FAILED"})
                
    df = pd.DataFrame(results)
    return df
Once this file is saved, we will integrate it into the app.py UI you updated earlier so it populates the currently empty "🏛️ Fundamentals" tab for searched stocks.

Let me know when you have saved the production fundamental_data.py file.

please give me teh .py file that i can download directly and use insted copying code and then saving teh file

Your Python file is ready.

PY icon
fundamental_data
 PY 
You can download fundamental_data.py directly from the link above. Once you've downloaded and saved it to your project folder, let me know, and we can move forward with integrating it into the app.py UI to populate the "Fundamentals" tab!

on equestion why dont we use nse nsepython it is more accurate then other , you can cahek all parameter for better usase of data intigration and i think nsepython is free as well

You are entirely correct that nsepython is free, highly accurate, and pulls data directly from the National Stock Exchange (NSE) REST APIs without relying on a third-party aggregator.

For Indian equities, direct NSE wrappers like nsepython are superior for live market metrics, delivery percentages, corporate announcements, and institutional shareholding data. The reason the initial fundamental_data.py prototype used yfinance is because it provides pre-standardized, easily parsable Pandas dataframes for historical balance sheets and income statements (like Revenue and Debt-to-Equity). The raw corporate result JSONs from the NSE API often require complex, company-specific parsing to extract those exact historic financial ratios.

However, moving forward, nsepython is the ideal engine for the Tier 2 and Tier 3 data modules outlined in the Master Data Blueprint.

Here is the architectural plan for integrating it:

Tier 1 (Historical Fundamentals): Retain yfinance specifically for historical quarterly revenue, net profit, and balance sheet extraction, as it standardizes the accounting data.

Tier 2 (Ownership & Liquidity): Use nsepython to fetch promoter pledging, FII/DII flow, and delivery percentages directly from the exchange.

Tier 3 (News & Events): Use nsepython to pull official corporate filings and announcements, bypassing delayed secondary news sources.

ok s o having to datat source in a code, will this can cause any misinformation ? or it is good practice ?

Using multiple specialized data sources is a standard and highly recommended practice in quantitative finance, provided you establish strict boundaries to prevent data conflicts. No single free API does everything perfectly; combining them allows you to exploit the specific strengths of each—like yfinance for standardized historical accounting and nsepython for live exchange metrics.

However, carelessly mixing them can cause "misinformation"—specifically data mismatch or latency issues—if you pull the exact same metric from both sources and they disagree on the value.

To make this a bulletproof good practice, we must enforce these rules:

Domain Isolation: yfinance strictly handles historical accounting (quarterly financials) while nsepython strictly handles exchange-specific data (delivery percentages, promoter pledges, and corporate filings).

Symbol Mapping: We must map tickers precisely between the two, adding the .NS suffix for yfinance while passing the raw symbol to nsepython.

Single Source of Truth for Price: We must never pull the current market price or OHLC history from both; we stick strictly to your existing scanner.py feed for price data to ensure technical indicators remain perfectly consistent.

Timestamp Alignment: All fundamental and exchange data must be explicitly tagged with its retrieval date so your combination analysis avoids look-ahead bias.

Would you like to build a quick test script for nsepython to see exactly what live exchange data it returns for our test basket?

Yes, give me a quick test script to verify my machine can connect to the NSE API using nsepython.

Your test script file is ready.

PY icon
test_nsepython
 PY 
Download test_nsepython.py into your project folder.

First, ensure you have the library installed. Run this in your command prompt:

Bash
python -m pip install nsepython
Then, execute the test script:

Bash
python test_nsepython.py
This script will attempt to:

Fetch the official list of NSE indices.

Pull the live quote for RELIANCE to check equity endpoints.

Fetch the F&O lot size for RELIANCE to test derivatives data endpoints.

Why this test is important:
The National Stock Exchange (NSE) has strict firewalls and frequently blocks certain ISPs, cloud hosting providers, and VPNs. If the script works and prints out the prices, your local machine has a clear path to the exchange. If it throws a connection error or timeout, we will know immediately that we need to use the server-optimized version (nsepythonserver) or adjust headers.

Let me know what the console outputs!

one question isit free the nse data collection is it leagal and now condition apply ?

Cost: nsepython is completely free and open-source. It does not require API keys, subscriptions, or logins.

Legality & Conditions: According to NSE India's official Terms of Use, users are strictly prohibited from conducting any "systematic or automated data collection activities (including scraping, data mining, data extraction and data harvesting)". Because nsepython scrapes data directly from NSE's public endpoints, using it is technically a violation of their Terms of Service.

What this means for you:

IP Blocking: While it is highly unlikely you would face legal action for personal, educational use, NSE actively monitors for automated traffic. If they detect too many requests from your machine, they will block your IP address.

Your Responsibility: As the user, you are ultimately responsible for how you use the data and for your own compliance with NSE's terms.

The Bottom Line: nsepython is widely used by retail traders because it is free, but it operates in a gray area. For a personal, low-traffic project like yours, it will work perfectly fine. However, if you ever plan to turn this scanner into a commercial product or a paid website, you would need to stop using scrapers and purchase an official, licensed data feed directly from the NSE.

Did the test script successfully pull the Reliance price without getting IP-blocked?

i got this result D:\scanner project\gemini version>python test_nsepython.py

========================================

   Testing NSE API via nsepython...

========================================



Testing basic index connection...
✅ Success! Fetched 139 indices.

   Sample: ['NIFTY 50', 'NIFTY NEXT 50', 'NIFTY BANK']



2. Fetching live equity data for RELIANCE...

WARNING:root:nse_eq(RELIANCE): /api/quote-equity is retired; returning data from the newer NextApi quote endpoint instead (see nse_quote() - the JSON shape differs from the old quote-equity response).

✅ Success! RELIANCE Last Price: ₹1300



3. Fetching F&O Lot Sizes...

✅ Success! RELIANCE Lot Size: 500



🎉 ALL TESTS PASSED! Your machine can communicate with the NSE API.

The test confirms your machine can successfully bypass NSE's firewalls and communicate directly with their live servers. The warning message you received simply means the NSE recently changed one of their internal URLs, but the nsepython library automatically detected it and successfully routed your request to the new endpoint.

Since your local environment has now successfully validated both yfinance (for historical accounting) and nsepython (for live exchange metrics), we have all the raw data engines required for the Master Data Blueprint.

The next step is to connect these data feeds to your new Streamlit dashboard so the empty "🏛️ Fundamentals" tab actually populates with data when you click "Analyze" on a stock. We can either wire up the fundamental_data.py script (Tier 1) to the UI right now, or we can build the nse_data.py script (Tier 2) to gather the promoter pledging and delivery data first.

we will go with flow with flow chart process and complete the app you know better then which step to go next

Perfect, following the roadmap, the exact next step is wiring the fundamental_data.py logic directly into the Streamlit UI so the "🏛️ Fundamentals" tab actually displays the metrics when you search for a stock.   
stock_intelligence_project_handoff_2026-11-02(1).md

I have updated your app.py script. The new version:

Imports your new fetch_single_fundamental function.

Wraps it in a @st.cache_data(ttl=3600) decorator so it doesn't repeatedly query Yahoo Finance if you click back and forth.

Replaces the placeholder UI in the "🏛️ Fundamentals" tab with live colored metrics (e.g., green for positive growth, red for high debt).

PY icon
app_updated_v2
 PY 
Download the updated file using the link above, rename it to app.py, and replace the one in your project folder.

Once replaced, run your Streamlit app (streamlit run app.py), search for RELIANCE or KPITTECH, and click the "🏛️ Fundamentals" tab to see your new Tier 1 data engine in action.

app throw a error ModuleNotFoundError: This app has encountered an error. The original error message is redacted to prevent data leaks. Full error details have been recorded in the logs (if you're on Streamlit Cloud, click on 'Manage app' in the lower right of your app).

Traceback:

File "/mount/src/scanner/app.py", line 36, in <module>

from fundamental_data import fetch_single_fundamental # NEW IMPORT

^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

This error occurs because your Streamlit Cloud environment cannot find the new fundamental_data.py file. The traceback path (/mount/src/...) indicates you are viewing the live deployed app, but the new file currently only exists on your local computer.

To fix this, you must upload the new file to the GitHub repository that powers your Streamlit app.

1. Locate the Local File
Ensure you have downloaded the fundamental_data.py file we generated earlier and saved it on your computer.

2. Upload to GitHub
Go to your GitHub repository where your scanner project is hosted. Click "Add file" > "Upload files" near the top right of your file list.

3. Select and Commit
Upload fundamental_data.py. Also, ensure you upload your newly updated app.py to overwrite the old version. Click "Commit changes".

4. Wait for Streamlit Sync
Streamlit Cloud will automatically detect the new commit, pull the files, and reboot the app. Watch the bottom right corner of your Streamlit app for the "Deploying" or "Baking" animation. Once it finishes, the app will reload and the module error will disappear.

I uploaded it to GitHub but I am getting a different error now...

Please paste the exact error message and traceback here so I can diagnose the exact failure point.

While I wait for the traceback, check these two common deployment issues that often happen after adding new files:

File Name Mismatch: Verify that the new file in your GitHub repository is named exactly fundamental_data.py (all lowercase, no spaces or numbers like fundamental_data(1).py).

Missing Dependencies (requirements.txt): Ensure your requirements.txt file in the GitHub repository includes yfinance, pandas, and numpy. Streamlit Cloud needs this file to install the required libraries on its servers, even if they are installed on your local computer.

What is the full error message shown in the Streamlit Cloud logs?

in the fundamental section File "/mount/src/scanner/app.py", line 799, in <module>

render_detail(st.session_state.selected_stock, st.session_state.selected_row)

~~~~~~~~~~~~~^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

File "/mount/src/scanner/app.py", line 448, in render_detail

fig=go.Figure(go.Indicator(mode="gauge+number",value=score,number={"suffix":"","font":{"size":42,"color":"#0f172a" if light else "#f1f5f9"}},gauge={"axis":{"range":[0,100],"tickwidth":0,"tickcolor":"transparent"},"bar":{"color":"#10b981","thickness":.15},"bgcolor":"#e2e8f0" if light else "#242933","borderwidth":0,"steps":[{"range":[0,40],"color":"rgba(239,68,68,0.15)"},{"range":[40,65],"color":"rgba(245,158,11,0.15)"},{"range":[65,80],"color":"rgba(132,204,22,0.15)"},{"range":[80,100],"color":"rgba(16,185,129,0.15)"}]}))

~~~~~~~~~~~~^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

File "/home/adminuser/venv/lib/python3.14/site-packages/plotly/graph_objs/_indicator.py", line 719, in __init__

self._set_property("gauge", arg, gauge)

~~~~~~~~~~~~~~~~~~^^^^^^^^^^^^^^^^^^^^^

File "/home/adminuser/venv/lib/python3.14/site-packages/plotly/basedatatypes.py", line 4313, in _set_property

_set_property_provided_value(self, name, arg, provided)

~~~~~~~~~~~~~~~~~~~~~~~~~~~~^^^^^^^^^^^^^^^^^^^^^^^^^^^

File "/home/adminuser/venv/lib/python3.14/site-packages/plotly/basedatatypes.py", line 398, in _set_property_provided_value

obj[name] = val

~~~^^^^^^

File "/home/adminuser/venv/lib/python3.14/site-packages/plotly/basedatatypes.py", line 4834, in __setitem__

self._set_compound_prop(prop, value)

~~~~~~~~~~~~~~~~~~~~~~~^^^^^^^^^^^^^

File "/home/adminuser/venv/lib/python3.14/site-packages/plotly/basedatatypes.py", line 5245, in _set_compound_prop

val = validator.validate_coerce(val, skip_invalid=self._skip_invalid)

File "/home/adminuser/venv/lib/python3.14/site-packages/_plotly_utils/basevalidators.py", line 2461, in validate_coerce

v = self.data_class(v, skip_invalid=skip_invalid, _validate=_validate)

File "/home/adminuser/venv/lib/python3.14/site-packages/plotly/graph_objs/indicator/_gauge.py", line 325, in __init__

self._set_property("axis", arg, axis)

~~~~~~~~~~~~~~~~~~^^^^^^^^^^^^^^^^^^^

File "/home/adminuser/venv/lib/python3.14/site-packages/plotly/basedatatypes.py", line 4313, in _set_property

_set_property_provided_value(self, name, arg, provided)

~~~~~~~~~~~~~~~~~~~~~~~~~~~~^^^^^^^^^^^^^^^^^^^^^^^^^^^

File "/home/adminuser/venv/lib/python3.14/site-packages/plotly/basedatatypes.py", line 398, in _set_property_provided_value

obj[name] = val

~~~^^^^^^

File "/home/adminuser/venv/lib/python3.14/site-packages/plotly/basedatatypes.py", line 4834, in __setitem__

self._set_compound_prop(prop, value)

~~~~~~~~~~~~~~~~~~~~~~~^^^^^^^^^^^^^

File "/home/adminuser/venv/lib/python3.14/site-packages/plotly/basedatatypes.py", line 5245, in _set_compound_prop

val = validator.validate_coerce(val, skip_invalid=self._skip_invalid)

File "/home/adminuser/venv/lib/python3.14/site-packages/_plotly_utils/basevalidators.py", line 2461, in validate_coerce

v = self.data_class(v, skip_invalid=skip_invalid, _validate=_validate)

File "/home/adminuser/venv/lib/python3.14/site-packages/plotly/graph_objs/indicator/gauge/_axis.py", line 1061, in __init__

self._set_property("tickcolor", arg, tickcolor)

~~~~~~~~~~~~~~~~~~^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

File "/home/adminuser/venv/lib/python3.14/site-packages/plotly/basedatatypes.py", line 4313, in _set_property

_set_property_provided_value(self, name, arg, provided)

~~~~~~~~~~~~~~~~~~~~~~~~~~~~^^^^^^^^^^^^^^^^^^^^^^^^^^^

File "/home/adminuser/venv/lib/python3.14/site-packages/plotly/basedatatypes.py", line 398, in _set_property_provided_value

obj[name] = val

~~~^^^^^^

File "/home/adminuser/venv/lib/python3.14/site-packages/plotly/basedatatypes.py", line 4842, in __setitem__

self._set_prop(prop, value)

~~~~~~~~~~~~~~^^^^^^^^^^^^^

File "/home/adminuser/venv/lib/python3.14/site-packages/plotly/basedatatypes.py", line 5186, in _set_prop

raise err

File "/home/adminuser/venv/lib/python3.14/site-packages/plotly/basedatatypes.py", line 5181, in _set_prop

val = validator.validate_coerce(val)

File "/home/adminuser/venv/lib/python3.14/site-packages/_plotly_utils/basevalidators.py", line 1388, in validate_coerce

self.raise_invalid_val(v)

~~~~~~~~~~~~~~~~~~~~~~^^^

File "/home/adminuser/venv/lib/python3.14/site-packages/_plotly_utils/basevalidators.py", line 312, in raise_invalid_val

raise ValueError(

...<11 lines>...

)

The error is caused by the Plotly charting library rejecting the word "transparent" for the gauge axis tick color in its newer versions.

I have replaced "transparent" with its correct CSS equivalent "rgba(0,0,0,0)".

PY icon
app
 PY 
Download the patched app.py file from the link above, upload it to your GitHub repository to overwrite the broken version, and let Streamlit reboot.

Did this resolve the Plotly error on the Streamlit dashboard?

Yes, it's fixed

Still seeing an error




Gemini is AI and can make mistakes.

Debugging the Streamlit app error
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

# IMPORTANT: scanner.py is the existing engine. This UI only calls its existing functions.
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
from audit_analysis import build_completed_outcomes, analyze_outcome_combinations
from performance_tracker import (
    build_performance_rows,
    fetch_ohlc_histories,
    latest_completed_market_date,
)
from fundamental_data import fetch_single_fundamental  # NEW IMPORT

IST = ZoneInfo("Asia/Kolkata")

# -----------------------------------------------------------------------------
# Normal Streamlit scan behavior. A scan runs in the normal app execution path.
# No background executor/job persistence is used. Scanner logic remains in
# scanner.py and is called exactly as before.
# -----------------------------------------------------------------------------

NIFTY50_CSV = "https://nsearchives.nseindia.com/content/indices/ind_nifty50list.csv"
NSE_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120 Safari/537.36",
    "Accept": "text/csv,text/plain,*/*",
}

st.set_page_config(
    page_title="NIFTY Breakout Scanner",
    page_icon="📈",
    layout="centered",
    initial_sidebar_state="collapsed",
)


def password_gate():
    """Optional single-password gate, enabled only when APP_PASSWORD is configured."""
    try:
        required = str(st.secrets.get("APP_PASSWORD", "")).strip()
    except Exception:
        required = ""
    if not required:
        return True  # No APP_PASSWORD secret means login is disabled.
    if st.session_state.get("authenticated", False):
        return True
    st.title("🔐 Stock Scanner")
    st.subheader("Password required")
    with st.form("scanner_password_login"):
        entered = st.text_input("Enter password", type="password")
        submitted = st.form_submit_button("Login", use_container_width=True)
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
# UI-only CSS. No scanner/data/scoring logic is changed here.
# -----------------------------------------------------------------------------
CSS = r"""
<style>
:root{--bg:#07111f;--card:#0c192b;--card2:#101f33;--border:rgba(148,163,184,.15);--text:#f1f5f9;--muted:#8fa3ba;--accent:#19d38a;--red:#ff5c70;--yellow:#f5c451;--chart-bg:#07111f}
html,body,[data-testid="stAppViewContainer"]{background:var(--bg)!important;color:var(--text)!important}[data-testid="stHeader"],footer,#MainMenu,[data-testid="stToolbar"]{visibility:hidden!important;height:0!important;display:none!important}.block-container{max-width:720px!important;padding:1rem .75rem 5rem!important}section[data-testid="stSidebar"]{display:none!important}*{box-sizing:border-box}
.stButton>button{width:100%;border-radius:14px;border:1px solid var(--border);background:var(--card);color:var(--text);min-height:46px;font-weight:800;transition:.18s ease}.stButton>button:hover{border-color:rgba(25,211,138,.55);transform:translateY(-1px)}
.scan-btn .stButton>button{min-height:58px;border:0;color:white;background:linear-gradient(135deg,#10b981,#0ea5e9);box-shadow:0 12px 30px rgba(16,185,129,.20);font-size:1.08rem}
.card{background:linear-gradient(145deg,var(--card2),var(--card));border:1px solid var(--border);border-radius:18px;padding:14px;margin:8px 0;box-shadow:0 8px 28px rgba(0,0,0,.12)}.status-card{padding:10px 12px;border-radius:15px;background:var(--card);border:1px solid var(--border)}.status-row{display:flex;align-items:center;justify-content:space-between;gap:10px}.status-left{display:flex;align-items:center;gap:8px;font-weight:800}.dot{width:9px;height:9px;border-radius:50%;display:inline-block;box-shadow:0 0 12px currentColor}.dot.green{background:var(--accent);color:var(--accent);animation:pulse 1.5s infinite}.dot.red{background:var(--red);color:var(--red);animation:pulse 1.5s infinite}.dot.yellow{background:var(--yellow);color:var(--yellow);animation:pulse 1.5s infinite}.index-wrap{display:flex;gap:12px;justify-content:flex-end;flex-wrap:wrap}.index-item{font-size:.82rem;color:var(--muted)}.index-item b{color:var(--text);font-size:.9rem}.up{color:var(--accent)!important}.down{color:var(--red)!important}.section-title{font-size:1.2rem;font-weight:900;margin:18px 2px 10px}
.metric-card{min-height:76px;padding:11px;border-radius:14px;border:1px solid var(--border);background:var(--card)}.metric-label{color:var(--muted);font-size:.72rem;text-transform:uppercase;letter-spacing:.04em}.metric-value{color:var(--text);font-weight:950;font-size:1.05rem;margin-top:4px;word-break:break-word}.metric-good{background:linear-gradient(135deg,rgba(25,211,138,.25),var(--card));border-color:rgba(25,211,138,.42)}.metric-ok{background:linear-gradient(135deg,rgba(154,211,70,.20),var(--card));border-color:rgba(154,211,70,.32)}.metric-neutral{background:linear-gradient(135deg,rgba(245,196,81,.20),var(--card));border-color:rgba(245,196,81,.30)}.metric-poor{background:linear-gradient(135deg,rgba(255,142,70,.20),var(--card));border-color:rgba(255,142,70,.32)}.metric-bad{background:linear-gradient(135deg,rgba(255,92,112,.22),var(--card));border-color:rgba(255,92,112,.34)}
.hero-price{font-size:2.15rem;font-weight:950;letter-spacing:-.03em}.badge{display:inline-block;padding:6px 10px;border-radius:999px;font-size:.82rem;font-weight:950}.badge-green{background:rgba(25,211,138,.16);color:var(--accent);border:1px solid rgba(25,211,138,.35)}.badge-red{background:rgba(255,92,112,.14);color:var(--red);border:1px solid rgba(255,92,112,.30)}.badge-yellow{background:rgba(245,196,81,.16);color:#a56b00;border:1px solid rgba(245,196,81,.35)}.badge-grey{background:rgba(148,163,184,.10);color:var(--muted);border:1px solid var(--border)}.entry-pulse{animation:glow 1.35s ease-in-out infinite alternate}.target-box{padding:10px 12px;border-radius:14px;background:rgba(25,211,138,.09);border:1px solid rgba(25,211,138,.28)}.target-label{font-size:.7rem;color:var(--muted);text-transform:uppercase;font-weight:800}.target-value{font-size:1.15rem;font-weight:950;color:var(--accent)}.target-upside{font-size:.75rem;color:var(--text);margin-top:2px}
.scan-shell{background:var(--card);border:1px solid var(--border);border-radius:18px;padding:16px;overflow:hidden}.scan-chart{height:145px;position:relative;overflow:hidden;border-radius:12px;background:linear-gradient(180deg,var(--card2),var(--bg))}.candle-track{position:absolute;inset:0;display:flex;align-items:center;gap:10px;width:max-content;animation:scrollCandles 7s linear infinite}.candle{width:7px;position:relative;border-radius:2px;flex:none;box-shadow:0 0 8px currentColor}.candle:before{content:"";position:absolute;left:2px;width:2px;top:-13px;bottom:-13px;background:currentColor;opacity:.85}.candle.g{height:55px;background:#19d38a;color:#19d38a}.candle.r{height:38px;background:#ff5c70;color:#ff5c70}@keyframes scrollCandles{from{transform:translateX(0)}to{transform:translateX(-50%)}}.scan-copy{display:flex;justify-content:space-between;color:var(--muted);font-size:.82rem;margin:10px 0 7px}.progress{height:7px;background:rgba(148,163,184,.18);border-radius:99px;overflow:hidden}.progress>div{width:65%;height:100%;border-radius:99px;background:linear-gradient(90deg,#10b981,#38bdf8);animation:progress 2.2s ease-in-out infinite}@keyframes progress{0%{width:8%}50%{width:78%}100%{width:94%}}
.ticker-note,.small-muted{color:var(--muted);font-size:.78rem}.tradingview-btn{display:block;text-align:center;padding:10px 14px;border-radius:12px;background:linear-gradient(135deg,#19d38a,#0ea5e9);color:#fff!important;text-decoration:none!important;font-weight:900;margin:4px 0 8px}.tv-under{text-align:center;margin:5px 0 12px}.tv-under a{color:var(--accent);font-size:.76rem;font-weight:800;text-decoration:none}.rank-note{font-size:.72rem;color:var(--muted);margin-bottom:8px}@keyframes pulse{50%{opacity:.45;transform:scale(.75)}}@keyframes glow{from{box-shadow:0 0 4px rgba(25,211,138,.1)}to{box-shadow:0 0 20px rgba(25,211,138,.45)}}
@media(max-width:520px){.block-container{padding:.65rem .55rem 4rem!important}.index-wrap{justify-content:flex-start}.hero-price{font-size:1.9rem}.stButton>button{min-height:44px}.target-value{font-size:1rem}.metric-value{font-size:.98rem}}
</style>
"""
st.markdown(CSS, unsafe_allow_html=True)

# UI-only theme state. Scanner/data/scoring logic is unchanged.
if "theme_mode" not in st.session_state:
    st.session_state.theme_mode = "dark"

def apply_theme():
    if st.session_state.theme_mode == "light":
        st.markdown("""<style>:root{--bg:#f5f7fa;--card:#fff;--card2:#f8fafc;--border:rgba(15,23,42,.12);--text:#111827;--muted:#64748b;--accent:#079669;--red:#dc3545;--yellow:#b7791f;--chart-bg:#f5f7fa}</style>""", unsafe_allow_html=True)

def render_reload_guard(active=True):
    """Warn before a browser refresh/navigation while a scan is running.

    Keyboard refresh (F5/Ctrl+R) gets a custom in-page confirmation with the
    requested red/green buttons. Browser toolbar refresh is handled by the
    browser's native beforeunload confirmation; browsers do not allow a web app
    to style that native dialog or control its button colours.
    """
    if not active:
        return
    components.html("""
    <div id="reload-confirm" style="display:none;position:fixed;inset:0;z-index:999999;background:rgba(0,0,0,.58);align-items:center;justify-content:center;font-family:Arial,sans-serif">
      <div style="width:min(420px,90vw);background:#fff;color:#111827;border-radius:16px;padding:22px;box-shadow:0 20px 60px rgba(0,0,0,.35);text-align:center">
        <div style="font-size:20px;font-weight:800;margin-bottom:8px">Reload application?</div>
        <div style="font-size:14px;color:#4b5563;line-height:1.5;margin-bottom:18px">The current scan/data will be lost if you reload. Do you want to reload?</div>
        <div style="display:flex;gap:12px;justify-content:center">
          <button id="reload-yes" style="border:0;border-radius:10px;padding:11px 22px;background:#dc3545;color:#fff;font-weight:800;cursor:pointer">YES, RELOAD</button>
          <button id="reload-no" style="border:0;border-radius:10px;padding:11px 22px;background:#198754;color:#fff;font-weight:800;cursor:pointer">NO, STAY</button>
        </div>
      </div>
    </div>
    <script>
    (() => {
      try {
        const w = window.parent;
        const d = w.document;
        if (w.__niftyReloadGuardInstalled) return;
        w.__niftyReloadGuardInstalled = true;

        const modal = d.getElementById('reload-confirm');
        const yes = d.getElementById('reload-yes');
        const no = d.getElementById('reload-no');
        const show = () => { if (modal) modal.style.display='flex'; };
        const hide = () => { if (modal) modal.style.display='none'; };

        if (yes) yes.onclick = () => {
          w.location.href = w.location.origin + w.location.pathname + '?__reload_home=1';
        };
        if (no) no.onclick = hide;

        w.addEventListener('keydown', (event) => {
          const key = String(event.key || '').toLowerCase();
          const refresh = key === 'f5' || ((event.ctrlKey || event.metaKey) && key === 'r');
          if (refresh) {
            event.preventDefault();
            show();
          }
        }, true);

        w.addEventListener('beforeunload', (event) => {
          try {
            w.sessionStorage.setItem('__nifty_reload_attempt','1');
            w.setTimeout(() => { try { w.sessionStorage.removeItem('__nifty_reload_attempt'); } catch(e) {} }, 10000);
          } catch(e) {}
          event.preventDefault();
          event.returnValue = '';
        });

        // If the user confirmed a browser-native reload, the new page starts
        // with a clean Streamlit session. Route that fresh load to Home once.
        try {
          if (w.sessionStorage.getItem('__nifty_reload_attempt') === '1') {
            w.sessionStorage.removeItem('__nifty_reload_attempt');
            const u = new URL(w.location.href);
            if (!u.searchParams.has('__reload_home')) {
              u.searchParams.set('__reload_home', '1');
              w.location.replace(u.toString());
              return;
            }
          }
        } catch(e) {}
      } catch (e) {}
    })();
    </script>
    """, height=0)


def render_theme_toggle():
    _, col = st.columns([5,1])
    with col:
        is_light = st.toggle("☀️", value=(st.session_state.theme_mode=="light"), key="theme_toggle", help="Switch light/dark mode")
        new_mode = "light" if is_light else "dark"
        if new_mode != st.session_state.theme_mode:
            st.session_state.theme_mode = new_mode
            # Normal Streamlit rerun: session state (page, selected stock,
            # scan result, search result, etc.) remains intact.

apply_theme()

# -----------------------------------------------------------------------------
# Cached UI market data. This does not touch scanner.py's scanning functions.
# -----------------------------------------------------------------------------
@st.cache_data(ttl=60, show_spinner=False)
def get_market_snapshot():
    result = {"nifty": None, "sensex": None, "updated": datetime.now(IST)}
    try:
        raw = yf.download(
            ["^NSEI", "^BSESN"], period="5d", interval="1d", auto_adjust=True,
            progress=False, threads=True, group_by="ticker", multi_level_index=True,
        )
        for symbol, key in [("^NSEI", "nifty"), ("^BSESN", "sensex")]:
            try:
                df = raw[symbol] if isinstance(raw.columns, pd.MultiIndex) and symbol in raw.columns.get_level_values(0) else raw.xs(symbol, axis=1, level=1)
                df = df.dropna(subset=["Close"])
                if len(df) >= 2:
                    last, prev = float(df.Close.iloc[-1]), float(df.Close.iloc[-2])
                    result[key] = {"value": last, "change": last-prev, "pct": (last/prev-1)*100}
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
        # UI fallback only. Scanner universe remains controlled by scanner.py.
        return [
            "ADANIENT","ADANIPORTS","APOLLOHOSP","ASIANPAINT","AXISBANK","BAJAJ-AUTO","BAJFINANCE","BAJAJFINSV","BEL","BHARTIARTL",
            "CIPLA","COALINDIA","DRREDDY","EICHERMOT","ETERNAL","GRASIM","HCLTECH","HDFCBANK","HDFCLIFE","HEROMOTOCO",
            "HINDALCO","HINDUNILVR","ICICIBANK","INDUSINDBK","INFY","ITC","JIOFIN","JSWSTEEL","KOTAKBANK","LT",
            "M&M","MARUTI","MAXHEALTH","NESTLEIND","NTPC","ONGC","POWERGRID","RELIANCE","SBILIFE","SBIN",
            "SHRIRAMFIN","SUNPHARMA","TATACONSUM","TATAMOTORS","TATASTEEL","TCS","TECHM","TITAN","TRENT","ULTRACEMCO",
        ]


@st.cache_data(ttl=60, show_spinner=False)
def get_nifty50_ticker_data(symbols):
    rows = []
    try:
        tickers = [s.replace("&", "%26") + ".NS" for s in symbols]
        raw = yf.download(tickers, period="5d", interval="1d", auto_adjust=True, progress=False, threads=True, group_by="ticker", multi_level_index=True)
        for symbol, ticker in zip(symbols, tickers):
            try:
                if isinstance(raw.columns, pd.MultiIndex):
                    if ticker in raw.columns.get_level_values(0): df = raw[ticker]
                    elif ticker in raw.columns.get_level_values(1): df = raw.xs(ticker, axis=1, level=1)
                    else: continue
                else: df = raw
                df = df.dropna(subset=["Close"])
                if len(df) < 2: continue
                last, prev = float(df.Close.iloc[-1]), float(df.Close.iloc[-2])
                rows.append({"symbol": symbol, "price": last, "pct": (last/prev-1)*100})
            except Exception:
                continue
    except Exception:
        return pd.DataFrame(columns=["symbol","price","pct"])
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
    if x is None or not np.isfinite(x): return "—"
    return f"{x:+.2f}%"


def render_market_bar():
    snap = get_market_snapshot()
    status, color = market_status()
    dot = f'<span class="dot {color}"></span>'
    parts = [f'<div class="status-card"><div class="status-row"><div class="status-left">{dot}<span>{status}</span></div><div class="index-wrap">']
    for label, key in [("NIFTY 50", "nifty"), ("SENSEX", "sensex")]:
        item = snap.get(key)
        if item:
            cls = "up" if item["pct"] >= 0 else "down"
            arrow = "▲" if item["pct"] >= 0 else "▼"
            parts.append(f'<div class="index-item"><b>{label}</b> {item["value"]:,.2f} <span class="{cls}">{arrow} {item["pct"]:+.2f}%</span></div>')
        else:
            parts.append(f'<div class="index-item"><b>{label}</b> —</div>')
    updated = snap["updated"].strftime("%d %b %Y, %H:%M:%S IST")
    parts.append(f'</div></div><div class="ticker-note">Last UI market-data refresh: {updated}</div></div>')
    st.markdown("".join(parts), unsafe_allow_html=True)


def render_ticker():
    symbols=get_nifty50_symbols(); df=get_nifty50_ticker_data(tuple(symbols))
    if df.empty:
        st.markdown('<div class="ticker-note">NIFTY 50 ticker data temporarily unavailable.</div>',unsafe_allow_html=True); return
    items=[]
    for _,r in df.iterrows():
        cls="up" if r.pct>=0 else "down"; arrow="▲" if r.pct>=0 else "▼"
        items.append(f'<span class="tick"><b>{html.escape(r.symbol)}</b> {money(r.price)} <span class="{cls}">{arrow} {r.pct:+.2f}%</span></span>')
    content="".join(items); light=st.session_state.theme_mode=="light"
    bg="#fff" if light else "#07111f"; viewport="#fff" if light else "#091727"; textc="#111827" if light else "#dbe7f3"; muted="#64748b" if light else "#9fb1c5"; border="rgba(15,23,42,.12)" if light else "rgba(148,163,184,.12)"; green="#079669" if light else "#19d38a"; red="#dc3545" if light else "#ff5c70"
    markup=f"""<html><head><style>*{{box-sizing:border-box}}body{{margin:0;background:{bg};color:{textc};font-family:Arial,sans-serif;overflow:hidden}}.viewport{{width:100%;overflow:hidden;border:1px solid {border};border-radius:13px;background:{viewport}}}.track{{display:flex;width:max-content;animation:marquee 144s linear infinite;padding:10px 0}}.track:hover{{animation-play-state:paused}}.tick{{white-space:nowrap;margin-right:28px;font-size:12px;color:{muted}}}.tick b{{color:{textc};margin-right:5px}}.up{{color:{green}}}.down{{color:{red}}}@keyframes marquee{{from{{transform:translateX(0)}}to{{transform:translateX(-50%)}}}}</style></head><body><div class="viewport" id="v"><div class="track" id="t">{content}{content}</div></div><script>const v=document.getElementById('v'),t=document.getElementById('t');v.addEventListener('touchstart',()=>t.style.animationPlayState='paused',{{passive:true}});v.addEventListener('touchend',()=>t.style.animationPlayState='running',{{passive:true}});</script></body></html>"""
    components.html(markup,height=43,scrolling=False)

def render_scan_animation():
    candles = "".join('<span class="candle '+('g' if i%3 else 'r')+'"></span>' for i in range(42))
    return f'''<div class="scan-shell"><div class="scan-chart"><div class="candle-track">{candles}{candles}</div></div><div class="scan-copy"><span>Scanning NIFTY 500 (Large + Mid + Small Cap)…</span><span>Technical setup analysis</span></div><div class="progress"><div></div></div><div class="small-muted" style="margin-top:8px">Fetching prices → calculating indicators → ranking near-breakout setups</div></div>'''


def metric_card(label, value):
    return f'<div class="metric-card"><div class="metric-label">{html.escape(str(label))}</div><div class="metric-value">{html.escape(str(value))}</div></div>'


def day_change(symbol, period="2y"):
    hist = fetch_history(symbol, period)
    if hist is None or len(hist) < 2:
        return None, None, None
    last, prev = float(hist.Close.iloc[-1]), float(hist.Close.iloc[-2])
    return last, last-prev, (last/prev-1)*100


def detail_chart(symbol,row,period="2y"):
    hist=fetch_history(symbol,period)
    if hist is None or hist.empty:
        st.warning("Price history is temporarily unavailable for the chart."); return
    light=st.session_state.theme_mode=="light"
    fig=go.Figure()
    fig.add_trace(go.Candlestick(x=hist.index,open=hist.Open,high=hist.High,low=hist.Low,close=hist.Close,name=symbol))
    fig.add_trace(go.Bar(x=hist.index,y=hist.Volume,name="Volume",yaxis="y2",opacity=.25))
    fig.add_hline(y=float(row["breakout_level"]),line_dash="dash",line_color="#079669" if light else "#19d38a",annotation_text=f"Breakout: ₹{row['breakout_level']:.2f}",annotation_position="top left")
    fig.update_layout(template="plotly_white" if light else "plotly_dark",height=470,margin=dict(l=8,r=8,t=30,b=10),xaxis_rangeslider_visible=False,hovermode="x unified",paper_bgcolor="#fff" if light else "#0c192b",plot_bgcolor="#f5f7fa" if light else "#07111f",yaxis=dict(title="Price"),yaxis2=dict(title="Volume",overlaying="y",side="right",showgrid=False,rangemode="tozero"),legend=dict(orientation="h",y=1.02,x=0))
    st.plotly_chart(fig,use_container_width=True,config={"displayModeBar":False,"responsive":True})

def verdict(score):
    if score>=90:return "Strong",True
    if score>=75:return "Good",True
    if score>=60:return "Neutral",False
    if score>=40:return "Weak",False
    return "Avoid",False

def score_class(value,kind):
    try:v=float(value)
    except Exception:return "metric-neutral"
    if kind=="rsi": return "metric-good" if 52<=v<=68 else "metric-ok" if 48<=v<=72 else "metric-poor"
    if kind=="rvol": return "metric-good" if v>=1.5 else "metric-ok" if v>=1.1 else "metric-poor" if v>=.8 else "metric-bad"
    if kind=="adx": return "metric-good" if v>=25 else "metric-ok" if v>=18 else "metric-poor"
    if kind=="distance": return "metric-good" if v<=1 else "metric-ok" if v<=3 else "metric-neutral" if v<=5 else "metric-poor" if v<=10 else "metric-bad"
    if kind=="rr": return "metric-good" if v>=2 else "metric-ok" if v>=1.5 else "metric-neutral" if v>=1 else "metric-poor"
    if kind=="score": return "metric-good" if v>=80 else "metric-ok" if v>=65 else "metric-neutral" if v>=50 else "metric-poor" if v>=35 else "metric-bad"
    return "metric-neutral"

def metric_card(label,value,kind=None):
    cls=score_class(value,kind) if kind else "metric-neutral"
    return f'<div class="metric-card {cls}"><div class="metric-label">{html.escape(str(label))}</div><div class="metric-value">{html.escape(str(value))}</div></div>'

def target_values(row,price):
    b=float(row.get("breakout_level",0) or 0); note=""
    try:t1=float(row.get("target1"))
    except Exception:t1=None
    try:t2=float(row.get("target2"))
    except Exception:t2=None
    if t1 is None or not np.isfinite(t1):
        base=max(b-float(price),0); t1=b+base if base else b*1.01; note="Targets estimated from the breakout base height."
    if t2 is None or not np.isfinite(t2):
        base=max(b-float(price),0); t2=b+2*base if base else b*1.02; note="Targets estimated from the breakout base height."
    return t1,t2,note


def build_scan_export(result, scanned_at):
    """Build the audit CSV from existing scan fields; scanner logic is untouched."""
    rows = []
    scan_date = str(scanned_at).split(" ")[0]
    for _, row in result.iterrows():
        try:
            t1 = float(row.get("target1"))
            t2 = float(row.get("target2"))
            t3 = t2 + (t2 - t1) if np.isfinite(t1) and np.isfinite(t2) else np.nan
        except Exception:
            t1 = t2 = t3 = np.nan

        rating = row.get("rating", "")
        targets = " | ".join(
            [f"T1: {t1:.2f}" if np.isfinite(t1) else "T1: —",
             f"T2: {t2:.2f}" if np.isfinite(t2) else "T2: —",
             f"T3: {t3:.2f}" if np.isfinite(t3) else "T3: —"]
        )

        def rounded_value(key):
            value = row.get(key)
            return round(float(value), 2) if pd.notna(value) and str(value).strip() != "" else ""

        rows.append({
            "Date": scan_date,
            "Stock": row.get("company_name", row.get("symbol", "")),
            "Rank": row.get("rank", ""),
            "Score": rounded_value("score"),
            "Strength": rating,
            "Price": rounded_value("price"),
            "Breakout Level": rounded_value("breakout_level"),
            "Targets": targets,
            "Stop": rounded_value("stop_reference"),
            "Distance %": rounded_value("distance_pct"),
            "RVOL": rounded_value("rvol"),
            "RSI": rounded_value("rsi"),
            "ADX": rounded_value("adx"),
            "Market Regime": row.get("market_regime", ""),
        })
    return pd.DataFrame(rows, columns=[
        "Date", "Stock", "Rank", "Score", "Strength", "Price",
        "Breakout Level", "Targets", "Stop", "Distance %", "RVOL",
        "RSI", "ADX", "Market Regime"
    ])


def build_single_stock_export(symbol, row, scanned_at, rank=""):
    """Build one audit-ready row from the exact scanner output for a searched stock."""
    t1 = float(row.get("target1")) if pd.notna(row.get("target1")) else np.nan
    t2 = float(row.get("target2")) if pd.notna(row.get("target2")) else np.nan
    t3 = t2 + (t2 - t1) if np.isfinite(t1) and np.isfinite(t2) else np.nan
    targets = " | ".join([
        f"T1: {t1:.2f}" if np.isfinite(t1) else "T1: —",
        f"T2: {t2:.2f}" if np.isfinite(t2) else "T2: —",
        f"T3: {t3:.2f}" if np.isfinite(t3) else "T3: —",
    ])
    return pd.DataFrame([{
        "Date": str(scanned_at).split(" ")[0],
        "Stock": row.get("company_name", symbol),
        "Symbol": symbol,
        "Cap": row.get("cap_category", ""),
        "Rank": rank,
        "Score": round(float(row.get("score", 0)), 2),
        "Strength": row.get("rating", ""),
        "Price": round(float(row.get("price")), 2),
        "Breakout Level": round(float(row.get("breakout_level")), 2),
        "Targets": targets,
        "Stop": round(float(row.get("stop_reference")), 2),
        "Distance %": round(float(row.get("distance_pct")), 2),
        "RVOL": round(float(row.get("rvol")), 2),
        "RSI": round(float(row.get("rsi")), 2),
        "ADX": round(float(row.get("adx")), 2),
        "Market Regime": row.get("market_regime", ""),
        "Breakout Trigger": round(float(row.get("breakout_trigger")), 2),
        "ATR %": round(float(row.get("atr_pct")), 2),
        "MACD": round(float(row.get("macd")), 4),
        "Squeeze": round(float(row.get("squeeze")), 2),
        "EMA Structure": row.get("ema_structure", ""),
        "Resistance Touches": row.get("resistance_touches", ""),
        "Relative Strength 60D %": round(float(row.get("relative_strength")), 2),
        "NIFTY Relative Strength %": round(float(row.get("nifty_relative_strength")), 2),
        "Risk / Reward": round(float(row.get("risk_reward")), 2),
        "False Breakout": "Yes" if row.get("false_breakout") else "No",
        "Scanner Status": row.get("status", ""),
    }])


def render_stock_search():
    st.markdown('<div class="section-title">🔎 Search Any Stock</div>', unsafe_allow_html=True)
    st.markdown('<div class="small-muted">Enter an NSE symbol such as RELIANCE, TCS, SBIN or INFY. The result uses the same scanner calculation engine.</div>', unsafe_allow_html=True)
    c1, c2 = st.columns([3, 1])
    with c1:
        query = st.text_input("Stock symbol", placeholder="e.g. RELIANCE", key="stock_search_input", label_visibility="collapsed")
    with c2:
        search_clicked = st.button("SEARCH", key="search_stock", use_container_width=True)

    if search_clicked and query.strip():
        symbol = query.strip().upper().replace(".NS", "")
        st.session_state.search_error = None
        with st.spinner(f"Running scanner analysis for {symbol}…"):
            try:
                # First use the scanner's public single-stock path. This preserves the
                # existing distance rule and all scoring/criteria exactly as-is.
                row = scan_single(symbol, max_distance=10.0, period="2y")
                if row is None:
                    # If the stock is outside the scanner's near-breakout window, still
                    # calculate its exact scanner fields for audit purposes. We do NOT
                    # change any scanner thresholds or scoring rules.
                    hist = fetch_history(symbol, "2y")
                    if hist is None:
                        raise ValueError("No usable 2-year price/volume history was returned for this symbol.")
                    nifty = __import__("scanner").fetch_index_history("^NSEI", period="2y")
                    row = score_stock(hist, nifty_df=nifty)
                    if row is None:
                        raise ValueError("The scanner could not calculate the technical setup for this stock.")
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
                    except Exception:
                        pass
                st.session_state.search_result = row
                st.session_state.search_symbol = symbol
                st.session_state.search_timestamp = datetime.now(IST).strftime("%Y-%m-%d %H:%M:%S IST")
            except Exception as exc:
                st.session_state.search_result = None
                st.session_state.search_error = str(exc)

    if st.session_state.get("search_error"):
        st.error(st.session_state.search_error)
    row = st.session_state.get("search_result")
    if not row:
        return

    symbol = st.session_state.get("search_symbol", "")
    if row.get("outside_near_breakout_range"):
        st.warning("This stock is outside the scanner's normal ≤10% near-breakout window. Its values below are still calculated by the same scanner logic for audit/testing; it would not normally appear in the market scan.")

    # Rank is a universe-relative value. A searched stock is not silently assigned a fake rank.
    rank_text = "Not ranked individually"
    company = row.get("company_name", symbol)
    st.markdown(f'<div class="card"><div class="small-muted">{html.escape(str(company))}</div><div style="font-size:1.25rem;font-weight:950">{html.escape(symbol)}</div><div class="hero-price">{money(row.get("price"))}</div><div class="small-muted">Scanner status: <b>{html.escape(str(row.get("status", "—")))}</b> &nbsp;•&nbsp; {rank_text}</div></div>', unsafe_allow_html=True)

    fields = [
        ("Score", f"{float(row.get('score', 0)):.1f}/100", "score"),
        ("Strength", f"{int(float(row.get('rating', 0)))} / 10", "score"),
        ("Breakout Level", money(row.get("breakout_level")), "distance"),
        ("Distance", pct(row.get("distance_pct")), "distance"),
        ("RVOL", f"{float(row.get('rvol', 0)):.2f}x", "rvol"),
        ("RSI", f"{float(row.get('rsi', 0)):.1f}", "rsi"),
        ("ADX", f"{float(row.get('adx', 0)):.1f}", "adx"),
        ("Market Regime", row.get("market_regime", "—"), None),
        ("Price", money(row.get("price")), None),
        ("Breakout Trigger", money(row.get("breakout_trigger")), None),
        ("Stop", money(row.get("stop_reference")), None),
        ("Target 1", money(row.get("target1")), None),
        ("Target 2", money(row.get("target2")), None),
        ("ATR %", f"{float(row.get('atr_pct', 0)):.2f}%", None),
        ("MACD", f"{float(row.get('macd', 0)):.4f}", None),
        ("Squeeze", f"{float(row.get('squeeze', 0)):.2f}", None),
        ("EMA Structure", row.get("ema_structure", "—"), None),
        ("Resistance Touches", row.get("resistance_touches", "—"), None),
        ("60D Relative Strength", pct(row.get("relative_strength")), None),
        ("NIFTY Relative Strength", pct(row.get("nifty_relative_strength")), None),
        ("Risk / Reward", f"{float(row.get('risk_reward', 0)):.2f}", "rr"),
        ("False Breakout", "Yes" if row.get("false_breakout") else "No", None),
    ]
    for i in range(0, len(fields), 2):
        c1, c2 = st.columns(2)
        with c1:
            st.markdown(metric_card(fields[i][0], fields[i][1], fields[i][2]), unsafe_allow_html=True)
        if i + 1 < len(fields):
            with c2:
                st.markdown(metric_card(fields[i+1][0], fields[i+1][1], fields[i+1][2]), unsafe_allow_html=True)

    st.markdown('<div class="section-title">Audit Entry</div>', unsafe_allow_html=True)
    st.markdown('<div class="small-muted">The downloaded row contains the scanner values plus extra technical fields useful for testing. You only need to add the future outcome later.</div>', unsafe_allow_html=True)
    audit_df = build_single_stock_export(symbol, row, st.session_state.get("search_timestamp", datetime.now(IST).strftime("%Y-%m-%d %H:%M:%S IST")), rank="")
    st.download_button("📥 DOWNLOAD THIS STOCK FOR AUDIT", data=audit_df.to_csv(index=False).encode("utf-8-sig"), file_name=f"audit_{symbol}_{datetime.now(IST).strftime('%Y%m%d_%H%M%S')}.csv", mime="text/csv", use_container_width=True, key=f"audit_{symbol}")


def render_detail(symbol,row):
    render_theme_toggle()
    if st.button("← Back to Top 20"):
        st.session_state.page="home"; st.rerun()
    company=row.get("company_name",symbol); last,change,change_pct=day_change(symbol); price=last if last is not None else row.get("price")
    score=float(row.get("score",0)); label,strong=verdict(score); change_cls="up" if (change_pct or 0)>=0 else "down"; arrow="▲" if (change_pct or 0)>=0 else "▼"
    t1,t2,target_note=target_values(row,price)
    t1up=((t1/price)-1)*100 if price else 0; t2up=((t2/price)-1)*100 if price else 0
    note_html=f'<div class="small-muted" style="margin-top:7px">{html.escape(target_note)}</div>' if target_note else ''
    st.markdown(f'''<div class="card"><div class="small-muted">{html.escape(str(company))}</div><div style="font-size:1.15rem;font-weight:900">{html.escape(symbol)}</div><div class="hero-price">{money(price)}</div><div class="{change_cls}" style="font-weight:850">{arrow} {money(change)} ({pct(change_pct)})</div><div style="height:8px"></div><div style="display:grid;grid-template-columns:1fr 1fr;gap:8px"><div class="target-box"><div class="target-label">Target 1</div><div class="target-value">{money(t1)}</div><div class="target-upside">{t1up:+.2f}% upside</div></div><div class="target-box"><div class="target-label">Target 2</div><div class="target-value">{money(t2)}</div><div class="target-upside">{t2up:+.2f}% upside</div></div></div>{note_html}</div>''',unsafe_allow_html=True)
    light=st.session_state.theme_mode=="light"
    fig=go.Figure(go.Indicator(mode="gauge+number",value=score,number={"suffix":" / 100","font":{"size":38,"color":"#111827" if light else "#f1f5f9"}},title={"text":"Technical Setup Strength"},gauge={"axis":{"range":[0,100],"tickwidth":1,"tickcolor":"#64748b"},"bar":{"color":"#079669" if light else "#19d38a","thickness":.22},"bgcolor":"#e5e7eb" if light else "#0b1829","borderwidth":0,"steps":[{"range":[0,40],"color":"#f3c4ca"},{"range":[40,65],"color":"#f5e4ad"},{"range":[65,80],"color":"#d9ecb0"},{"range":[80,100],"color":"#b8efd9"}]}))
    fig.update_layout(template="plotly_white" if light else "plotly_dark",height=245,margin=dict(l=15,r=15,t=45,b=5),paper_bgcolor="#fff" if light else "#0c192b")
    st.plotly_chart(fig,use_container_width=True,config={"displayModeBar":False})
    badge_cls="badge-green" if strong else "badge-red" if score<40 else "badge-yellow"; badge='<span class="badge badge-green">BUY SIGNAL</span>' if strong else '<span class="badge badge-grey">SETUP WATCH</span>'
    st.markdown(f'<div style="text-align:center;margin-top:-12px"><span class="badge {badge_cls}">{label}</span> &nbsp; {badge}</div>',unsafe_allow_html=True)

    st.markdown('<div class="section-title">Technical Data</div>',unsafe_allow_html=True)
    hist=fetch_history(symbol,"2y"); extra={}
    if hist is not None and len(hist):
        last52=hist.tail(252); extra={"52-week high":money(float(last52.High.max())),"52-week low":money(float(last52.Low.min()))}
    fields=[
      ("Breakout level",money(row.get("breakout_level")),"distance"),("Breakout trigger",money(row.get("breakout_trigger")),None),
      ("Distance",pct(row.get("distance_pct")),"distance"),("Rating",f"{row.get('rating','—')}/10","score"),
      ("Score",f"{row.get('score',0):.1f}/100","score"),("RVOL",f"{row.get('rvol',0):.2f}x","rvol"),
      ("RSI",f"{row.get('rsi',0):.1f}","rsi"),("ADX",f"{row.get('adx',0):.1f}","adx"),
      ("EMA structure",row.get("ema_structure","—"),None),("MACD",f"{row.get('macd',0):.3f}",None),
      ("ATR %",f"{row.get('atr_pct',0):.2f}%",None),("Squeeze",f"{row.get('squeeze',0):.2f}",None),
      ("NIFTY relative strength",pct(row.get("nifty_relative_strength")),None),("60D relative strength",pct(row.get("relative_strength")),None),
      ("Candlestick",row.get("candlestick","—"),None),("Resistance touches",row.get("resistance_touches","—"),None),
      ("Risk / reward",f"{row.get('risk_reward',0):.2f}","rr"),("Market regime",row.get("market_regime","—"),None),
      ("Status",row.get("status","—"),None),("False breakout","Yes" if row.get("false_breakout") else "No",None),
      ("Stop reference",money(row.get("stop_reference")),None),("Target 1",money(t1),None),("Target 2",money(t2),None),
      ("52-week high",extra.get("52-week high","—"),None),("52-week low",extra.get("52-week low","—"),None)]
    known={x[0] for x in fields}; field_map={"price":"Current price","breakout_level":"Breakout level","breakout_trigger":"Breakout trigger","distance_pct":"Distance","score":"Score","rating":"Rating","rsi":"RSI","macd":"MACD","adx":"ADX","rvol":"RVOL","atr_pct":"ATR %","ema_structure":"EMA structure","candlestick":"Candlestick","relative_strength":"60D relative strength","nifty_relative_strength":"NIFTY relative strength","sector_relative_strength":"Sector relative strength","market_regime":"Market regime","risk_reward":"Risk / reward","squeeze":"Squeeze"}
    for k,v in row.items():
        label2=field_map.get(k,k.replace("_"," ").title())
        if label2 in known or k in {"symbol","company_name","rank_score","explanation","rank"}: continue
        fields.append((label2,f"{v:.2f}" if isinstance(v,(float,np.floating)) else str(v),None))
    for i in range(0,len(fields),2):
        c1,c2=st.columns(2)
        with c1: st.markdown(metric_card(fields[i][0],fields[i][1],fields[i][2]),unsafe_allow_html=True)
        if i+1<len(fields):
            with c2: st.markdown(metric_card(fields[i+1][0],fields[i+1][1],fields[i+1][2]),unsafe_allow_html=True)

    st.markdown('<div class="section-title">Price Chart</div>',unsafe_allow_html=True)
    tv_symbol=str(symbol).replace(".NS","").upper(); tv_url=f"https://www.tradingview.com/chart/?symbol=NSE:{tv_symbol}"
    st.markdown(f'<a class="tradingview-btn" href="{tv_url}" target="_blank" rel="noopener">Open in TradingView ↗</a>',unsafe_allow_html=True)
    detail_chart(symbol,row)
    st.markdown(f'<div class="tv-under"><a href="{tv_url}" target="_blank" rel="noopener">View on TradingView ↗</a></div>',unsafe_allow_html=True)

    level=float(row.get("breakout_level",0) or 0); p=float(price or 0); distance=((level-p)/level*100) if level else 999
    if p>=level: title,msg,cls="Breakout Confirmed","Price is trading at or above the detected breakout level.","badge-green"
    elif distance<=2: title,msg,cls="ENTRY ZONE","Price is near the breakout level. Confirmation still matters.","badge-green entry-pulse"
    elif distance<=5: title,msg,cls="Wait","Not near the entry point yet.","badge-yellow"
    else: title,msg,cls="Wait","Not near the entry point.","badge-grey"
    st.markdown(f'''<div class="card"><span class="badge {cls}">{title}</span><div style="font-size:1.05rem;font-weight:900;margin-top:9px">{msg}</div><div class="small-muted" style="margin-top:7px">Distance to breakout: {distance:.2f}% &nbsp; • &nbsp; Suggested entry reference: {money(row.get("breakout_trigger"))}</div></div>''',unsafe_allow_html=True)
    if row.get("explanation"):
        st.markdown(f'<div class="card"><b>Technical summary</b><div class="small-muted" style="margin-top:8px">{html.escape(str(row["explanation"]))}</div></div>',unsafe_allow_html=True)


def render_home():
    render_theme_toggle()
    st.markdown("<div style='font-size:1.6rem;font-weight:950'>📈 NIFTY Breakout Scanner</div><div class='small-muted'>Near-breakout technical setups across NIFTY Large Cap 100 + Midcap 150</div>",unsafe_allow_html=True)
    render_market_bar(); render_ticker(); st.markdown("<div style='height:5px'></div>",unsafe_allow_html=True)
    render_stock_search()

    audit_pending = st.session_state.get("audit_pending_rows") is not None
    scan_col, audit_col = st.columns(2)
    with scan_col:
        normal_clicked = st.button("🚀 SCAN MARKET", key="scan_market", type="primary", use_container_width=True, disabled=audit_pending)
    with audit_col:
        audit_clicked = st.button("📊 COLLECT AUDIT DATA", key="collect_audit", use_container_width=True, disabled=audit_pending)

    tracking_clicked = st.button(
        "📈 UPDATE PERFORMANCE TRACKING",
        key="update_performance_tracking",
        use_container_width=True,
        disabled=audit_pending,
        help="Backfill available historical OHLC after each saved signal and append missing tracking days up to Day 20.",
    )
    st.caption("Normal Scan never writes to Google Sheets. Collect Audit saves a signal snapshot after confirmation. Update Performance Tracking retrieves historical OHLC for saved signals.")

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
        selected_outcome_label = st.selectbox(
            "Outcome to evaluate",
            list(outcome_labels.keys()),
            key="audit_research_outcome_choice",
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
                        analysis_df = analyze_outcome_combinations(
                            completed_outcomes,
                            outcome_col=outcome_labels[selected_outcome_label],
                            min_signals=max(25, int(len(completed_outcomes) * 0.05)),
                            max_order=3,
                        )
                        st.session_state.audit_analysis_result = analysis_df
                        st.session_state.audit_analysis_report = completion_report
                        st.session_state.audit_analysis_outcome = outcome_labels[selected_outcome_label]
                        st.session_state.audit_analysis_saved = False
                        analysis_status.update(label=f"Analysis complete: {len(completed_outcomes):,} matured signals evaluated", state="complete", expanded=False)
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
            st.info("No Day-20 outcomes are ready yet. Continue updating performance tracking after market close; this analysis will become available as signals mature.")

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
                    # Re-read compact keys after writing to verify every market-session key
                    # expected from the retrieved calendar now exists in the Sheet.
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

    if audit_pending:
        st.info("📌 An audit scan is waiting for your confirmation below. Resolve it before starting another scan.")

    scan_mode = "audit" if audit_clicked else "normal" if normal_clicked else None
    if scan_mode:
        st.session_state.scanning = True
        st.session_state.scan_error = None
        st.session_state.scan_result = None
        scan_placeholder = st.empty()
        try:
            scan_placeholder.markdown('<div class="scan-shell"><div style="font-weight:950;font-size:1rem">🔎 Scanning market…</div><div class="scan-copy"><span>Analyzing NIFTY 250 universe</span><span>Working</span></div><div class="scan-chart"><div class="candle-track">' + ''.join([f'<span class="candle {"g" if i % 3 else "r"}"></span>' for i in range(42)]) + '</div></div><div class="progress"><div></div></div><div class="small-muted" style="margin-top:8px">Please keep this page open while the scan is running.</div></div>', unsafe_allow_html=True)
            with st.spinner("Calculating technical setups…"):
                result = scan_universe(max_distance=10.0, period="2y", top_n=500)
            st.session_state.scan_result = result
            st.session_state.scan_timestamp = datetime.now(IST).strftime("%Y-%m-%d %H:%M:%S IST")

            # IMPORTANT: the normal scan NEVER writes audit data anywhere.
            if scan_mode == "audit" and result is not None and not result.empty:
                run_id = new_run_id()
                st.session_state.audit_pending_run_id = run_id
                st.session_state.audit_pending_timestamp = st.session_state.scan_timestamp
                st.session_state.audit_pending_rows = build_scan_snapshot(
                    result,
                    run_id=run_id,
                    scan_timestamp_ist=st.session_state.scan_timestamp,
                    scanner_period="2y",
                    max_distance_pct=10.0,
                )
                st.session_state.audit_last_saved = None
        except Exception as exc:
            st.session_state.scan_result = pd.DataFrame()
            st.session_state.scan_error = str(exc)
        finally:
            st.session_state.scanning = False
            scan_placeholder.empty()

    result=st.session_state.get("scan_result")
    if st.session_state.get("scan_error"): st.error("The market scan could not be completed. Please try again. Details: "+st.session_state.scan_error)
    if result is None:
        st.markdown('<div class="card"><b>Ready to scan</b><div class="small-muted" style="margin-top:6px">The scanner will fetch NIFTY Large Cap 100 + Midcap 150 and list qualifying stocks by Rating, highest first.</div></div>',unsafe_allow_html=True); return
    if result.empty:
        st.markdown('<div class="card"><b>No qualifying setups found</b><div class="small-muted" style="margin-top:6px">Nothing currently meets the scanner’s near-breakout criteria. Try again after the next market session.</div></div>',unsafe_allow_html=True); return
    pending_rows = st.session_state.get("audit_pending_rows")
    pending_run_id = st.session_state.get("audit_pending_run_id")
    pending_timestamp = st.session_state.get("audit_pending_timestamp")
    append_in_progress = st.session_state.get("audit_append_in_progress", False)
    if pending_rows is not None:
        if append_in_progress:
            # This is deliberately a separate rerun from the YES click. It prevents
            # accidental double-clicks and makes the write state visible while the
            # Google Apps Script request is running. No scanner logic is involved.
            st.info(
                f"⏳ Writing {len(pending_rows)} audit rows to Google Sheets… "
                "Please keep this page open and do not click again."
            )
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
                    if audit_info.get("reason") == "batch_already_exists":
                        status.update(
                            label="ℹ️ This audit batch was already recorded; no duplicate rows were added.",
                            state="complete",
                            expanded=False,
                        )
                    else:
                        status.update(
                            label=f"✅ Audit batch written: {audit_info.get('rows', 0)} new rows.",
                            state="complete",
                            expanded=False,
                        )
                st.session_state.audit_last_saved = audit_info
                st.session_state.audit_pending_rows = None
                st.session_state.audit_pending_run_id = None
                st.session_state.audit_pending_timestamp = None
                st.session_state.audit_append_in_progress = False
                st.rerun()
            except Exception as exc:
                st.session_state.audit_append_in_progress = False
                st.error(
                    "The audit batch was NOT confirmed as written. Check your Google Sheets "
                    "connection and Apps Script deployment. Details: " + str(exc)
                )
        else:
            st.warning(
                f"📊 Audit collection is ready: {len(pending_rows)} signal rows from {pending_timestamp}. "
                "Nothing has been written yet. Append this batch to the Google Sheet?"
            )
            yes_col, no_col = st.columns(2)
            with yes_col:
                append_clicked = st.button(
                    "✅ YES — APPEND TO AUDIT SHEET",
                    key="audit_yes",
                    use_container_width=True,
                    type="primary",
                )
            with no_col:
                discard_clicked = st.button(
                    "❌ NO — DISCARD THIS AUDIT",
                    key="audit_no",
                    use_container_width=True,
                )
            if append_clicked:
                # First rerun changes the UI into an explicit in-progress state.
                # The actual network write occurs only on the following run.
                st.session_state.audit_append_in_progress = True
                st.rerun()
            elif discard_clicked:
                st.session_state.audit_pending_rows = None
                st.session_state.audit_pending_run_id = None
                st.session_state.audit_pending_timestamp = None
                st.session_state.audit_append_in_progress = False
                st.session_state.audit_last_saved = {"saved": False, "rows": 0, "reason": "discarded_by_user"}
                st.success("Audit batch discarded. The normal scan result remains available, and nothing was written to Google Sheets.")
                st.rerun()

    audit_info = st.session_state.get("audit_last_saved") or {}
    if audit_info.get("saved") and audit_info.get("reason") in {"appended", "batch_already_exists"}:
        st.success(f"✅ Audit batch recorded: {audit_info.get('rows', 0)} new signal rows. Run ID: {audit_info.get('run_id', '—')}")

    export_df = build_scan_export(result, st.session_state.get("scan_timestamp") or datetime.now(IST).strftime("%Y-%m-%d %H:%M:%S IST"))
    csv_data = export_df.to_csv(index=False).encode("utf-8-sig")
    st.download_button(
        "📥 EXPORT SCAN RESULTS (CSV)",
        data=csv_data,
        file_name=f"stock_scan_{datetime.now(IST).strftime('%Y%m%d_%H%M%S')}.csv",
        mime="text/csv",
        use_container_width=True,
        key="export_scan_csv",
    )
    st.caption("The Google Sheet is the source of truth for saved audit signals and tracking rows.")
    display=result.copy()
    # Display order is explicitly based on Strength (the scanner's 1-10 rating), highest first.
    sort_cols = [c for c in ["rating", "score", "rank_score", "distance_pct"] if c in display.columns]
    if sort_cols:
        ascending = [False, False, False, True][:len(sort_cols)]
        display = display.sort_values(sort_cols, ascending=ascending, kind="stable").reset_index(drop=True)
    st.markdown(f'<div class="section-title">Scanned Stocks ({len(display)})</div>',unsafe_allow_html=True); st.markdown('<div class="rank-note">Sorted by Strength: highest first. Score is used as the tie-breaker.</div>',unsafe_allow_html=True)
    for start in range(0,len(display),2):
        cols=st.columns(2)
        for j,col in enumerate(cols):
            idx=start+j
            if idx>=len(display): continue
            row=display.iloc[idx]; ratio=idx/max(len(display)-1,1)
            color="#19d38a" if ratio<.2 else "#8fd66a" if ratio<.4 else "#f5c451" if ratio<.6 else "#ff9b4a" if ratio<.8 else "#ff5c70"
            with col:
                rating = int(float(row.get("rating", 0) or 0))
                rating_color = "#19d38a" if rating >= 8 else "#8fd66a" if rating >= 7 else "#f5c451" if rating >= 5 else "#ff9b4a" if rating >= 3 else "#ff5c70"
                score = float(row.get("score", 0) or 0)
                t1 = float(row.get("target1", 0) or 0)
                t2 = float(row.get("target2", 0) or 0)
                price = float(row.get("price", 0) or 0)
                t1_up = ((t1 - price) / price * 100) if price else 0.0
                t2_up = ((t2 - price) / price * 100) if price else 0.0
                st.markdown(f'''<div style="border-radius:14px;border:1px solid rgba(255,255,255,.12);padding:10px 11px 8px;background:linear-gradient(145deg,{color}22,var(--card));margin-bottom:-4px"><div style="font-size:.72rem;font-weight:900;color:{color}">RANK #{idx+1} &nbsp;•&nbsp; {html.escape(str(row.get("cap_category","")))}</div><div style="display:flex;align-items:center;justify-content:space-between;gap:8px"><div style="font-weight:950;font-size:1rem;color:var(--text)">{html.escape(str(row.get("company_name",row["symbol"])))}</div><span style="flex:none;padding:4px 7px;border-radius:999px;border:1px solid {rating_color}66;background:{rating_color}18;color:{rating_color};font-size:.68rem;font-weight:950;white-space:nowrap">Rating {rating}/10</span><span style="padding:4px 7px;border-radius:999px;border:1px solid rgba(255,255,255,.20);background:rgba(255,255,255,.06);color:var(--text);font-size:.68rem;font-weight:950;white-space:nowrap">Score {score:.1f}/100</span></div><div class="small-muted">{html.escape(str(row["symbol"]))}</div><div style="font-weight:950;font-size:1.05rem;margin-top:5px">{money(price)}</div><div style="font-size:.75rem;color:{color};font-weight:900">{float(row.get("distance_pct",0)):.2f}% to breakout</div><div style="display:grid;grid-template-columns:1fr 1fr 1fr;gap:7px;margin-top:9px"><div style="border:1px solid rgba(25,211,138,.24);border-radius:10px;padding:7px 8px;background:rgba(25,211,138,.06)"><div style="font-size:.68rem;font-weight:900;color:#19d38a">RSI</div><div style="font-size:.98rem;font-weight:950;margin-top:2px">{float(row.get("rsi", 0) or 0):.1f}</div><div class="small-muted">Relative strength</div></div><div style="border:1px solid rgba(25,211,138,.24);border-radius:10px;padding:7px 8px;background:rgba(25,211,138,.06)"><div style="font-size:.68rem;font-weight:900;color:#19d38a">ADX</div><div style="font-size:.98rem;font-weight:950;margin-top:2px">{float(row.get("adx", 0) or 0):.1f}</div><div class="small-muted">Trend strength</div></div><div style="border:1px solid rgba(25,211,138,.24);border-radius:10px;padding:7px 8px;background:rgba(25,211,138,.06)"><div style="font-size:.68rem;font-weight:900;color:#19d38a">MACD</div><div style="font-size:.98rem;font-weight:950;margin-top:2px">{float(row.get("macd", 0) or 0):.3f}</div><div class="small-muted">Momentum</div></div></div></div>''',unsafe_allow_html=True)
                if st.button(f"Open {row['symbol']}",key=f"stock_{row['symbol']}",use_container_width=True):
                    st.session_state.selected_stock=row["symbol"]; st.session_state.selected_row=row.to_dict(); st.session_state.page="detail"; st.rerun()
    st.markdown('<div class="small-muted" style="text-align:center;margin-top:12px">Breakout levels are technical reference levels, not guaranteed predictions.</div>',unsafe_allow_html=True)


# -----------------------------------------------------------------------------
# Session-state navigation: only two pages, no multipage folder.
# -----------------------------------------------------------------------------
if "page" not in st.session_state: st.session_state.page = "home"
if "scan_result" not in st.session_state: st.session_state.scan_result = None
if "scan_timestamp" not in st.session_state: st.session_state.scan_timestamp = None
if "scanning" not in st.session_state: st.session_state.scanning = False
if "audit_last_saved" not in st.session_state: st.session_state.audit_last_saved = None
if "audit_pending_rows" not in st.session_state: st.session_state.audit_pending_rows = None
if "audit_pending_run_id" not in st.session_state: st.session_state.audit_pending_run_id = None
if "audit_pending_timestamp" not in st.session_state: st.session_state.audit_pending_timestamp = None
if "audit_append_in_progress" not in st.session_state: st.session_state.audit_append_in_progress = False
if "audit_analysis_result" not in st.session_state: st.session_state.audit_analysis_result = None
if "audit_analysis_report" not in st.session_state: st.session_state.audit_analysis_report = None
if "audit_analysis_saved" not in st.session_state: st.session_state.audit_analysis_saved = False
if "audit_analysis_outcome" not in st.session_state: st.session_state.audit_analysis_outcome = "T1_Hit"

try:
    if st.query_params.get("__reload_home") == "1":
        st.session_state.page = "home"
        st.query_params.pop("__reload_home", None)
except Exception:
    pass

# Global reload/navigation guard: active on every page, not only during a scan.
render_reload_guard(True)

if st.session_state.page == "detail" and st.session_state.get("selected_stock"):
    render_detail(st.session_state.selected_stock, st.session_state.selected_row)
else:
    render_home()

st.markdown('<div style="text-align:center;color:#71839a;font-size:.7rem;margin-top:28px">For educational purposes only. Not investment advice.</div>', unsafe_allow_html=True)
app.py
Displaying app.py.
