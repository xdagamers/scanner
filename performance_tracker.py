"""Historical OHLC backfill and 20-trading-session audit reconciliation.

This module is independent from scanner.py. It does not alter any scan,
score, rank, filter, resistance, target or stop calculation. Daily OHLC is read
as raw market prices; split actions are handled explicitly so recorded signal
levels remain comparable to the prices actually traded after a split.
"""
from __future__ import annotations

from datetime import date, datetime, timedelta
from typing import Callable
from zoneinfo import ZoneInfo

import numpy as np
import pandas as pd

IST = ZoneInfo("Asia/Kolkata")
OHLC_COLUMNS = ["Open", "High", "Low", "Close"]
PERFORMANCE_COLUMNS = [
    # Original columns retained in order for safe migration of the existing tab.
    "Signal_ID", "Scan_Date", "Tracking_Day", "Tracking_Date",
    "Open", "High", "Low", "Close", "Breakout_Trigger", "Target_1",
    "Target_2", "Target_3", "Stop", "Breakout_Hit", "T1_Hit", "T2_Hit",
    "T3_Hit", "Stop_Hit", "Best_Gain_Pct", "Max_Drawdown_Pct", "Status",
    "Data_Quality", "Signal_Price", "Close_Return_Pct", "Breakout_First_Day",
    "T1_First_Day", "T2_First_Day", "T3_First_Day", "Stop_First_Day",
    "First_Event", "First_Event_Day", "Data_Source", "Updated_At_IST",
    "Cumulative_Split_Ratio", "Signal_Price_Current_Basis",
    "Breakout_Trigger_Current_Basis", "Target_1_Current_Basis",
    "Target_2_Current_Basis", "Target_3_Current_Basis", "Stop_Current_Basis",
]


def latest_completed_market_date(now: datetime | None = None) -> date:
    """Use today's OHLC only after 16:15 IST; otherwise cap at yesterday."""
    now = now or datetime.now(IST)
    local = now.astimezone(IST) if now.tzinfo else now.replace(tzinfo=IST)
    if local.hour < 16 or (local.hour == 16 and local.minute < 15):
        return local.date() - timedelta(days=1)
    return local.date()


def _to_date(value) -> date | None:
    """Parse Sheets dates without shifting naive YYYY-MM-DD values by timezone."""
    if value is None or (isinstance(value, float) and np.isnan(value)):
        return None
    try:
        ts = pd.Timestamp(value)
        if pd.isna(ts):
            return None
        if ts.tzinfo is not None:
            ts = ts.tz_convert("Asia/Kolkata")
        return ts.date()
    except Exception:
        return None


def _num(value) -> float:
    try:
        x = float(value)
        return x if np.isfinite(x) else np.nan
    except Exception:
        return np.nan


def _ticker_for_symbol(symbol: str) -> str:
    # Matches scanner.py's current ticker conversion.
    return str(symbol).strip().replace("&", "%26") + ".NS"


def _extract_ticker_frame(downloaded: pd.DataFrame, ticker: str) -> pd.DataFrame | None:
    if downloaded is None or downloaded.empty:
        return None
    df = downloaded
    if isinstance(df.columns, pd.MultiIndex):
        found = False
        for level in range(df.columns.nlevels):
            vals = [str(v) for v in df.columns.get_level_values(level).unique()]
            if ticker in vals:
                try:
                    df = df.xs(ticker, axis=1, level=level, drop_level=True)
                    found = True
                    break
                except Exception:
                    continue
        if not found:
            for level in range(df.columns.nlevels):
                vals = {str(v).strip().title() for v in df.columns.get_level_values(level).unique()}
                if set(OHLC_COLUMNS).issubset(vals):
                    df = df.copy()
                    df.columns = df.columns.get_level_values(level)
                    found = True
                    break
        if not found:
            return None
    normalized = {str(c).strip().title(): c for c in df.columns}
    if not all(c in normalized for c in OHLC_COLUMNS):
        return None
    out = df[[normalized[c] for c in OHLC_COLUMNS]].copy()
    out.columns = OHLC_COLUMNS
    # Keep raw traded OHLC plus split events, if available. This prevents future
    # dividend adjustments from retrospectively shifting stored signal targets.
    split_column = normalized.get("Stock Splits")
    if split_column is not None:
        out["Stock Splits"] = pd.to_numeric(df[split_column], errors="coerce").fillna(0.0).to_numpy()
    else:
        out["Stock Splits"] = 0.0
    for col in OHLC_COLUMNS:
        out[col] = pd.to_numeric(out[col], errors="coerce")
    out = out.dropna(subset=OHLC_COLUMNS)
    if out.empty:
        return None
    idx = pd.to_datetime(out.index, errors="coerce")
    if getattr(idx, "tz", None) is not None:
        idx = idx.tz_convert("Asia/Kolkata").tz_localize(None)
    out.index = pd.DatetimeIndex(idx).normalize()
    out = out[~out.index.isna()]
    out = out[~out.index.duplicated(keep="last")].sort_index()
    out.index.name = "Date"
    return out if not out.empty else None


