"""Streamlit UI for the NIFTY Breakout & Institutional Anti-Trap Scanner (v2 Edition)."""
from __future__ import annotations

from datetime import datetime
import time
from zoneinfo import ZoneInfo

import numpy as np
import pandas as pd
import streamlit as st

import scanner
import audit_logger
import google_sheets_audit
import performance_tracker
import audit_analysis
import live_watchlist

IST = ZoneInfo("Asia/Kolkata")

st.set_page_config(
    page_title="NIFTY Breakout & Anti-Trap Scanner (v2)",
    page_icon="🚀",
    layout="wide",
)

st.title("🚀 NIFTY Breakout & Institutional Anti-Trap Scanner (v2)")
st.markdown("Automated quantitative breakout scanner, 68-column Google Sheets audit logging, live watchlist, and paper portfolio tracker.")

# --- SIDEBAR CONFIGURATION ---
st.sidebar.header("⚙️ Scanner Controls & Settings")
scanner_period = st.sidebar.selectbox("Historical Period", ["1y", "2y", "5y"], index=1)
max_distance = st.sidebar.slider("Max Distance from Breakout (%)", 2.0, 20.0, 10.0, 0.5)
top_n_results = st.sidebar.slider("Top Results to Display", 10, 100, 25, 5)

st.sidebar.markdown("---")
st.sidebar.subheader("📊 Google Sheets Audit")

def get_secrets():
    try:
        return st.secrets
    except Exception:
        return {}

secrets = get_secrets()

if st.sidebar.button("🚀 SCAN MARKET"):
    with st.spinner("Downloading universe, checking NIFTY/sector RS, and evaluating anti-trap metrics..."):
        try:
            results = scanner.scan_universe(max_distance=max_distance, period=scanner_period, top_n=top_n_results)
            st.session_state["scan_results"] = results
            st.session_state["scan_timestamp"] = datetime.now(IST).strftime("%Y-%m-%d %H:%M:%S IST")
            st.success(f"Scan complete! Found {len(results)} qualifying breakout setups.")
        except Exception as e:
            st.error(f"Scan failed: {e}")

# --- MAIN NAVIGATION TABS ---
tab_scan, tab_audit, tab_watchlist, tab_portfolio, tab_analysis = st.tabs([
    "🔍 Market Scan", "📊 Audit & Logs", "👁️ Live Watchlist", "📄 Paper Portfolio", "📈 Combination Analysis"
])

# --- TAB 1: MARKET SCAN ---
with tab_scan:
    st.header("Top Ranked Breakout Setups")
    if "scan_results" in st.session_state and not st.session_state["scan_results"].empty:
        results = st.session_state["scan_results"]
        timestamp = st.session_state.get("scan_timestamp", "")
        st.info(f"Last scanned at: {timestamp} (Period: {scanner_period}, Max Distance: {max_distance}%)")
        
        # Display summary metrics
        col1, col2, col3 = st.columns(3)
        col1.metric("Qualified Setups", len(results))
        col2.metric("Confirmed Breakouts", len(results[results["status"] == "BREAKOUT CONFIRMED"]))
        col3.metric("Clean Anti-Trap Setups", len(results[~results["is_distribution_trap"] & ~results["false_breakout"]]))
        
        st.dataframe(results, use_container_width=True)
        
        # Audit Collection Button
        if st.button("📊 COLLECT AUDIT & SYNC GOOGLE SHEET"):
            with st.spinner("Preparing 68-column audit snapshot and syncing to Google Sheets..."):
                try:
                    run_id = google_sheets_audit.new_run_id()
                    snapshot_df = audit_logger.build_scan_snapshot(
                        results, run_id=run_id, scan_timestamp_ist=timestamp,
                        scanner_period=scanner_period, max_distance_pct=max_distance
                    )
                    # Save locally
                    audit_logger.append_scan_snapshot(
                        results, scan_timestamp_ist=timestamp, scanner_period=scanner_period,
                        max_distance_pct=max_distance, run_id=run_id
                    )
                    # Sync to Google Sheets
                    res = google_sheets_audit.append_audit_batch(
                        secrets, snapshot_df, run_id=run_id, scan_timestamp_ist=timestamp,
                        scanner_period=scanner_period, max_distance_pct=max_distance
                    )
                    st.success(f"Successfully logged {res.get('rows', len(snapshot_df))} signals to Google Sheets! Run ID: {run_id}")
                except Exception as e:
                    st.error(f"Audit sync failed: {e}")
    else:
        st.warning("No active scan results in memory. Click '🚀 SCAN MARKET' in the sidebar to run a scan.")

# --- TAB 2: AUDIT & LOGS ---
with tab_audit:
    st.header("Audit Runs & Google Sheets Status")
    try:
        signals_df = google_sheets_audit.read_audit_signals(secrets)
        if not signals_df.empty:
            st.metric("Total Logged Signals in Google Sheet", len(signals_df))
            st.dataframe(signals_df.tail(50), use_container_width=True)
        else:
            st.info("No audit signals found in the Google Sheet yet.")
    except Exception as e:
        st.warning(f"Could not load audit signals from Google Sheet: {e}")

