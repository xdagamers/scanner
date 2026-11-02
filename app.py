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
    if kind=="rsi": return "metric