def fetch_ohlc_histories(
    signals: pd.DataFrame,
    as_of_date: date | None = None,
    chunk_size: int = 15,
    progress_callback: Callable[[int, int, str], None] | None = None,
) -> tuple[dict[str, pd.DataFrame], list[str], list[date], str]:
    """Fetch OHLC for unique signal symbols and an index-derived trading calendar.

    Returns histories, symbols with no usable OHLC, market session dates, and
    calendar source. The index calendar allows missing stock candles to be
    flagged instead of silently shifting that stock's tracking-day numbering.
    """
    if signals is None or signals.empty or "Symbol" not in signals.columns:
        return {}, [], [], "no_signals"
    try:
        import yfinance as yf
    except ImportError as exc:
        raise RuntimeError("The yfinance package is missing. Add yfinance to requirements.txt and redeploy.") from exc

    as_of_date = as_of_date or latest_completed_market_date()
    starts = [_to_date(v) for v in signals.get("Scan_Date", [])]
    starts = [d for d in starts if d is not None]
    if not starts:
        return {}, sorted(set(signals["Symbol"].dropna().astype(str))), [], "invalid_scan_dates"
    start_date = min(starts) + timedelta(days=1)
    if start_date > as_of_date:
        return {}, [], [], "no_post_signal_sessions_yet"

    symbols = sorted({str(s).strip() for s in signals["Symbol"].dropna() if str(s).strip()})
    ticker_to_symbol = {_ticker_for_symbol(s): s for s in symbols}
    tickers = list(ticker_to_symbol)
    histories: dict[str, pd.DataFrame] = {}
    end_exclusive = as_of_date + timedelta(days=1)
    chunks = [tickers[i:i + max(1, chunk_size)] for i in range(0, len(tickers), max(1, chunk_size))]

    for chunk_num, chunk in enumerate(chunks, start=1):
        if progress_callback:
            progress_callback(chunk_num - 1, len(chunks) + 1, f"Downloading OHLC batch {chunk_num}/{len(chunks)}")
        kwargs = dict(tickers=chunk, start=start_date.isoformat(), end=end_exclusive.isoformat(),
                      interval="1d", auto_adjust=False, actions=True, progress=False, threads=False, group_by="ticker")
        try:
            try:
                downloaded = yf.download(**kwargs, multi_level_index=True, timeout=25)
            except TypeError:
                downloaded = yf.download(**kwargs)
        except Exception:
            downloaded = None

        missing_in_chunk = []
        for ticker in chunk:
            frame = _extract_ticker_frame(downloaded, ticker)
            if frame is not None:
                histories[ticker_to_symbol[ticker]] = frame
            else:
                missing_in_chunk.append(ticker)

        # Retry missing tickers individually, since Yahoo batch responses can
        # omit one or more symbols even when other columns are returned.
        for ticker in missing_in_chunk:
            one_kwargs = dict(kwargs)
            one_kwargs["tickers"] = ticker
            try:
                try:
                    single = yf.download(**one_kwargs, multi_level_index=True, timeout=20)
                except TypeError:
                    single = yf.download(**one_kwargs)
                frame = _extract_ticker_frame(single, ticker)
                if frame is not None:
                    histories[ticker_to_symbol[ticker]] = frame
            except Exception:
                continue
        if progress_callback:
            progress_callback(chunk_num, len(chunks) + 1, f"Processed OHLC batch {chunk_num}/{len(chunks)}")

    missing = sorted(set(symbols) - set(histories))

    # Fetch the NIFTY 50 daily index as the trading-session calendar. If this
    # endpoint fails, fall back to the union of dates returned for stock OHLC;
    # the UI reports which calendar source was used.
    calendar: list[date] = []
    calendar_source = "NIFTY 50 index (^NSEI)"
    if progress_callback:
        progress_callback(len(chunks), len(chunks) + 1, "Fetching trading-session calendar from NIFTY 50…")
    try:
        index_kwargs = dict(tickers="^NSEI", start=start_date.isoformat(), end=end_exclusive.isoformat(),
                            interval="1d", auto_adjust=False, actions=True, progress=False, threads=False, group_by="ticker")
        try:
            index_data = yf.download(**index_kwargs, multi_level_index=True, timeout=20)
        except TypeError:
            index_data = yf.download(**index_kwargs)
        index_frame = _extract_ticker_frame(index_data, "^NSEI")
        if index_frame is not None:
            calendar = sorted({stamp.date() for stamp in index_frame.index if stamp.date() <= as_of_date})
    except Exception:
        calendar = []
    if not calendar:
        calendar_source = "Fallback: union of stock OHLC dates"
        calendar = sorted({stamp.date() for frame in histories.values() for stamp in frame.index if stamp.date() <= as_of_date})
    if progress_callback:
        progress_callback(len(chunks) + 1, len(chunks) + 1, f"Trading calendar ready: {len(calendar)} sessions ({calendar_source})")
    return histories, missing, calendar, calendar_source