# --- TAB 3: LIVE WATCHLIST ---
with tab_watchlist:
    st.header("Live Manual Watchlist & Performance Tracker")
    try:
        watchlist_df = google_sheets_audit.read_watchlist(secrets)
        if not watchlist_df.empty:
            # Automated live PnL calculation helper
            def compute_live_pnl(df):
                symbols = [str(s).strip() + ".NS" for s in df["Symbol"].dropna().unique()]
                if not symbols: return df
                try:
                    import yfinance as yf
                    data = yf.download(symbols, period="2d", interval="1d", progress=False, group_by="ticker")
                    current_prices = {}
                    for s in df["Symbol"].dropna().unique():
                        ticker = str(s).strip() + ".NS"
                        try:
                            hist = data if len(symbols) == 1 else data[ticker]
                            if not hist.empty: current_prices[ticker] = float(hist['Close'].iloc[-1])
                        except Exception: pass
                    df["Current_Price"] = df["Symbol"].apply(lambda x: current_prices.get(str(x).strip() + ".NS", None))
                    if "Price_Added" in df.columns:
                        df["Return_Pct"] = ((df["Current_Price"] - df["Price_Added"]) / df["Price_Added"]) * 100.0
                        df["Status"] = df["Return_Pct"].apply(lambda r: "🟢 PROFIT" if pd.notna(r) and r >= 0 else "🔴 LOSS" if pd.notna(r) else "⏳ PENDING")
                except Exception:
                    pass
                return df

            live_watch = compute_live_pnl(watchlist_df)
            st.dataframe(live_watch, use_container_width=True)
        else:
            st.info("No watchlist items found.")
    except Exception as e:
        st.warning(f"Could not load watchlist: {e}")

# --- TAB 4: PAPER PORTFOLIO ---
with tab_portfolio:
    st.header("Automated Paper Portfolio Tracker")
    try:
        paper_df = google_sheets_audit.get_paper_trades(secrets)
        if not paper_df.empty:
            def compute_paper_pnl(df):
                symbols = [str(s).strip() + ".NS" for s in df["Symbol"].dropna().unique()]
                if not symbols: return df
                try:
                    import yfinance as yf
                    data = yf.download(symbols, period="2d", interval="1d", progress=False, group_by="ticker")
                    current_prices = {}
                    for s in df["Symbol"].dropna().unique():
                        ticker = str(s).strip() + ".NS"
                        try:
                            hist = data if len(symbols) == 1 else data[ticker]
                            if not hist.empty: current_prices[ticker] = float(hist['Close'].iloc[-1])
                        except Exception: pass
                    df["Current_Price"] = df["Symbol"].apply(lambda x: current_prices.get(str(x).strip() + ".NS", None))
                    if "Entry_Price" in df.columns and "Quantity" in df.columns:
                        df["Unrealized_PnL"] = (df["Current_Price"] - df["Entry_Price"]) * df["Quantity"]
                        df["Return_Pct"] = ((df["Current_Price"] - df["Entry_Price"]) / df["Entry_Price"]) * 100.0
                        df["Performance_Status"] = df["Return_Pct"].apply(lambda r: "🟢 PROFIT" if pd.notna(r) and r >= 0 else "🔴 LOSS" if pd.notna(r) else "⏳ PENDING")
                except Exception:
                    pass
                return df

            live_paper = compute_paper_pnl(paper_df)
            total_invested = live_paper["Invested_Capital"].sum() if "Invested_Capital" in live_paper.columns else 0
            total_pnl = live_paper["Unrealized_PnL"].sum() if "Unrealized_PnL" in live_paper.columns else 0
            
            c1, c2 = st.columns(2)
            c1.metric("Total Invested Capital", f"₹{total_invested:,.2f}")
            c2.metric("Total Unrealized PnL", f"₹{total_pnl:,.2f}", delta=f"{total_pnl:,.2f}")
            
            st.dataframe(live_paper, use_container_width=True)
        else:
            st.info("No paper trades recorded yet.")
    except Exception as e:
        st.warning(f"Could not load paper trades: {e}")

# --- TAB 5: COMBINATION ANALYSIS ---
with tab_analysis:
    st.header("Bounded Combination & Multi-Factor Analysis")
    st.markdown("Evaluate historical performance rules across RSI, MACD, ADX, and institutional delivery metrics.")
    if st.button("📈 RUN COMBINATION ANALYSIS"):
        with st.spinner("Analyzing multi-factor combinations and win rates..."):
            try:
                signals_df = google_sheets_audit.read_audit_signals(secrets)
                perf_df = google_sheets_audit.read_daily_performance(secrets)
                if not signals_df.empty and not perf_df.empty:
                    outcomes, rep = audit_analysis.build_completed_outcomes(signals_df, perf_df)
                    analysis_res = audit_analysis.analyze_outcome_combinations(outcomes, outcome_col="T1_Hit")
                    st.dataframe(analysis_res, use_container_width=True)
                    google_sheets_audit.append_analysis_rows(secrets, analysis_res)
                    st.success("Analysis complete and synced to Google Sheets Analysis_Results tab!")
                else:
                    st.warning("Insufficient signal audit or performance data to run combination analysis.")
            except Exception as e:
                st.error(f"Analysis failed: {e}")
