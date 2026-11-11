import html
import numpy as np
import pandas as pd
import streamlit as st
import yfinance as yf


def _clean_num(val, default=0.0):
    try:
        if pd.isna(val):
            return default
        cleaned = str(val).replace("₹", "").replace(",", "").replace("%", "").strip()
        return float(cleaned) if cleaned else default
    except Exception:
        return default


def _money(x):
    return f"₹{x:,.2f}" if x is not None and np.isfinite(x) and x > 0 else "—"


@st.cache_data(ttl=60, show_spinner=False)
def fetch_live_watchlist_prices(symbols_tuple):
    """Fetch live prices for watchlist symbols with MultiIndex handling and fast_info fallback."""
    live_prices = {}
    for sym in symbols_tuple:
        clean_sym = str(sym).strip().upper().replace(".NS", "")
        if not clean_sym:
            continue
        yf_sym = clean_sym.replace("&", "%26") + ".NS"
        price_found = None

        # Primary Method: 5-day 1d download
        try:
            t_df = yf.download(yf_sym, period="5d", interval="1d", progress=False, auto_adjust=True)
            if t_df is not None and not t_df.empty:
                close_col = t_df["Close"]
                if isinstance(close_col, pd.DataFrame):
                    close_col = close_col.iloc[:, 0]
                close_series = close_col.dropna()
                if not close_series.empty:
                    price_found = float(close_series.iloc[-1])
        except Exception:
            pass

        # Fallback Method: Yahoo Finance fast_info
        if price_found is None or not np.isfinite(price_found) or price_found <= 0:
            try:
                fi = yf.Ticker(yf_sym).fast_info
                lp = fi.get("lastPrice") or fi.get("regularMarketPrice") or fi.get("previousClose")
                if lp and float(lp) > 0:
                    price_found = float(lp)
            except Exception:
                pass

        if price_found is not None and np.isfinite(price_found) and price_found > 0:
            live_prices[clean_sym] = price_found

    return live_prices