def _yes(value: bool) -> str:
    return "YES" if value else "NO"


def build_performance_rows(
    signals: pd.DataFrame,
    histories: dict[str, pd.DataFrame],
    existing_performance: pd.DataFrame | None = None,
    as_of_date: date | None = None,
    market_sessions: list[date] | None = None,
    calendar_source: str = "provided market session calendar",
    now: datetime | None = None,
) -> tuple[pd.DataFrame, dict]:
    """Build/reconcile up to 20 tracking days per signal, including explicit gaps.

    Every market session after the signal date has a stable day number. If a
    stock candle is missing, a blank placeholder is recorded with Data_Quality
    set to MISSING_OHLC_FOR_MARKET_SESSION. When data arrives later, that row and
    dependent incomplete rows are repaired in place by the Apps Script endpoint.
    """
    now = now or datetime.now(IST)
    as_of_date = as_of_date or latest_completed_market_date(now)

    # Existing OK keys are immutable/idempotent. Missing/incomplete keys are
    # regenerated so late provider data can repair the outcome and its metrics.
    existing_quality: dict[tuple[str, int], str] = {}
    if existing_performance is not None and not existing_performance.empty:
        for _, old in existing_performance.iterrows():
            sid = str(old.get("Signal_ID", "")).strip()
            try:
                day_num = int(float(old.get("Tracking_Day")))
            except Exception:
                continue
            quality = str(old.get("Data_Quality", "OK") or "OK").strip().upper()
            if sid and day_num > 0:
                existing_quality[(sid, day_num)] = quality

    empty_report = {
        "signals": int(len(signals)) if signals is not None else 0,
        "signals_with_history": 0, "signals_without_history": 0,
        "signals_complete_20d": 0, "signals_window_elapsed_20d": 0,
        "rows_generated": 0, "rows_skipped_existing": 0,
        "missing_symbols": [], "missing_signals": [], "missing_candles": [],
        "incomplete_signals": [], "pending_no_future_sessions": [],
        "expected_keys": [], "as_of_date": as_of_date.isoformat(),
        "calendar_source": calendar_source,
    }
    if signals is None or signals.empty:
        return pd.DataFrame(columns=PERFORMANCE_COLUMNS), empty_report

    sessions = sorted({_to_date(d) for d in (market_sessions or []) if _to_date(d) is not None and _to_date(d) <= as_of_date})
    if not sessions:
        sessions = sorted({stamp.date() for frame in histories.values() for stamp in frame.index if stamp.date() <= as_of_date})
        calendar_source = "Fallback: union of stock OHLC dates"

    rows: list[dict] = []
    missing_signals: list[dict] = []
    pending_no_future: list[dict] = []
    missing_candles: list[dict] = []
    incomplete_signals: list[dict] = []
    with_history_ids: set[str] = set()
    complete_20d = 0
    elapsed_20d = 0
    skipped_existing = 0
    expected_keys: set[tuple[str, int]] = set()
    timestamp = (now.astimezone(IST) if now.tzinfo else now.replace(tzinfo=IST)).strftime("%Y-%m-%d %H:%M:%S IST")

    for _, signal in signals.iterrows():
        sid = str(signal.get("Signal_ID", "")).strip()
        symbol = str(signal.get("Symbol", "")).strip()
        scan_date = _to_date(signal.get("Scan_Date"))
        if not sid or not symbol or scan_date is None:
            missing_signals.append({"Signal_ID": sid or "(missing ID)", "Symbol": symbol, "Reason": "Missing Signal_ID, Symbol or valid Scan_Date"})
            continue
        if as_of_date <= scan_date:
            pending_no_future.append({"Signal_ID": sid, "Symbol": symbol, "Reason": "No completed trading session after this signal date yet"})
            continue

        expected_dates = [d for d in sessions if scan_date < d <= as_of_date][:20]
        if not expected_dates:
            pending_no_future.append({"Signal_ID": sid, "Symbol": symbol, "Reason": "No market sessions available after this signal date yet"})
            continue

        history = histories.get(symbol)
        date_lookup = {}
        if history is not None and not history.empty:
            frame = history.copy()
            frame.index = pd.to_datetime(frame.index, errors="coerce")
            frame = frame[~frame.index.isna()].sort_index()
            date_lookup = {stamp.date(): candle for stamp, candle in frame.iterrows()}

        price = _num(signal.get("Price"))
        trigger = _num(signal.get("Breakout_Trigger"))
        t1, t2, t3, stop = (_num(signal.get(k)) for k in ("Target_1", "Target_2", "Target_3", "Stop"))
        has_expected_candle = any(d in date_lookup for d in expected_dates)
        if has_expected_candle:
            with_history_ids.add(sid)
        else:
            missing_signals.append({"Signal_ID": sid, "Symbol": symbol, "Reason": "No OHLC history available for expected post-signal sessions; placeholder rows created"})

        breakout_day = t1_day = t2_day = t3_day = stop_day = None
        # Normalize post-signal prices to the original signal-share basis. This
        # makes fixed targets comparable across stock splits.
        cumulative_split_ratio = 1.0
        max_high = price if np.isfinite(price) else np.nan
        prior_peak = price if np.isfinite(price) else np.nan
        worst_drawdown = 0.0
        first_event = "NONE"
        first_event_day = None
        first_missing_day = None
        signal_rows: list[dict] = []
        valid_ohlc_days = 0

        for tracking_day, tracking_date in enumerate(expected_dates, start=1):
            candle = date_lookup.get(tracking_date)
            available = candle is not None
            if available:
                op, high, low, close = (_num(candle.get(c)) for c in OHLC_COLUMNS)
                available = all(np.isfinite(v) for v in (op, high, low, close))
            else:
                op = high = low = close = np.nan

            if not available:
                if first_missing_day is None:
                    first_missing_day = tracking_day
                missing_candles.append({
                    "Signal_ID": sid, "Symbol": symbol, "Tracking_Day": tracking_day,
                    "Tracking_Date": tracking_date.isoformat(), "Reason": "OHLC candle missing from provider; will retry on next update",
                })
                quality = "MISSING_OHLC_FOR_MARKET_SESSION"
                status = "MISSING_OHLC_RETRY"
            else:
                valid_ohlc_days += 1
                split_event = _num(candle.get("Stock Splits", 0.0))
                if np.isfinite(split_event) and split_event > 0:
                    cumulative_split_ratio *= split_event

                # The Sheet retains raw prices; calculations use original signal
                # price basis. For a 2-for-1 split, for example, 55 raw becomes
                # 110 in the original-share basis after the split.
                norm_high = high * cumulative_split_ratio if np.isfinite(high) else np.nan
                norm_low = low * cumulative_split_ratio if np.isfinite(low) else np.nan
                if np.isfinite(norm_high):
                    max_high = max(max_high, norm_high) if np.isfinite(max_high) else norm_high
                if breakout_day is None and np.isfinite(trigger) and np.isfinite(norm_high) and norm_high >= trigger:
                    breakout_day = tracking_day
                if t1_day is None and np.isfinite(t1) and np.isfinite(norm_high) and norm_high >= t1:
                    t1_day = tracking_day
                if t2_day is None and np.isfinite(t2) and np.isfinite(norm_high) and norm_high >= t2:
                    t2_day = tracking_day
                if t3_day is None and np.isfinite(t3) and np.isfinite(norm_high) and norm_high >= t3:
                    t3_day = tracking_day
                stop_today = np.isfinite(stop) and np.isfinite(norm_low) and norm_low <= stop
                if stop_day is None and stop_today:
                    stop_day = tracking_day
                target_today = any(np.isfinite(level) and np.isfinite(norm_high) and norm_high >= level for level in (t1, t2, t3))
                if first_event == "NONE":
                    if stop_today and target_today:
                        first_event, first_event_day = "AMBIGUOUS_SAME_DAY", tracking_day
                    elif stop_today:
                        first_event, first_event_day = "STOP_FIRST", tracking_day
                    elif target_today:
                        first_event, first_event_day = "TARGET_FIRST", tracking_day

                # Conservative intraday drawdown estimate: treat the daily high as
                # a possible peak before its low. Daily OHLC cannot establish order.
                day_peak = max(prior_peak, norm_high) if np.isfinite(prior_peak) and np.isfinite(norm_high) else (norm_high if np.isfinite(norm_high) else prior_peak)
                if np.isfinite(norm_low) and np.isfinite(day_peak) and day_peak > 0:
                    worst_drawdown = min(worst_drawdown, (norm_low / day_peak - 1.0) * 100.0)
                prior_peak = day_peak
                quality = "OK"
                status = first_event if first_event != "NONE" else "OPEN_NO_TARGET_OR_STOP_YET"

            # An unresolved earlier missing candle makes the order and cumulative
            # path after that date provisional until the next update repairs it.
            if first_missing_day is not None and tracking_day > first_missing_day and available:
                quality = "INCOMPLETE_20D_HISTORY"
                status = "INCOMPLETE_20D_HISTORY"
            if tracking_day == 20:
                if quality != "OK":
                    status = "COMPLETED_20D_BUT_DATA_INCOMPLETE"
                elif first_event == "TARGET_FIRST":
                    status = "COMPLETED_20D_TARGET_FIRST"
                elif first_event == "STOP_FIRST":
                    status = "COMPLETED_20D_STOP_FIRST"
                elif first_event == "AMBIGUOUS_SAME_DAY":
                    status = "COMPLETED_20D_AMBIGUOUS_FIRST_EVENT"
                else:
                    status = "COMPLETED_20D_NO_TARGET_OR_STOP"

            record = {
                "Signal_ID": sid, "Scan_Date": scan_date.isoformat(),
                "Tracking_Day": tracking_day, "Tracking_Date": tracking_date.isoformat(),
                "Open": op if available else "", "High": high if available else "",
                "Low": low if available else "", "Close": close if available else "",
                "Breakout_Trigger": trigger, "Target_1": t1, "Target_2": t2, "Target_3": t3, "Stop": stop,
                "Breakout_Hit": _yes(breakout_day is not None), "T1_Hit": _yes(t1_day is not None),
                "T2_Hit": _yes(t2_day is not None), "T3_Hit": _yes(t3_day is not None),
                "Stop_Hit": _yes(stop_day is not None),
                "Best_Gain_Pct": ((max_high / price) - 1.0) * 100.0 if np.isfinite(max_high) and np.isfinite(price) and price > 0 else "",
                "Max_Drawdown_Pct": worst_drawdown,
                "Status": status, "Data_Quality": quality,
                "Signal_Price": price if np.isfinite(price) else "",
                "Close_Return_Pct": ((close * cumulative_split_ratio / price) - 1.0) * 100.0 if available and np.isfinite(close) and np.isfinite(price) and price > 0 else "",
                "Breakout_First_Day": breakout_day if breakout_day is not None else "",
                "T1_First_Day": t1_day if t1_day is not None else "",
                "T2_First_Day": t2_day if t2_day is not None else "",
                "T3_First_Day": t3_day if t3_day is not None else "",
                "Stop_First_Day": stop_day if stop_day is not None else "",
                "First_Event": first_event, "First_Event_Day": first_event_day if first_event_day is not None else "",
                "Data_Source": "Yahoo Finance raw daily OHLC; split-normalized comparisons", "Updated_At_IST": timestamp,
                "Cumulative_Split_Ratio": cumulative_split_ratio,
                "Signal_Price_Current_Basis": price / cumulative_split_ratio if np.isfinite(price) and cumulative_split_ratio > 0 else "",
                "Breakout_Trigger_Current_Basis": trigger / cumulative_split_ratio if np.isfinite(trigger) and cumulative_split_ratio > 0 else "",
                "Target_1_Current_Basis": t1 / cumulative_split_ratio if np.isfinite(t1) and cumulative_split_ratio > 0 else "",
                "Target_2_Current_Basis": t2 / cumulative_split_ratio if np.isfinite(t2) and cumulative_split_ratio > 0 else "",
                "Target_3_Current_Basis": t3 / cumulative_split_ratio if np.isfinite(t3) and cumulative_split_ratio > 0 else "",
                "Stop_Current_Basis": stop / cumulative_split_ratio if np.isfinite(stop) and cumulative_split_ratio > 0 else "",
            }
            signal_rows.append(record)
            expected_keys.add((sid, tracking_day))

        # If any required OHLC is missing, all later rows are provisional so a
        # subsequent backfill can recalculate the cumulative metrics correctly.
        missing_day_nums = [r["Tracking_Day"] for r in signal_rows if r["Data_Quality"] == "MISSING_OHLC_FOR_MARKET_SESSION"]
        if missing_day_nums:
            first_gap = min(missing_day_nums)
            for record in signal_rows:
                if int(record["Tracking_Day"]) > first_gap and record["Data_Quality"] == "OK":
                    record["Data_Quality"] = "INCOMPLETE_20D_HISTORY"
                    record["Status"] = "INCOMPLETE_20D_HISTORY"
            incomplete_signals.append({
                "Signal_ID": sid, "Symbol": symbol, "Available_Days": valid_ohlc_days,
                "Missing_Tracking_Days": ",".join(str(d) for d in missing_day_nums),
                "Reason": "One or more expected market-session candles are missing; outcome excluded until repaired",
            })

        if len(expected_dates) >= 20:
            elapsed_20d += 1
            day20 = next((r for r in signal_rows if int(r["Tracking_Day"]) == 20), None)
            if day20 and day20["Data_Quality"] == "OK":
                complete_20d += 1

        for record in signal_rows:
            key = (sid, int(record["Tracking_Day"]))
            old_quality = existing_quality.get(key)
            # Existing good records do not get resent. Missing/incomplete rows
            # are deliberately resent so Apps Script can repair them in place.
            if old_quality and old_quality not in {"MISSING_OHLC_FOR_MARKET_SESSION", "INCOMPLETE_20D_HISTORY"}:
                skipped_existing += 1
                continue
            rows.append(record)

    result = pd.DataFrame(rows, columns=PERFORMANCE_COLUMNS)
    empty_report.update({
        "signals_with_history": len(with_history_ids),
        "signals_without_history": len({r.get("Signal_ID") for r in missing_signals if r.get("Signal_ID") and "No OHLC history" in r.get("Reason", "")}),
        "signals_waiting_for_first_session": len(pending_no_future),
        "signals_complete_20d": complete_20d,
        "signals_window_elapsed_20d": elapsed_20d,
        "rows_generated": int(len(result)),
        "rows_skipped_existing": int(skipped_existing),
        "missing_signals": missing_signals,
        "missing_symbols": sorted({str(r.get("Symbol")) for r in missing_signals if r.get("Symbol") and "No OHLC history" in r.get("Reason", "")}),
        "pending_no_future_sessions": pending_no_future,
        "missing_candles": missing_candles,
        "incomplete_signals": incomplete_signals,
        "expected_keys": [(sid, day) for sid, day in sorted(expected_keys)],
        "calendar_source": calendar_source,
        "latest_market_session": max(sessions).isoformat() if sessions else "",
    })
    return result, empty_report
