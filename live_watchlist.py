import pandas as pd
from datetime import datetime
import streamlit as st
import yfinance as yf
import html

def money(x):
    try:
        return f'₹{float(x):,.2f}'
    except:
        return '—'

@st.cache_data(ttl=30, show_spinner=False)
def fetch_live_watchlist_prices(symbols):
    """Fetches live prices using yfinance."""
    live_prices = {}
    if not symbols: return live_prices
    
    try:
        tickers = [f"{s.replace('.NS', '')}.NS" for s in symbols]
        data = yf.download(tickers, period="1d", interval="1m", progress=False)
        if not data.empty:
            for sym, ticker in zip(symbols, tickers):
                if isinstance(data.columns, pd.MultiIndex):
                    try: live_prices[sym] = float(data['Close'][ticker].dropna().iloc[-1])
                    except: pass
                else:
                    try: live_prices[sym] = float(data['Close'].dropna().iloc[-1])
                    except: pass
    except Exception:
        pass
        
    return live_prices

def render_watchlist_tab(watchlist_df):
    header_html = (
        '<div style="display:flex; justify-content:space-between; align-items:center; margin-bottom: 16px;">'
        '<div class="section-title" style="margin:0; border:none;">Active Positions & Watchlist</div>'
        '<span class="badge badge-brand">🟢 Yahoo Finance Live Feed</span>'
        '</div>'
    )
    st.markdown(header_html, unsafe_allow_html=True)
    
    if watchlist_df.empty:
        st.info("Your Manual_Watch_List is currently empty. Add stocks from the scanner!")
        return

    if "Symbol" not in watchlist_df.columns:
        watchlist_df["Symbol"] = watchlist_df.get("Stock_Name", "")
        
    symbols = watchlist_df["Symbol"].dropna().unique().tolist()
    live_prices = fetch_live_watchlist_prices(symbols)
    
    # Render as a vertical list of full-width horizontal cards
    for idx, row in watchlist_df.iterrows():
        sym = str(row.get("Symbol", "")).replace(".NS", "")
        
        # Safely parse dates using the generic coerce to handle both old and new date formats
        added_date = pd.to_datetime(row.get("Date_Added"), errors="coerce")
        days_active = (datetime.now() - added_date).days if pd.notna(added_date) else 0
        
        entry_str = str(row.get("Price_Added", 0)).replace(',', '').strip()
        try:
            entry_price = float(entry_str)
        except ValueError:
            entry_price = 0.0
            
        live_price = live_prices.get(sym, entry_price)
        change_pct = ((live_price - entry_price) / entry_price * 100) if entry_price > 0 else 0
        
        if change_pct > 0:
            arrow, color = "▲", "var(--accent)"
        elif change_pct < 0:
            arrow, color = "▼", "var(--red)"
        else:
            arrow, color = "−", "var(--muted)"
            
        trade_type = str(row.get("Trade_Type", "SWING"))
        exp_days = str(row.get("Expected_Days", ""))
        
        t1 = str(row.get("Target_1", ""))
        t2 = str(row.get("Target_2", ""))
        
        card_html = (
            f'<div class="bento-stock-card" style="display:flex; flex-wrap:wrap; justify-content:space-between; align-items:center; padding:18px 24px; margin-bottom:12px;">'
            
            # Left Section: Ticker, Entry, Badge
            f'<div style="display:flex; flex-direction:column; gap:6px; min-width:200px;">'
            f'<div style="font-size:1.6rem; font-weight:900; color:var(--text); line-height:1; letter-spacing:0.02em;">{html.escape(sym)}</div>'
            f'<div style="font-size:0.85rem; color:var(--muted);">Entry: {money(entry_price)}</div>'
            f'<div style="margin-top:2px;"><span style="background:rgba(255,255,255,0.05); border:1px solid var(--border); padding:4px 8px; border-radius:4px; font-size:0.75rem; font-weight:700; color:#8ba2b5; letter-spacing:0.03em; text-transform:uppercase;">{html.escape(trade_type)} <span style="color:var(--text); font-weight:500;">{html.escape(exp_days)}</span></span></div>'
            f'</div>'
            
            # Middle Section: Days Active, Pct, Current Price
            f'<div style="display:flex; flex-direction:column; gap:2px; min-width:200px;">'
            f'<div style="display:flex; align-items:baseline; gap:12px;">'
            f'<span style="font-size:0.85rem; font-weight:700; color:#8ba2b5; letter-spacing:0.02em; text-transform:uppercase;">{days_active} DAYS ACTIVE</span>'
            f'<span style="color:{color}; font-size:1.15rem; font-weight:900;">{arrow} {abs(change_pct):.2f}%</span>'
            f'</div>'
            f'<div style="font-size:1.8rem; font-weight:900; color:var(--text); display:flex; align-items:baseline; gap:6px; margin-top:2px;">'
            f'<span style="font-size:1.2rem; font-weight:500; color:var(--text);">CP-</span>{money(live_price)}'
            f'</div>'
            f'</div>'
            
            # Right Section: Targets
            f'<div style="display:flex; gap:40px; align-items:center; min-width:200px;">'
            f'<div style="display:flex; flex-direction:column; gap:4px;">'
            f'<span style="font-size:1.1rem; font-weight:400; color:var(--text);">Target -1</span>'
            f'<span style="font-size:1.2rem; font-weight:400; color:var(--text);">{t1 if t1 != "" else "—"}</span>'
            f'</div>'
            f'<div style="display:flex; flex-direction:column; gap:4px;">'
            f'<span style="font-size:1.1rem; font-weight:400; color:var(--text);">Target -2</span>'
            f'<span style="font-size:1.2rem; font-weight:400; color:var(--text);">{t2 if t2 != "" else "—"}</span>'
            f'</div>'
            f'</div>'
            
            f'</div>'
        )
        
        st.markdown(card_html, unsafe_allow_html=True)