def render_watchlist_tab(watchlist_df):
    if watchlist_df is None or watchlist_df.empty:
        st.info("Your Live Watchlist is empty. Go to the Scanner Dashboard, launch analytics on a stock, and click '⭐ Add to Watchlist'!")
        return

    df = watchlist_df.copy()
    if "Symbol" not in df.columns:
        st.warning("Watchlist sheet does not contain a 'Symbol' column.")
        return

    df["Symbol_Clean"] = df["Symbol"].astype(str).str.strip().str.upper().str.replace(".NS", "", regex=False)
    df = df[df["Symbol_Clean"].ne("") & df["Symbol_Clean"].ne("NAN")].reset_index(drop=True)

    if df.empty:
        st.info("No valid stock symbols found in your watchlist.")
        return

    # Optional simulated capital per watchlist stock to see rupee Unrealized PnL alongside % return
    wc_col1, wc_col2 = st.columns([6, 2])
    with wc_col1:
        st.markdown(
            "<div class='small-muted' style='margin-bottom:12px;'>Live prices are pulled in real time via Yahoo Finance APIs and compared against your saved Price_Added.</div>",
            unsafe_allow_html=True,
        )
    with wc_col2:
        sim_capital = st.number_input(
            "Simulated Capital / Stock (₹)",
            min_value=1000,
            value=25000,
            step=5000,
            key="watchlist_sim_cap",
        )

    symbols_tuple = tuple(df["Symbol_Clean"].unique().tolist())
    live_prices = fetch_live_watchlist_prices(symbols_tuple)

    total_sim_pnl = 0.0
    total_sim_invested = 0.0

    for idx, row in df.iterrows():
        sym = row["Symbol_Clean"]
        company = str(row.get("Stock_Name", sym) or sym)
        date_added = str(row.get("Date_Added", "—") or "—")
        trade_type = str(row.get("Trade_Type", "Setup") or "Setup")
        exp_days = str(row.get("Expected_Days", "N/A") or "N/A")

        price_added = _clean_num(row.get("Price_Added", 0))
        live_price = live_prices.get(sym, price_added)

        t1 = _clean_num(row.get("Target_1", 0))
        t2 = _clean_num(row.get("Target_2", 0))
        t3 = _clean_num(row.get("Target_3", 0))
        trigger = _clean_num(row.get("Trigger_Price", 0))

        # Calculate Unrealized Return % and Simulated Rupee PnL
        if price_added > 0 and live_price > 0:
            diff_per_share = live_price - price_added
            return_pct = ((live_price / price_added) - 1.0) * 100.0
            sim_qty = max(1, int(sim_capital // price_added))
            sim_pnl = diff_per_share * sim_qty
            total_sim_pnl += sim_pnl
            total_sim_invested += (price_added * sim_qty)
        else:
            diff_per_share = 0.0
            return_pct = 0.0
            sim_qty = 0
            sim_pnl = 0.0

        pnl_color = "var(--accent)" if return_pct >= 0 else "var(--red)"
        pnl_sign = "+" if return_pct >= 0 else ""

        # Status badge against Trigger & Targets
        if t3 > 0 and live_price >= t3:
            status_badge = "<span class='badge badge-green'>🎯 T3 REACHED</span>"
        elif t2 > 0 and live_price >= t2:
            status_badge = "<span class='badge badge-green'>🎯 T2 REACHED</span>"
        elif t1 > 0 and live_price >= t1:
            status_badge = "<span class='badge badge-green'>✅ T1 REACHED</span>"
        elif trigger > 0 and live_price >= trigger:
            status_badge = "<span class='badge badge-accent'>🚀 ABOVE TRIGGER</span>"
        else:
            status_badge = "<span class='badge badge-yellow'>⏳ IN WATCH ZONE</span>"

        st.markdown(
            f"""
            <div class="bento-card" style="display:flex; justify-content:space-between; align-items:center; flex-wrap:wrap; gap:16px;">
                <div style="flex:1.5; min-width:220px;">
                    <div style="display:flex; align-items:center; gap:8px; flex-wrap:wrap;">
                        <span style="font-weight:900; font-size:1.2rem; color:var(--text);">{html.escape(sym)}</span>
                        <span class="badge badge-brand">{html.escape(trade_type)} ({html.escape(exp_days)})</span>
                        {status_badge}
                    </div>
                    <div class="small-muted" style="margin-top:4px;">{html.escape(company)} • Added: {html.escape(date_added)}</div>
                    <div class="small-muted" style="margin-top:4px;">
                        Trigger: <b>{_money(trigger)}</b> &nbsp;|&nbsp; T1: <b>{_money(t1)}</b> &nbsp;|&nbsp; T2: <b>{_money(t2)}</b> &nbsp;|&nbsp; T3: <b>{_money(t3)}</b>
                    </div>
                </div>
                <div>
                    <div class="small-muted" style="text-transform:uppercase; font-size:0.7rem;">Added Price</div>
                    <div style="font-weight:800; font-size:1.05rem; color:var(--text);">{_money(price_added)}</div>
                </div>
                <div>
                    <div class="small-muted" style="text-transform:uppercase; font-size:0.7rem;">Live Price</div>
                    <div style="font-weight:800; font-size:1.1rem; color:var(--text);">{_money(live_price)}</div>
                </div>
                <div style="text-align:right; min-width:170px;">
                    <div class="small-muted" style="text-transform:uppercase; font-size:0.7rem;">Unrealized Move / Sim PnL ({sim_qty} sh)</div>
                    <div style="font-weight:900; font-size:1.15rem; color:{pnl_color};">
                        {pnl_sign}{return_pct:.2f}% ({pnl_sign}{_money(abs(sim_pnl)) if sim_pnl < 0 else _money(sim_pnl)})
                    </div>
                    <div class="small-muted" style="font-size:0.72rem;">Per Share: {pnl_sign}₹{diff_per_share:,.2f}</div>
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    if total_sim_invested > 0:
        tot_color = "var(--accent)" if total_sim_pnl >= 0 else "var(--red)"
        tot_sign = "+" if total_sim_pnl >= 0 else ""
        tot_pct = (total_sim_pnl / total_sim_invested) * 100.0
        st.markdown(
            f"""
            <div style="text-align:right; margin-top:8px; padding-right:16px;">
                <span class="small-muted" style="font-size:0.8rem; text-transform:uppercase; font-weight:700;">Total Watchlist Simulated PnL:</span>
                <span style="font-size:1.3rem; font-weight:900; color:{tot_color}; margin-left:8px;">
                    {tot_sign}₹{total_sim_pnl:,.2f} ({tot_sign}{tot_pct:.2f}%)
                </span>
            </div>
            """,
            unsafe_allow_html=True,
        )
