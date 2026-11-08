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

def render_watchlist_card(row, live_prices):
    """Helper function to render a single watchlist card."""
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
        arrow, color, border = "▲", "var(--accent)", "border:1px solid rgba(16, 185, 129, 0.3);"
    elif change_pct < 0:
        arrow, color, border = "▼", "var(--red)", "border:1px solid rgba(239, 68, 68, 0.3);"
    else:
        arrow, color, border = "−", "var(--muted)", ""
        
    trade_type = str(row.get("Trade_Type", "SWING"))
    exp_days = str(row.get("Expected_Days", ""))
    
    try: t1 = f'{float(row.get("Target_1", 0)):.2f}'
    except: t1 = "—"
        
    try: t2 = f'{float(row.get("Target_2", 0)):.2f}'
    except: t2 = "—"
    
    card_html = (
        f'<div class="bento-stock-card" style="padding:12px 14px; {border}">'
        
        # Row 1: Symbol & CP
        f'<div style="display:flex; justify-content:space-between; align-items:baseline; margin-bottom:2px;">'
        f'<div style="font-size:1.1rem; font-weight:900; color:var(--text); letter-spacing:0.02em;">{html.escape(sym)}</div>'
        f'<div style="font-size:1.05rem; font-weight:900; color:var(--text);"><span style="font-size:0.75rem; font-weight:500; color:var(--text);">CP- </span>{money(live_price)}</div>'
        f'</div>'
        
        # Row 2: Entry & Pct Change
        f'<div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:8px;">'
        f'<div style="font-size:0.75rem; color:var(--muted);">Entry: {money(entry_price)}</div>'
        f'<div style="font-size:0.9rem; font-weight:900; color:{color};">{arrow} {abs(change_pct):.2f}%</div>'
        f'</div>'
        
        # Row 3: Trade Type & Days Active
        f'<div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:12px;">'
        f'<div style="font-size:0.65rem; font-weight:800; color:#8ba2b5; text-transform:uppercase; letter-spacing:0.03em;">{html.escape(trade_type)} <span style="font-weight:500; color:var(--muted); text-transform:none;">{html.escape(exp_days)}</span></div>'
        f'<div style="font-size:0.65rem; font-weight:800; color:#8ba2b5; text-transform:uppercase; letter-spacing:0.03em;">{days_active} DAYS</div>'
        f'</div>'
        
        # Row 4: Targets
        f'<div style="display:flex; gap:12px; align-items:center; padding-top:10px; border-top:1px solid rgba(139, 162, 181, 0.15);">'
        f'<div style="display:flex; flex-direction:column; gap:2px; flex:1; text-align:left;">'
        f'<span style="font-size:0.75rem; font-weight:500; color:var(--text);">Target -1</span>'
        f'<span style="font-size:0.95rem; font-weight:700; color:var(--text);">{t1}</span>'
        f'</div>'
        f'<div style="display:flex; flex-direction:column; gap:2px; flex:1; text-align:left;">'
        f'<span style="font-size:0.75rem; font-weight:500; color:var(--text);">Target -2</span>'
        f'<span style="font-size:0.95rem; font-weight:700; color:var(--text);">{t2}</span>'
        f'</div>'
        f'</div>'
        
        f'</div>'
    )
    return card_html, change_pct

def render_watchlist_tab(watchlist_df):
    
    if watchlist_df.empty:
        st.markdown('<div class="section-title" style="margin:0; border:none;">Active Positions & Watchlist</div>', unsafe_allow_html=True)
        st.info("Your Manual_Watch_List is currently empty. Add stocks from the scanner!")
        return

    if "Symbol" not in watchlist_df.columns:
        watchlist_df["Symbol"] = watchlist_df.get("Stock_Name", "")
        
    symbols = watchlist_df["Symbol"].dropna().unique().tolist()
    live_prices = fetch_live_watchlist_prices(symbols)
    
    # Bifurcate the portfolio based on actual live calculations
    winners = []
    losers = []
    
    for idx, row in watchlist_df.iterrows():
        sym = str(row.get("Symbol", "")).replace(".NS", "")
        entry_str = str(row.get("Price_Added", 0)).replace(',', '').strip()
        try: entry_price = float(entry_str)
        except ValueError: entry_price = 0.0
            
        live_price = live_prices.get(sym, entry_price)
        change_pct = ((live_price - entry_price) / entry_price * 100) if entry_price > 0 else 0
        
        # Categorize
        if change_pct >= 0:
            winners.append((row, change_pct))
        else:
            losers.append((row, change_pct))
            
    # Sort by performance (highest gainers first, biggest losers first)
    winners = sorted(winners, key=lambda x: x[1], reverse=True)
    losers = sorted(losers, key=lambda x: x[1])

    # Header with Portfolio Summary Stats
    header_html = (
        f'<div style="display:flex; justify-content:space-between; align-items:center; margin-bottom: 24px; padding:16px 20px; background:var(--card); border:1px solid var(--border); border-radius:12px;">'
        f'<div style="display:flex; align-items:center; gap:24px;">'
        f'<div style="font-size:1.2rem; font-weight:800; color:var(--text); letter-spacing:-0.02em;">Live Portfolio Snapshot</div>'
        f'<div style="display:flex; gap:16px;">'
        f'<span class="badge badge-brand">Total Trades: {len(watchlist_df)}</span>'
        f'<span class="badge badge-green">🟢 In Profit: {len(winners)}</span>'
        f'<span class="badge badge-red">🔴 In Loss: {len(losers)}</span>'
        f'</div>'
        f'</div>'
        f'<span class="badge badge-grey">🟢 Yahoo Finance Live Feed</span>'
        f'</div>'
    )
    st.markdown(header_html, unsafe_allow_html=True)
    
    # ---------------------------------------------------------
    # SECTION 1: PROFITABLE TRADES (GREEN)
    # ---------------------------------------------------------
    if winners:
        st.markdown(f'<div class="section-title" style="margin-top:0; border-bottom:2px solid var(--accent); padding-bottom:8px; display:inline-block;">Profitable Positions <span style="color:var(--muted); font-size:0.9rem;">({len(winners)})</span></div>', unsafe_allow_html=True)
        st.markdown("<div style='height:8px'></div>", unsafe_allow_html=True)
        
        for start in range(0, len(winners), 4):
            cols = st.columns(4)
            for j, col in enumerate(cols):
                idx = start + j
                if idx >= len(winners): continue
                row, _ = winners[idx]
                card_html, _ = render_watchlist_card(row, live_prices)
                with col:
                    st.markdown(card_html, unsafe_allow_html=True)
        st.markdown("<div style='height:24px'></div>", unsafe_allow_html=True)

    # ---------------------------------------------------------
    # SECTION 2: NEGATIVE TRADES (RED)
    # ---------------------------------------------------------
    if losers:
        st.markdown(f'<div class="section-title" style="margin-top:0; border-bottom:2px solid var(--red); padding-bottom:8px; display:inline-block;">Positions in Loss <span style="color:var(--muted); font-size:0.9rem;">({len(losers)})</span></div>', unsafe_allow_html=True)
        st.markdown("<div style='height:8px'></div>", unsafe_allow_html=True)
        
        for start in range(0, len(losers), 4):
            cols = st.columns(4)
            for j, col in enumerate(cols):
                idx = start + j
                if idx >= len(losers): continue
                row, _ = losers[idx]
                card_html, _ = render_watchlist_card(row, live_prices)
                with col:
                    st.markdown(card_html, unsafe_allow_html=True)
