import io
import json
import html
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, time as dtime
from zoneinfo import ZoneInfo

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import requests
import streamlit as st
import streamlit.components.v1 as components
import yfinance as yf
from fpdf import FPDF

# IMPORTANT: scanner.py is the existing engine. This UI only calls its existing functions.
from scanner import load_universe, scan_universe, scan_single, fetch_history

IST = ZoneInfo("Asia/Kolkata")
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
:root {
  --bg: #07111f;
  --card: #0c192b;
  --card2: #101f33;
  --border: rgba(148,163,184,.15);
  --text: #f1f5f9;
  --muted: #8fa3ba;
  --green: #19d38a;
  --green2: #0ea66b;
  --red: #ff5c70;
  --yellow: #f5c451;
  --blue: #4da3ff;
}
html, body, [data-testid="stAppViewContainer"] { background: var(--bg) !important; color: var(--text) !important; }
[data-testid="stHeader"], footer, #MainMenu { visibility: hidden !important; height: 0 !important; }
[data-testid="stToolbar"] { display: none !important; }
.block-container { max-width: 720px !important; padding: 1rem .75rem 5rem !important; }
section[data-testid="stSidebar"] { display: none !important; }
* { box-sizing: border-box; }
.stButton > button {
  width: 100%; border-radius: 14px; border: 1px solid var(--border);
  background: var(--card); color: var(--text); min-height: 46px;
  font-weight: 700; transition: .18s ease; box-shadow: none;
}
.stButton > button:hover { border-color: rgba(25,211,138,.55); transform: translateY(-1px); }
.scan-btn .stButton > button {
  min-height: 58px; border: 0; color: white;
  background: linear-gradient(135deg,#10b981,#0ea5e9);
  box-shadow: 0 12px 30px rgba(16,185,129,.20);
  font-size: 1.08rem;
}
.card {
  background: linear-gradient(145deg, rgba(16,31,51,.98), rgba(8,21,36,.98));
  border: 1px solid var(--border); border-radius: 18px; padding: 14px;
  margin: 8px 0; box-shadow: 0 8px 28px rgba(0,0,0,.16);
}
.status-card { padding: 10px 12px; border-radius: 15px; background:#0b1829; border:1px solid var(--border); }
.status-row { display:flex; align-items:center; justify-content:space-between; gap:10px; }
.status-left { display:flex; align-items:center; gap:8px; font-weight:800; }
.dot { width:9px; height:9px; border-radius:50%; display:inline-block; box-shadow:0 0 12px currentColor; }
.dot.green { background:var(--green); color:var(--green); animation:pulse 1.5s infinite; }
.dot.red { background:var(--red); color:var(--red); animation:pulse 1.5s infinite; }
.dot.yellow { background:var(--yellow); color:var(--yellow); animation:pulse 1.5s infinite; }
.index-wrap { display:flex; gap:12px; justify-content:flex-end; flex-wrap:wrap; }
.index-item { font-size:.82rem; color:var(--muted); }
.index-item b { color:var(--text); font-size:.9rem; }
.up { color:var(--green) !important; } .down { color:var(--red) !important; }
.section-title { font-size:1.2rem; font-weight:850; margin:18px 2px 10px; }
.stock-btn { text-align:left !important; }
.stock-rank { color:var(--green); font-weight:900; margin-right:7px; }
.stock-name { font-weight:800; } .stock-meta { color:var(--muted); font-size:.78rem; }
.metric-card { min-height:76px; padding:11px; border-radius:14px; background:#0b1829; border:1px solid var(--border); }
.metric-label { color:var(--muted); font-size:.72rem; text-transform:uppercase; letter-spacing:.04em; }
.metric-value { color:var(--text); font-weight:850; font-size:1rem; margin-top:4px; word-break:break-word; }
.hero-price { font-size:2.15rem; font-weight:900; letter-spacing:-.03em; }
.badge { display:inline-block; padding:5px 9px; border-radius:999px; font-size:.72rem; font-weight:900; }
.badge-green { background:rgba(25,211,138,.13); color:var(--green); border:1px solid rgba(25,211,138,.25); }
.badge-red { background:rgba(255,92,112,.12); color:var(--red); border:1px solid rgba(255,92,112,.25); }
.badge-grey { background:rgba(148,163,184,.10); color:#aab9ca; border:1px solid var(--border); }
.entry-pulse { animation: glow 1.35s ease-in-out infinite alternate; }
@keyframes pulse { 50% { opacity:.45; transform:scale(.75); } }
@keyframes glow { from { box-shadow:0 0 4px rgba(25,211,138,.1); } to { box-shadow:0 0 20px rgba(25,211,138,.45); } }
.scan-shell { background:#06101d; border:1px solid var(--border); border-radius:18px; padding:16px; overflow:hidden; }
.scan-chart { height:145px; position:relative; overflow:hidden; border-radius:12px; background:linear-gradient(180deg,#081626,#06101a); }
.candle-track { position:absolute; inset:0; display:flex; align-items:center; gap:10px; width:max-content; animation:scrollCandles 7s linear infinite; }
.candle { width:7px; position:relative; border-radius:2px; flex:none; box-shadow:0 0 8px currentColor; }
.candle:before { content:""; position:absolute; left:2px; width:2px; top:-13px; bottom:-13px; background:currentColor; opacity:.85; }
.candle.g { height:55px; background:#19d38a; color:#19d38a; } .candle.r { height:38px; background:#ff5c70; color:#ff5c70; }
@keyframes scrollCandles { from { transform:translateX(0); } to { transform:translateX(-50%); } }
.scan-copy { display:flex; justify-content:space-between; color:#9fb1c5; font-size:.82rem; margin:10px 0 7px; }
.progress { height:7px; background:#132438; border-radius:99px; overflow:hidden; }
.progress > div { width:65%; height:100%; border-radius:99px; background:linear-gradient(90deg,#10b981,#38bdf8); animation:progress 2.2s ease-in-out infinite; }
@keyframes progress { 0%{width:8%} 50%{width:78%} 100%{width:94%} }
.ticker-note { color:var(--muted); font-size:.72rem; text-align:center; margin-top:6px; }
.small-muted { color:var(--muted); font-size:.78rem; }
@media (max-width: 520px) {
  .block-container { padding: .65rem .55rem 4rem !important; }
  .index-wrap { justify-content:flex-start; }
  .hero-price { font-size:1.9rem; }
  .stButton > button { min-height:44px; }
}
</style>
"""
st.markdown(CSS, unsafe_allow_html=True)

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
    symbols = get_nifty50_symbols()
    df = get_nifty50_ticker_data(tuple(symbols))
    if df.empty:
        st.markdown('<div class="ticker-note">NIFTY 50 ticker data temporarily unavailable.</div>', unsafe_allow_html=True)
        return
    items = []
    for _, r in df.iterrows():
        cls = "up" if r.pct >= 0 else "down"
        arrow = "▲" if r.pct >= 0 else "▼"
        items.append(f'<span class="tick"><b>{html.escape(r.symbol)}</b> {money(r.price)} <span class="{cls}">{arrow} {r.pct:+.2f}%</span></span>')
    content = "".join(items)
    markup = f"""
    <html><head><style>
    *{{box-sizing:border-box}} body{{margin:0;background:#07111f;color:#dbe7f3;font-family:Arial,sans-serif;overflow:hidden}}
    .viewport{{width:100%;overflow:hidden;border:1px solid rgba(148,163,184,.12);border-radius:13px;background:#091727}}
    .track{{display:flex;width:max-content;animation:marquee 48s linear infinite;padding:10px 0}}
    .track:hover{{animation-play-state:paused}} .tick{{white-space:nowrap;margin-right:28px;font-size:12px;color:#9fb1c5}}
    .tick b{{color:#f1f5f9;margin-right:5px}} .up{{color:#19d38a}} .down{{color:#ff5c70}}
    @keyframes marquee{{from{{transform:translateX(0)}}to{{transform:translateX(-50%)}}}}
    </style></head><body>
    <div class="viewport" id="v"><div class="track" id="t">{content}{content}</div></div>
    <script>const v=document.getElementById('v'),t=document.getElementById('t');v.addEventListener('touchstart',()=>t.style.animationPlayState='paused',{{passive:true}});v.addEventListener('touchend',()=>t.style.animationPlayState='running',{{passive:true}});</script>
    </body></html>"""
    components.html(markup, height=43, scrolling=False)


def render_scan_animation():
    candles = "".join('<span class="candle '+('g' if i%3 else 'r')+'"></span>' for i in range(42))
    return f'''<div class="scan-shell"><div class="scan-chart"><div class="candle-track">{candles}{candles}</div></div><div class="scan-copy"><span>Scanning NIFTY LargeMidcap 250…</span><span>Technical setup analysis</span></div><div class="progress"><div></div></div><div class="small-muted" style="margin-top:8px">Fetching prices → calculating indicators → ranking near-breakout setups</div></div>'''


def metric_card(label, value):
    return f'<div class="metric-card"><div class="metric-label">{html.escape(str(label))}</div><div class="metric-value">{html.escape(str(value))}</div></div>'


def day_change(symbol, period="2y"):
    hist = fetch_history(symbol, period)
    if hist is None or len(hist) < 2:
        return None, None, None
    last, prev = float(hist.Close.iloc[-1]), float(hist.Close.iloc[-2])
    return last, last-prev, (last/prev-1)*100


def detail_chart(symbol, row, period="2y"):
    hist = fetch_history(symbol, period)
    if hist is None or hist.empty:
        st.warning("Price history is temporarily unavailable for the chart.")
        return
    fig = go.Figure()
    fig.add_trace(go.Candlestick(x=hist.index, open=hist.Open, high=hist.High, low=hist.Low, close=hist.Close, name=symbol))
    fig.add_trace(go.Bar(x=hist.index, y=hist.Volume, name="Volume", yaxis="y2", opacity=.25))
    fig.add_hline(y=float(row["breakout_level"]), line_dash="dash", line_color="#19d38a", annotation_text=f"Breakout: ₹{row['breakout_level']:.2f}", annotation_position="top left")
    fig.update_layout(
        template="plotly_dark", height=470, margin=dict(l=8,r=8,t=30,b=10),
        xaxis_rangeslider_visible=False, hovermode="x unified",
        paper_bgcolor="#0c192b", plot_bgcolor="#07111f",
        yaxis=dict(title="Price", fixedrange=False),
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



def _pdf_text(value):
    """Keep PDF text ASCII-safe so fpdf2 does not choke on ₹ or other glyphs."""
    if value is None:
        return "-"
    text = str(value)
    for old, new in {"₹":"Rs.", "—":"-", "–":"-", "•":"-", "▲":"UP", "▼":"DOWN", "→":"->", "←":"<-", "≥":">=", "≤":"<=", "×":"x"}.items():
        text = text.replace(old, new)
    return text.encode("latin-1", "replace").decode("latin-1")


def build_pdf_report(symbol, row, price, export_dt):
    """Build the single-stock PDF entirely in memory; no server file is created."""
    pdf = FPDF()
    pdf.set_auto_page_break(auto=True, margin=14)
    pdf.add_page()
    company = row.get("company_name", symbol)
    score = float(row.get("score", 0) or 0)
    label, strong = verdict(score)

    pdf.set_font("Helvetica", "B", 18)
    pdf.cell(0, 10, "NIFTY Breakout Scanner Report", ln=True)
    pdf.set_font("Helvetica", "", 9)
    pdf.cell(0, 6, _pdf_text(f"Scanned/exported: {export_dt.strftime('%d %b %Y, %H:%M:%S IST')}"), ln=True)
    pdf.ln(3)
    pdf.set_fill_color(235, 242, 248)
    pdf.set_font("Helvetica", "B", 12)
    pdf.cell(0, 9, _pdf_text(f"{company} ({symbol})"), ln=True, fill=True)
    pdf.set_font("Helvetica", "", 10)
    pdf.cell(0, 7, _pdf_text(f"Price on export: {money(price)}"), ln=True)
    pdf.cell(0, 7, _pdf_text(f"Target 1: {money(row.get('target1'))}    Target 2: {money(row.get('target2'))}"), ln=True)
    pdf.ln(4)

    pdf.set_font("Helvetica", "B", 12)
    pdf.cell(0, 8, "Setup Strength & Verdict", ln=True)
    pdf.set_font("Helvetica", "", 10)
    pdf.cell(0, 7, _pdf_text(f"Technical setup strength: {score:.1f}/100"), ln=True)
    pdf.cell(0, 7, _pdf_text(f"Verdict: {label} | Strong setup: {'Yes' if strong else 'No'}"), ln=True)

    level = float(row.get("breakout_level", 0) or 0)
    p = float(price or 0)
    distance = ((level-p)/level*100) if level else 999
    if p >= level:
        entry_title, entry_msg = "Breakout Confirmed", "Price is trading at or above the detected breakout level."
    elif distance <= 2:
        entry_title, entry_msg = "ENTRY ZONE", "Price is near the breakout level. Confirmation still matters."
    else:
        entry_title, entry_msg = "Wait", "Not near the entry point yet."
    pdf.cell(0, 7, _pdf_text(f"Entry status: {entry_title} - {entry_msg}"), ln=True)
    pdf.cell(0, 7, _pdf_text(f"Distance to breakout: {distance:.2f}% | Suggested entry reference: {money(row.get('breakout_trigger'))}"), ln=True)
    pdf.ln(3)

    pdf.set_font("Helvetica", "B", 12)
    pdf.cell(0, 8, "Technical Data", ln=True)
    pdf.set_font("Helvetica", "", 9)
    field_map = {
        "price":"Current price", "breakout_level":"Breakout level", "breakout_trigger":"Breakout trigger",
        "distance_pct":"Distance", "score":"Score", "rating":"Rating", "rsi":"RSI", "macd":"MACD", "adx":"ADX",
        "rvol":"RVOL", "atr_pct":"ATR %", "ema_structure":"EMA structure", "candlestick":"Candlestick",
        "relative_strength":"60D relative strength", "nifty_relative_strength":"NIFTY relative strength",
        "sector_relative_strength":"Sector relative strength", "market_regime":"Market regime",
        "risk_reward":"Risk / reward", "squeeze":"Squeeze", "resistance_touches":"Resistance touches",
        "status":"Status", "false_breakout":"False breakout", "false_breakout_age":"False breakout age",
        "stop_reference":"Stop reference", "target1":"Target 1", "target2":"Target 2",
    }
    preferred = ["price","breakout_level","breakout_trigger","distance_pct","rating","score","rvol","rsi","adx","ema_structure","macd","atr_pct","squeeze","nifty_relative_strength","relative_strength","sector_relative_strength","candlestick","resistance_touches","risk_reward","market_regime","status","false_breakout","false_breakout_age","stop_reference","target1","target2"]
    seen=set()
    for key in preferred:
        if key not in row or key in seen: continue
        seen.add(key)
        value=row.get(key)
        if key=="price" or key in {"breakout_level","breakout_trigger","stop_reference","target1","target2"}: value=money(value)
        elif key=="distance_pct" or key in {"nifty_relative_strength","relative_strength","sector_relative_strength"}: value=pct(value)
        elif key=="rating": value=f"{value}/10"
        elif key=="score": value=f"{float(value):.1f}/100"
        elif key=="rvol": value=f"{float(value):.2f}x"
        elif key in {"rsi","adx","macd","atr_pct","squeeze","risk_reward"}:
            value=f"{float(value):.3f}" if key=="macd" else f"{float(value):.2f}"
            if key=="atr_pct": value += "%"
        elif key=="false_breakout": value="Yes" if value else "No"
        pdf.cell(58, 6.5, _pdf_text(field_map.get(key, key.replace("_"," ").title())), border=1)
        pdf.cell(0, 6.5, _pdf_text(value), border=1, ln=True)
    for key, value in row.items():
        if key in seen or key in {"symbol","company_name","rank_score","explanation","rank"}: continue
        pdf.cell(58, 6.5, _pdf_text(key.replace("_"," ").title()), border=1)
        pdf.cell(0, 6.5, _pdf_text(value), border=1, ln=True)

    pdf.ln(4)
    pdf.set_font("Helvetica", "B", 12)
    pdf.cell(0, 8, "Technical Summary", ln=True)
    pdf.set_font("Helvetica", "", 9)
    pdf.multi_cell(0, 5.5, _pdf_text(row.get("explanation") or "No technical summary was supplied by the scanner."))
    data=pdf.output(dest="S")
    return bytes(data) if not isinstance(data,str) else data.encode("latin-1")


def build_shortlist_pdf(result, export_dt):
    pdf=FPDF(orientation="L")
    pdf.set_auto_page_break(auto=True, margin=10)
    pdf.add_page()
    pdf.set_font("Helvetica","B",16)
    pdf.cell(0,9,"NIFTY Breakout Scanner - Shortlist",ln=True)
    pdf.set_font("Helvetica","",9)
    pdf.cell(0,6,_pdf_text(f"Exported: {export_dt.strftime('%d %b %Y, %H:%M:%S IST')}"),ln=True)
    pdf.ln(3)
    headers=["Rank","Symbol","Price","Distance","Rating","Score","RVOL","Status"]
    widths=[15,35,30,30,22,25,25,75]
    pdf.set_font("Helvetica","B",9)
    for h,w in zip(headers,widths): pdf.cell(w,7,h,border=1,fill=True)
    pdf.ln(); pdf.set_font("Helvetica","",8)
    for _,r in result.iterrows():
        vals=[int(r.get("rank",0)),r.get("symbol",""),money(r.get("price")),pct(r.get("distance_pct")),f"{r.get('rating','-')}/10",f"{float(r.get('score',0)):.1f}",f"{float(r.get('rvol',0)):.2f}x",r.get("status","-")]
        for v,w in zip(vals,widths): pdf.cell(w,7,_pdf_text(v),border=1)
        pdf.ln()
    data=pdf.output(dest="S")
    return bytes(data) if not isinstance(data,str) else data.encode("latin-1")

def render_detail(symbol, row):
    if st.button("← Back to Top 20"):
        st.session_state.page = "home"
        st.rerun()
    company = row.get("company_name", symbol)
    last, change, change_pct = day_change(symbol)
    price = last if last is not None else row.get("price")
    score = float(row.get("score", 0))
    label, strong = verdict(score)
    change_cls = "up" if (change_pct or 0) >= 0 else "down"
    arrow = "▲" if (change_pct or 0) >= 0 else "▼"

    st.markdown(f'''<div class="card"><div class="small-muted">{html.escape(str(company))}</div><div style="font-size:1.15rem;font-weight:900">{html.escape(symbol)}</div><div class="hero-price">{money(price)}</div><div class="{change_cls}" style="font-weight:850">{arrow} {money(change)} ({pct(change_pct)})</div></div>''', unsafe_allow_html=True)

    # The scanner's score is a technical setup score, not a fundamental-analysis score.
    fig = go.Figure(go.Indicator(
        mode="gauge+number", value=score,
        number={"suffix":" / 100", "font":{"size":34}},
        title={"text":"Technical Setup Strength"},
        gauge={
            "axis":{"range":[0,100],"tickwidth":1,"tickcolor":"#71839a"},
            "bar":{"color":"#19d38a","thickness":.22},
            "bgcolor":"#0b1829", "borderwidth":0,
            "steps":[
                {"range":[0,40],"color":"#54202a"},
                {"range":[40,65],"color":"#5a4c22"},
                {"range":[65,80],"color":"#716225"},
                {"range":[80,100],"color":"#123d30"},
            ],
        },
        domain={"x":[0,1],"y":[0,1]},
    ))
    fig.update_layout(template="plotly_dark", height=245, margin=dict(l=15,r=15,t=45,b=5), paper_bgcolor="#0c192b")
    st.plotly_chart(fig, use_container_width=True, config={"displayModeBar":False})
    badge = '<span class="badge badge-green">BUY SIGNAL</span>' if strong else '<span class="badge badge-grey">SETUP WATCH</span>'
    st.markdown(f'<div style="text-align:center;margin-top:-12px"><b>{label}</b> &nbsp; {badge}</div>', unsafe_allow_html=True)

    st.markdown('<div class="section-title">Technical Data</div>', unsafe_allow_html=True)
    hist = fetch_history(symbol, "2y")
    extra = {}
    if hist is not None and len(hist):
        last52 = hist.tail(252)
        extra = {"52-week high": money(float(last52.High.max())), "52-week low": money(float(last52.Low.min()))}
    fields = [
        ("Breakout level", money(row.get("breakout_level"))), ("Breakout trigger", money(row.get("breakout_trigger"))),
        ("Distance", pct(row.get("distance_pct"))), ("Rating", f"{row.get('rating','—')}/10"),
        ("Score", f"{row.get('score',0):.1f}/100"), ("RVOL", f"{row.get('rvol',0):.2f}x"),
        ("RSI", f"{row.get('rsi',0):.1f}"), ("ADX", f"{row.get('adx',0):.1f}"),
        ("EMA structure", row.get("ema_structure","—")), ("MACD", f"{row.get('macd',0):.3f}"),
        ("ATR %", f"{row.get('atr_pct',0):.2f}%"), ("Squeeze", f"{row.get('squeeze',0):.2f}"),
        ("NIFTY relative strength", pct(row.get("nifty_relative_strength"))), ("60D relative strength", pct(row.get("relative_strength"))),
        ("Candlestick", row.get("candlestick","—")), ("Resistance touches", row.get("resistance_touches","—")),
        ("Risk / reward", f"{row.get('risk_reward',0):.2f}"), ("Market regime", row.get("market_regime","—")),
        ("Status", row.get("status","—")), ("False breakout", "Yes" if row.get("false_breakout") else "No"),
        ("Stop reference", money(row.get("stop_reference"))), ("Target 1", money(row.get("target1"))),
        ("Target 2", money(row.get("target2"))), ("52-week high", extra.get("52-week high","—")),
        ("52-week low", extra.get("52-week low","—")),
    ]
    # If the scanner later exposes additional fields, display them too without changing scanner.py.
    known = {x[0] for x in fields}
    field_map = {"price":"Current price","breakout_level":"Breakout level","breakout_trigger":"Breakout trigger","distance_pct":"Distance","score":"Score","rating":"Rating","rsi":"RSI","macd":"MACD","adx":"ADX","rvol":"RVOL","atr_pct":"ATR %","ema_structure":"EMA structure","candlestick":"Candlestick","relative_strength":"60D relative strength","nifty_relative_strength":"NIFTY relative strength","sector_relative_strength":"Sector relative strength","market_regime":"Market regime","risk_reward":"Risk / reward","squeeze":"Squeeze"}
    for k, v in row.items():
        label = field_map.get(k, k.replace("_"," ").title())
        if label in known or k in {"symbol","company_name","rank_score","explanation","rank"}: continue
        fields.append((label, f"{v:.2f}" if isinstance(v,(float,np.floating)) else str(v)))
    for i in range(0, len(fields), 2):
        c1, c2 = st.columns(2)
        with c1: st.markdown(metric_card(*fields[i]), unsafe_allow_html=True)
        if i+1 < len(fields):
            with c2: st.markdown(metric_card(*fields[i+1]), unsafe_allow_html=True)

    st.markdown('<div class="section-title">Price Chart</div>', unsafe_allow_html=True)
    detail_chart(symbol, row)

    level = float(row.get("breakout_level", 0) or 0)
    p = float(price or 0)
    distance = ((level-p)/level*100) if level else 999
    if p >= level:
        title, msg, cls = "Breakout Confirmed", "Price is trading at or above the detected breakout level.", "badge-green"
    elif distance <= 2:
        title, msg, cls = "ENTRY ZONE", "Price is near the breakout level. Confirmation still matters.", "badge-green entry-pulse"
    else:
        title, msg, cls = "Wait", "Not near the entry point yet.", "badge-grey"
    st.markdown(f'''<div class="card"><span class="badge {cls}">{title}</span><div style="font-size:1.05rem;font-weight:850;margin-top:9px">{msg}</div><div class="small-muted" style="margin-top:7px">Distance to breakout: {distance:.2f}% &nbsp; • &nbsp; Suggested entry reference: {money(row.get('breakout_trigger'))}</div></div>''', unsafe_allow_html=True)

    if row.get("explanation"):
        st.markdown(f'<div class="card"><b>Technical summary</b><div class="small-muted" style="margin-top:8px">{html.escape(str(row["explanation"]))}</div></div>', unsafe_allow_html=True)

    # UI/export only: the report uses the already-scanned row and does not alter scanner logic.
    export_dt = datetime.now(IST)
    pdf_bytes = build_pdf_report(symbol, row, price, export_dt)
    safe_symbol = str(symbol).replace(".NS", "").replace("/", "_")
    st.download_button(
        "Download PDF report",
        data=pdf_bytes,
        file_name=f"{safe_symbol}_breakout_report_{export_dt.strftime('%Y%m%d_%H%M%S')}.pdf",
        mime="application/pdf",
        use_container_width=True,
        key=f"pdf_report_{safe_symbol}",
    )


def render_home():
    st.markdown("<div style='font-size:1.6rem;font-weight:950'>📈 NIFTY Breakout Scanner</div><div class='small-muted'>Top 20 near-breakout technical setups from the NIFTY LargeMidcap 250 universe</div>", unsafe_allow_html=True)
    render_market_bar()
    render_ticker()
    st.markdown("<div style='height:5px'></div>", unsafe_allow_html=True)

    if st.button("🚀 SCAN MARKET", key="scan_market", type="primary", use_container_width=True):
        st.session_state.scanning = True
        st.session_state.scan_error = None
        placeholder = st.empty()
        placeholder.markdown(render_scan_animation(), unsafe_allow_html=True)
        try:
            with ThreadPoolExecutor(max_workers=1) as executor:
                future = executor.submit(scan_universe, max_distance=10.0, period="2y", top_n=20)
                while not future.done():
                    time.sleep(.25)
                result = future.result()
            st.session_state.scan_result = result
        except Exception as exc:
            st.session_state.scan_result = pd.DataFrame()
            st.session_state.scan_error = str(exc)
        finally:
            placeholder.empty()
            st.session_state.scanning = False

    st.markdown("<div class='section-title' style='margin-top:14px'>Search a Stock</div>", unsafe_allow_html=True)
    with st.form("single_stock_search", clear_on_submit=False):
        search_symbol = st.text_input("", placeholder="Enter NSE symbol, e.g. RELIANCE or TCS", label_visibility="collapsed")
        search_submitted = st.form_submit_button("🔎 Check Stock", use_container_width=True)
    if search_submitted:
        symbol = search_symbol.strip().upper().replace(".NS", "")
        if not symbol:
            st.warning("Please enter an NSE stock symbol.")
        else:
            with st.spinner(f"Checking {symbol} using the existing scanner criteria…"):
                try:
                    single = scan_single(symbol, max_distance=10.0, period="2y")
                except Exception as exc:
                    single = None
                    st.session_state.single_scan_error = str(exc)
                else:
                    st.session_state.single_scan_error = None
                if single is None:
                    st.session_state.single_scan_result = None
                    st.warning(f"{symbol} does not meet the scanner criteria right now, or the required data is unavailable. No criteria were loosened to force a result.")
                else:
                    if isinstance(single, pd.Series):
                        single = single.to_dict()
                    single["symbol"] = str(single.get("symbol", symbol)).upper().replace(".NS", "")
                    st.session_state.selected_stock = single["symbol"]
                    st.session_state.selected_row = single
                    st.session_state.page = "detail"
                    st.session_state.single_scan_result = single
                    st.rerun()

    result = st.session_state.get("scan_result")
    if st.session_state.get("scan_error"):
        st.error("The market scan could not be completed. Please try again. Details: " + st.session_state.scan_error)
    if result is None:
        st.markdown('<div class="card"><b>Ready to scan</b><div class="small-muted" style="margin-top:6px">The scanner will fetch the NIFTY LargeMidcap 250 data and rank the strongest near-breakout setups.</div></div>', unsafe_allow_html=True)
        return
    if result.empty:
        st.markdown('<div class="card"><b>No qualifying setups found</b><div class="small-muted" style="margin-top:6px">Nothing currently meets the scanner’s near-breakout criteria. Try again after the next market session.</div></div>', unsafe_allow_html=True)
        return

    st.markdown(f'<div class="section-title">Shortlisted Stocks ({len(result)})</div>', unsafe_allow_html=True)
    for start in range(0, len(result), 2):
        cols = st.columns(2)
        for j, col in enumerate(cols):
            idx = start+j
            if idx >= len(result): continue
            row = result.iloc[idx]
            with col:
                label = f"#{int(row['rank'])}  {row['symbol']}\n₹{row['price']:,.2f}  •  {row['distance_pct']:.2f}% to breakout  •  {int(row['rating'])}/10"
                if st.button(label, key=f"stock_{row['symbol']}", use_container_width=True):
                    st.session_state.selected_stock = row['symbol']
                    st.session_state.selected_row = row.to_dict()
                    st.session_state.page = "detail"
                    st.rerun()

    shortlist_pdf = build_shortlist_pdf(result, datetime.now(IST))
    st.download_button(
        "Download Shortlist PDF",
        data=shortlist_pdf,
        file_name=f"nifty_breakout_shortlist_{datetime.now(IST).strftime('%Y%m%d_%H%M%S')}.pdf",
        mime="application/pdf",
        use_container_width=True,
        key="shortlist_pdf",
    )

    st.markdown('<div class="small-muted" style="text-align:center;margin-top:12px">Breakout levels are technical reference levels, not guaranteed predictions.</div>', unsafe_allow_html=True)


# -----------------------------------------------------------------------------
# Session-state navigation: only two pages, no multipage folder.
# -----------------------------------------------------------------------------
if "page" not in st.session_state: st.session_state.page = "home"
if "scan_result" not in st.session_state: st.session_state.scan_result = None

if st.session_state.page == "detail" and st.session_state.get("selected_stock"):
    render_detail(st.session_state.selected_stock, st.session_state.selected_row)
else:
    render_home()

st.markdown('<div style="text-align:center;color:#71839a;font-size:.7rem;margin-top:28px">For educational purposes only. Not investment advice.</div>', unsafe_allow_html=True)
