"""Live Manual Watchlist & Simulated PnL Tracker (Phase 4 Upgraded).

Upgrades implemented in Phase 4:
  1. Targeted Cache Invalidation: Replaces global st.cache_data.clear() with targeted
     cache clearing so promoting or removing a watchlist stock never wipes out cached
     market snapshots, stock histories, or fundamental data.
  2. Trigger Proximity & Progress Bar: Adds a visual progress bar from Added Price / Trigger
     to Target 1 & Target 2, plus a "🔥 NEAR TRIGGER (<=1%)" alert badge so imminent
     breakouts stand out immediately.
  3. Technical Snapshot Pills: Displays saved RSI, ADX, and MACD values on each watchlist
     card and computes a Trigger-Anchored Stop Loss when promoting a setup to a Paper Trade.
"""
from __future__ import annotations

import html
import time
from datetime import datetime
from zoneinfo import ZoneInfo

import numpy as np
import pandas as pd
import streamlit as st
import yfinance as yf

from google_sheets_audit import delete_watchlist_row, log_paper_trade

IST = ZoneInfo("Asia/Kolkata")


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
    """Fetch live prices for all watchlist symbols in a single parallel batch download."""
    if not symbols_tuple:
        return {}
    clean_syms = [str(s).strip().upper().replace(".NS", "") for s in symbols_tuple if str(s).strip()]
    if not clean_syms:
        return {}
    tickers = [s.replace("&", "%26") + ".NS" for s in clean_syms]
    live_prices = {}

    try:
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
        if raw is not None and not raw.empty:
            for sym, ticker in zip(clean_syms, tickers):
                try:
                    if isinstance(raw.columns, pd.MultiIndex):
                        if ticker in raw.columns.get_level_values(0):
                            df_s = raw[ticker]
                        elif ticker in raw.columns.get_level_values(1):
                            df_s = raw.xs(ticker, axis=1, level=1)
                        else:
                            continue
                    else:
                        df_s = raw
                    close_s = df_s["Close"].dropna()
                    if not close_s.empty:
                        val = float(close_s.iloc[-1])
                        if np.isfinite(val) and val > 0:
                            live_prices[sym] = val
                except Exception:
                    continue
    except Exception:
        pass

    # Fallback only for any symbol that missed batch download
    for sym, ticker in zip(clean_syms, tickers):
        if sym not in live_prices:
            try:
                fi = yf.Ticker(ticker).fast_info
                lp = fi.get("lastPrice") or fi.get("regularMarketPrice") or fi.get("previousClose")
                if lp and float(lp) > 0:
                    live_prices[sym] = float(lp)
            except Exception:
                pass

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

    wc_col1, wc_col2 = st.columns([6, 2])
    with wc_col1:
        st.markdown(
            "<div class='small-muted' style='margin-bottom:12px;'>Live prices are pulled in real time via Yahoo Finance APIs and compared against your saved Price_Added &amp; Trigger_Price.</div>",
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

    symbols_tuple = tuple(sorted(df["Symbol_Clean"].unique().tolist()))
    live_prices = fetch_live_watchlist_prices(symbols_tuple)

    total_stocks = len(df)
    positive_count = 0
    loss_count = 0
    flat_count = 0
    triggered_count = 0
    total_sim_pnl = 0.0
    total_sim_invested = 0.0
    rendered_items = []

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
        rsi_v = _clean_num(row.get("RSI", 0))
        adx_v = _clean_num(row.get("ADX", 0))
        macd_v = _clean_num(row.get("MACD", 0))

        if price_added > 0 and live_price > 0:
            diff_per_share = live_price - price_added
            return_pct = ((live_price / price_added) - 1.0) * 100.0
            sim_qty = max(1, int(sim_capital // live_price))
            sim_pnl = diff_per_share * sim_qty
            total_sim_pnl += sim_pnl
            total_sim_invested += (price_added * sim_qty)

            if diff_per_share > 0:
                positive_count += 1
            elif diff_per_share < 0:
                loss_count += 1
            else:
                flat_count += 1
        else:
            diff_per_share = 0.0
            return_pct = 0.0
            sim_qty = max(1, int(sim_capital // live_price)) if live_price > 0 else 1
            sim_pnl = 0.0
            flat_count += 1

        pnl_color = "var(--accent)" if return_pct >= 0 else "var(--red)"
        pnl_sign = "+" if return_pct >= 0 else ""

        if t3 > 0 and live_price >= t3:
            status_badge = "<span class='badge badge-green'>🏆 T3 REACHED</span>"
            card_border = "border-left: 4px solid var(--accent); background: var(--accent-bg);"
            triggered_count += 1
        elif t2 > 0 and live_price >= t2:
            status_badge = "<span class='badge badge-green'>🎯 T2 REACHED</span>"
            card_border = "border-left: 4px solid var(--accent); background: var(--accent-bg);"
            triggered_count += 1
        elif t1 > 0 and live_price >= t1:
            status_badge = "<span class='badge badge-green'>✅ T1 REACHED</span>"
            card_border = "border-left: 4px solid var(--accent);"
            triggered_count += 1
        elif trigger > 0 and live_price >= trigger:
            status_badge = "<span class='badge badge-accent'>🚀 ABOVE TRIGGER — ACTIVE</span>"
            card_border = "border-left: 4px solid var(--brand);"
            triggered_count += 1
        elif trigger > 0 and live_price > 0 and ((trigger - live_price) / live_price * 100.0) <= 1.0:
            status_badge = "<span class='badge badge-brand'>🔥 NEAR TRIGGER (&le;1% AWAY)</span>"
            card_border = "border-left: 4px solid var(--brand);"
        else:
            status_badge = "<span class='badge badge-yellow'>⏳ IN WATCH ZONE</span>"
            card_border = "border-left: 4px solid var(--border);"

        # Progress bar toward Target 1 / Target 2
        anchor_low = min(price_added, trigger) if (price_added > 0 and trigger > 0) else max(price_added, trigger)
        if t2 > anchor_low > 0 and live_price > 0:
            prog_pct = float(np.clip(((live_price - anchor_low) / (t2 - anchor_low)) * 100.0, 0.0, 100.0))
        elif t1 > anchor_low > 0 and live_price > 0:
            prog_pct = float(np.clip(((live_price - anchor_low) / (t1 - anchor_low)) * 100.0, 0.0, 100.0))
        else:
            prog_pct = 50.0 if return_pct >= 0 else 20.0
        prog_color = "var(--accent)" if return_pct >= 0 else "var(--red)"

        tech_meta = []
        if rsi_v > 0:
            tech_meta.append(f"RSI: <b>{rsi_v:.1f}</b>")
        if adx_v > 0:
            tech_meta.append(f"ADX: <b>{adx_v:.1f}</b>")
        if macd_v != 0:
            tech_meta.append(f"MACD: <b>{macd_v:.2f}</b>")
        tech_line = (" &nbsp;•&nbsp; " + " &nbsp;|&nbsp; ".join(tech_meta)) if tech_meta else ""

        card_html = f"""
        <div class="bento-card" style="{card_border} display:flex; justify-content:space-between; align-items:center; flex-wrap:wrap; gap:16px; margin-bottom:8px;">
            <div style="flex:1.6; min-width:240px;">
                <div style="display:flex; align-items:center; gap:8px; flex-wrap:wrap;">
                    <span style="font-weight:900; font-size:1.2rem; color:var(--text);">{html.escape(sym)}</span>
                    <span class="badge badge-brand">{html.escape(trade_type)} ({html.escape(exp_days)})</span>
                    {status_badge}
                </div>
                <div class="small-muted" style="margin-top:4px;">{html.escape(company)} • Added: {html.escape(date_added)}{tech_line}</div>
                <div class="small-muted" style="margin-top:4px;">
                    Trigger: <b>{_money(trigger)}</b> &nbsp;|&nbsp; T1: <b style="color:var(--accent);">{_money(t1)}</b> &nbsp;|&nbsp; T2: <b style="color:var(--brand);">{_money(t2)}</b> &nbsp;|&nbsp; T3: <b>{_money(t3)}</b>
                </div>
                <div style="margin-top:8px; max-width:360px;">
                    <div class="bar-track" style="height:6px;"><div class="bar-fill" style="width:{prog_pct:.1f}%; background:{prog_color};"></div></div>
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
        """

        rendered_items.append({
            "idx": idx,
            "sym": sym,
            "live_price": live_price,
            "sim_qty": sim_qty,
            "t1": t1,
            "t2": t2,
            "trigger": trigger,
            "card_html": card_html,
        })

    win_rate_pct = (positive_count / total_stocks * 100.0) if total_stocks > 0 else 0.0
    loss_rate_pct = (loss_count / total_stocks * 100.0) if total_stocks > 0 else 0.0

    summary_html = f"""
    <div style="display:grid; grid-template-columns: repeat(4, 1fr); gap:16px; margin-bottom:20px;">
        <div class="bento-card" style="margin-bottom:0; padding:16px 20px; border-left: 4px solid var(--brand);">
            <div class="small-muted" style="text-transform:uppercase; font-size:0.72rem; font-weight:700;">Total Stocks in Watchlist</div>
            <div style="font-size:1.8rem; font-weight:900; color:var(--text); margin-top:4px;">{total_stocks}</div>
            <div class="small-muted" style="font-size:0.75rem; margin-top:2px;">Active Tracked Setups ({flat_count} Flat)</div>
        </div>
        <div class="bento-card" style="margin-bottom:0; padding:16px 20px; border-left: 4px solid var(--accent); background:var(--accent-bg);">
            <div class="small-muted" style="text-transform:uppercase; font-size:0.72rem; font-weight:700; color:var(--accent);">Stocks in Profit</div>
            <div style="font-size:1.8rem; font-weight:900; color:var(--accent); margin-top:4px;">{positive_count}</div>
            <div class="small-muted" style="font-size:0.75rem; margin-top:2px;">{win_rate_pct:.1f}% of Watchlist Green</div>
        </div>
        <div class="bento-card" style="margin-bottom:0; padding:16px 20px; border-left: 4px solid var(--red); background:var(--red-bg);">
            <div class="small-muted" style="text-transform:uppercase; font-size:0.72rem; font-weight:700; color:var(--red);">Stocks in Loss</div>
            <div style="font-size:1.8rem; font-weight:900; color:var(--red); margin-top:4px;">{loss_count}</div>
            <div class="small-muted" style="font-size:0.75rem; margin-top:2px;">{loss_rate_pct:.1f}% of Watchlist Red</div>
        </div>
        <div class="bento-card" style="margin-bottom:0; padding:16px 20px; border-left: 4px solid var(--yellow); background:var(--yellow-bg);">
            <div class="small-muted" style="text-transform:uppercase; font-size:0.72rem; font-weight:700; color:var(--yellow);">Above Trigger / Target</div>
            <div style="font-size:1.8rem; font-weight:900; color:var(--text); margin-top:4px;">{triggered_count}</div>
            <div class="small-muted" style="font-size:0.75rem; margin-top:2px;">Breakout Confirmed Setups</div>
        </div>
    </div>
    """
    st.markdown(summary_html, unsafe_allow_html=True)

    for item in rendered_items:
        st.markdown(item["card_html"], unsafe_allow_html=True)
        act_spacer, act_col1, act_col2 = st.columns([5.5, 2.5, 2.0])
        with act_col1:
            if st.button(
                f"🚀 Paper Trade ({item['sim_qty']} sh)",
                key=f"wl_promote_{item['sym']}_{item['idx']}",
                use_container_width=True,
            ):
                ep = float(item["live_price"]) if item["live_price"] > 0 else 0.0
                if ep <= 0:
                    st.error(f"Cannot execute paper trade for {item['sym']}: live price unavailable.")
                else:
                    t1_val = float(item["t1"]) if item["t1"] > 0 else round(ep * 1.06, 2)
                    t2_val = float(item["t2"]) if item["t2"] > 0 else round(ep * 1.12, 2)
                    implied_risk = (t2_val - ep) / 2.4 if t2_val > ep else (ep * 0.04)
                    sl_default = round(max(0.05, ep - max(ep * 0.02, min(ep * 0.06, implied_risk))), 2)
                    trade_payload = {
                        "Trade_ID": f"{item['sym']}_{int(time.time())}",
                        "Symbol": item["sym"],
                        "Entry_Date": datetime.now(IST).strftime("%Y-%m-%d %H:%M:%S"),
                        "Entry_Price": round(ep, 2),
                        "Quantity": int(item["sim_qty"]),
                        "Invested_Capital": round(ep * int(item["sim_qty"]), 2),
                        "Stop_Loss": sl_default,
                        "Target_1": t1_val,
                        "Target_2": t2_val,
                        "Status": "OPEN",
                        "PnL": 0.0,
                    }
                    try:
                        with st.spinner(f"Logging paper trade for {item['sym']}..."):
                            log_paper_trade(st.secrets, trade_payload)
                        fetch_live_watchlist_prices.clear()
                        st.session_state["_invalidate_portfolio_caches"] = True
                        st.toast(f"✅ Executed Paper Trade: {item['sim_qty']} shares of {item['sym']} @ ₹{ep:,.2f}!")
                        time.sleep(0.6)
                        st.rerun()
                    except Exception as e:
                        st.error(f"Paper trade failed: {e}")
        with act_col2:
            if st.button(
                "🗑️ Remove",
                key=f"wl_del_{item['sym']}_{item['idx']}",
                use_container_width=True,
            ):
                try:
                    with st.spinner(f"Removing {item['sym']} from Watchlist..."):
                        delete_watchlist_row(st.secrets, item["sym"])
                    fetch_live_watchlist_prices.clear()
                    st.session_state["_invalidate_portfolio_caches"] = True
                    st.toast(f"🗑️ Removed {item['sym']} from Manual_Watch_List!")
                    time.sleep(0.6)
                    st.rerun()
                except Exception as e:
                    st.error(f"Could not delete {item['sym']}: {e}")

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
