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
    
    for start in range(0, len(watchlist_df), 3):
        cols = st.columns(3)
        for j, col in enumerate(cols):
            idx = start + j
            if idx >= len(watchlist_df): continue
            row = watchlist_df.iloc[idx]
            sym = str(row.get("Symbol", "")).replace(".NS", "")
            
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
                
            change_str = f'<span style="color:{color}; font-weight:900; font-size:1.15rem;">{arrow} {abs(change_pct):.2f}%</span>'
            
            with col:
                card_html = (
                    f'<div class="bento-stock-card">'
                    f'<div style="display:flex;justify-content:space-between;align-items:center;">'
                    f'<span class="badge badge-grey">{html.escape(str(row.get("Trade_Type", "SWING")))}</span>'
                    f'<span style="font-size:0.75rem; color:var(--muted); font-weight:700;">{days_active} DAYS ACTIVE</span>'
                    f'</div>'
                    f'<div style="font-weight:800;font-size:1.2rem;color:var(--text);margin-top:10px;">{html.escape(sym)}</div>'
                    f'<div class="small-muted" style="margin-bottom:12px;">Entry: {money(entry_price)}</div>'
                    f'<div style="display:flex;justify-content:space-between;align-items:baseline;padding-top:12px;border-top:1px solid var(--border);">'
                    f'<div style="font-weight:900;font-size:1.4rem;">{money(live_price)}</div>'
                    f'<div>{change_str}</div>'
                    f'</div>'
                    f'<div style="display:flex;gap:10px;margin-top:14px;">'
                    f'<div class="target-box" style="padding:10px;flex:1;"><div class="target-label">Target 1</div><div class="target-value" style="font-size:1rem;">{money(row.get("Target_1"))}</div></div>'
                    f'<div class="target-box" style="padding:10px;flex:1;"><div class="target-label">Target 2</div><div class="target-value" style="font-size:1rem;">{money(row.get("Target_2"))}</div></div>'
                    f'</div>'
                    f'</div>'
                )
                st.markdown(card_html, unsafe_allow_html=True)
