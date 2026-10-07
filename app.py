import io
import json
import html
import time
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
from audit_logger import build_scan_snapshot, read_signal_audit
from google_sheets_audit import append_audit_batch, new_run_id

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
    # Download the complete accumulated audit history, not just today's scan.
    audit_df = read_signal_audit()
    if not audit_df.empty:
        st.download_button(
            f"📊 DOWNLOAD FULL AUDIT LOG ({len(audit_df)} signals)",
            data=audit_df.to_csv(index=False).encode("utf-8-sig"),
            file_name="scanner_audit_signals.csv",
            mime="text/csv",
            use_container_width=True,
            key="download_full_audit_log",
        )
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
                st.markdown(f'''<div style="border-radius:14px;border:1px solid rgba(255,255,255,.12);padding:10px 11px 8px;background:linear-gradient(145deg,{color}22,var(--card));margin-bottom:-4px"><div style="font-size:.72rem;font-weight:900;color:{color}">RANK #{idx+1} &nbsp;•&nbsp; {html.escape(str(row.get("cap_category","")))}</div><div style="display:flex;align-items:center;justify-content:space-between;gap:8px"><div style="font-weight:950;font-size:1rem;color:var(--text)">{html.escape(str(row.get("company_name",row["symbol"])))}</div><span style="flex:none;padding:4px 7px;border-radius:999px;border:1px solid {rating_color}66;background:{rating_color}18;color:{rating_color};font-size:.68rem;font-weight:950;white-space:nowrap">Rating {rating}/10</span><span style="padding:4px 7px;border-radius:999px;border:1px solid rgba(255,255,255,.20);background:rgba(255,255,255,.06);color:var(--text);font-size:.68rem;font-weight:950;white-space:nowrap">Score {score:.1f}/100</span></div><div class="small-muted">{html.escape(str(row["symbol"]))}</div><div style="font-weight:950;font-size:1.05rem;margin-top:5px">{money(price)}</div><div style="font-size:.75rem;color:{color};font-weight:900">{float(row.get("distance_pct",0)):.2f}% to breakout</div><div style="display:grid;grid-template-columns:1fr 1fr;gap:7px;margin-top:9px"><div style="border:1px solid rgba(25,211,138,.24);border-radius:10px;padding:7px 8px;background:rgba(25,211,138,.06)"><div style="font-size:.68rem;font-weight:900;color:#19d38a">TARGET 1</div><div style="font-size:.98rem;font-weight:950;margin-top:2px">{money(t1)}</div><div class="small-muted">+{t1_up:.2f}% from price</div></div><div style="border:1px solid rgba(25,211,138,.24);border-radius:10px;padding:7px 8px;background:rgba(25,211,138,.06)"><div style="font-size:.68rem;font-weight:900;color:#19d38a">TARGET 2</div><div style="font-size:.98rem;font-weight:950;margin-top:2px">{money(t2)}</div><div class="small-muted">+{t2_up:.2f}% from price</div></div></div></div>''',unsafe_allow_html=True)
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
