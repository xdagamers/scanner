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
