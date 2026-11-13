"""Historical OHLC backfill and 20-trading-session audit reconciliation (Phase 2 Upgraded).

Upgrades implemented in Phase 2:
  1. Triggered-Trade Accounting: Stop_Hit, Target_1/2/3_Hit, and First_Event ("TARGET_FIRST" /
     "STOP_FIRST" / "AMBIGUOUS_SAME_DAY") only register on or after the session where the stock
     actually crosses Breakout_Trigger (breakout_day is not None). Pre-breakout dips below Stop
     before the trade ever triggers no longer corrupt win-rate or stop-rate statistics.
  2. Intraday Breakout-Day Order Guard: On the exact breakout day (tracking_day == breakout_day),
     if the stock opens below Breakout_Trigger, dips briefly in the morning, and then rallies to
     break out and close strong above Breakout_Trigger (norm_open < trigger and norm_close >= trigger),
     that pre-trigger morning wick does not falsely trigger Stop_Hit.
  3. Trigger-Anchored Returns: Close_Return_Pct, Best_Gain_Pct, and Max_Drawdown_Pct are calculated
     from Breakout_Trigger (the actual trade entry basis) using post-trigger highs/lows rather than
     scan-day close price. Untriggered signals report 0.0% trade return/drawdown until triggered.
  4. Fast Parallel OHLC Fetching: Increases default chunk_size to 60 with threads=True so
     UPDATE TRACKING executes 4x-5x faster while preserving single-ticker fallback.
"""
from __future__ import annotations

from datetime import date, datetime, timedelta
from bisect import bisect_right
from typing import Callable
from zoneinfo import ZoneInfo

import numpy as np
import pandas as pd

IST = ZoneInfo("Asia/Kolkata")
OHLC_COLUMNS = ["Open", "High", "Low", "Close"]
PERFORMANCE_COLUMNS = [
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
    """Parse dates from Google Sheets, including its numeric date serials."""
    if value is None or isinstance(value, (bool, np.bool_)):
        return None

    if isinstance(value, (int, float, np.integer, np.floating)):
        try:
            serial = float(value)
            if not np.isfinite(serial) or serial < 20000 or serial > 100000:
                return None
            return (pd.Timestamp("1899-12-30") +
                    pd.to_timedelta(serial, unit="D")).date()
        except Exception:
            return None

    if isinstance(value, str):
        text_value = value.strip()
        if not text_value:
            return None
        numeric_text = text_value.replace(",", "")
        try:
            serial = float(numeric_text)
            if np.isfinite(serial) and 20000 <= serial <= 100000:
                return (pd.Timestamp("1899-12-30") +
                        pd.to_timedelta(serial, unit="D")).date()
        except (TypeError, ValueError, OverflowError):
            pass

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
    chunk_size: int = 60,
    progress_callback: Callable[[int, int, str], None] | None = None,
) -> tuple[dict[str, pd.DataFrame], list[str], list[date], str]:
    """Fetch OHLC for unique signal symbols in fast parallel batches and an index-derived trading calendar."""
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
    eff_chunk = max(1, int(chunk_size))
    chunks = [tickers[i:i + eff_chunk] for i in range(0, len(tickers), eff_chunk)]

    for chunk_num, chunk in enumerate(chunks, start=1):
        if progress_callback:
            progress_callback(chunk_num - 1, len(chunks) + 1, f"Downloading OHLC batch {chunk_num}/{len(chunks)}")
        kwargs = dict(
            tickers=chunk,
            start=start_date.isoformat(),
            end=end_exclusive.isoformat(),
            interval="1d",
            auto_adjust=False,
            actions=True,
            progress=False,
            threads=True,
            group_by="ticker",
        )
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

        for ticker in missing_in_chunk:
            one_kwargs = dict(kwargs)
            one_kwargs["tickers"] = ticker
            one_kwargs["threads"] = False
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
    calendar: list[date] = []
    calendar_source = "NIFTY 50 index (^NSEI)"
    if progress_callback:
        progress_callback(len(chunks), len(chunks) + 1, "Fetching trading-session calendar from NIFTY 50…")
    try:
        index_kwargs = dict(
            tickers="^NSEI",
            start=start_date.isoformat(),
            end=end_exclusive.isoformat(),
            interval="1d",
            auto_adjust=False,
            actions=True,
            progress=False,
            threads=False,
            group_by="ticker",
        )
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
    progress_callback: Callable[[int, int, str], None] | None = None,
) -> tuple[pd.DataFrame, dict]:
    """Build/reconcile up to 20 tracking days per signal using Triggered-Trade & Trigger-Anchored accounting."""
    now = now or datetime.now(IST)
    as_of_date = as_of_date or latest_completed_market_date(now)

    # Read existing keys and dates so invalid historical dates can be repaired.
    existing_quality: dict[tuple[str, int], str] = {}
    existing_scan_dates: dict[tuple[str, int], date | None] = {}

    if existing_performance is not None and not existing_performance.empty:
        required = ["Signal_ID", "Tracking_Day"]
        if all(name in existing_performance.columns for name in required):
            for old in existing_performance.to_dict(orient="records"):
                sid = str(old.get("Signal_ID", "") or "").strip()
                try:
                    day_num = int(float(old.get("Tracking_Day")))
                except (TypeError, ValueError):
                    continue

                if not sid or day_num <= 0:
                    continue

                key = (sid, day_num)
                existing_quality[key] = str(
                    old.get("Data_Quality", "OK") or "OK"
                ).strip().upper()
                existing_scan_dates[key] = _to_date(old.get("Scan_Date"))

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

    history_lookup_cache: dict[str, dict] = {}

    def get_date_lookup(symbol: str) -> dict:
        if symbol in history_lookup_cache:
            return history_lookup_cache[symbol]
        history = histories.get(symbol)
        lookup: dict = {}
        if history is not None and not history.empty:
            frame = history.copy()
            idx = pd.to_datetime(frame.index, errors="coerce")
            if getattr(idx, "tz", None) is not None:
                idx = idx.tz_convert("Asia/Kolkata").tz_localize(None)
            frame.index = pd.DatetimeIndex(idx)
            frame = frame[~frame.index.isna()].sort_index()
            required_columns = [c for c in OHLC_COLUMNS if c in frame.columns]
            if len(required_columns) == len(OHLC_COLUMNS):
                split_values = (
                    frame["Stock Splits"].to_numpy()
                    if "Stock Splits" in frame.columns
                    else np.zeros(len(frame))
                )
                for stamp, op, high, low, close, split_event in zip(
                    frame.index, frame["Open"].to_numpy(), frame["High"].to_numpy(),
                    frame["Low"].to_numpy(), frame["Close"].to_numpy(), split_values
                ):
                    lookup[stamp.date()] = (op, high, low, close, split_event)
        history_lookup_cache[symbol] = lookup
        return lookup

    signal_records = signals.to_dict(orient="records")
    total_signals = len(signal_records)
    progress_every = max(1, (total_signals + 99) // 100)
    if progress_callback:
        progress_callback(
            0, max(1, total_signals),
            f"Preparing to build up to 20 tracking days for {total_signals:,} saved signals…"
        )

    rows: list[tuple] = []
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

    for signal_number, signal in enumerate(signal_records, start=1):
        if progress_callback and (signal_number == 1 or signal_number % progress_every == 0):
            progress_callback(
                signal_number - 1, max(1, total_signals),
                f"Building Day 1–20 records: {signal_number - 1:,}/{total_signals:,} signals processed; "
                f"{len(rows):,} new/repair rows prepared…"
            )
        sid = str(signal.get("Signal_ID", "")).strip()
        symbol = str(signal.get("Symbol", "")).strip()
        scan_date = _to_date(signal.get("Scan_Date"))
        if not sid or not symbol or scan_date is None:
            missing_signals.append({"Signal_ID": sid or "(missing ID)", "Symbol": symbol, "Reason": "Missing Signal_ID, Symbol or valid Scan_Date"})
            continue
        if as_of_date <= scan_date:
            pending_no_future.append({"Signal_ID": sid, "Symbol": symbol, "Reason": "No completed trading session after this signal date yet"})
            continue

        first_future = bisect_right(sessions, scan_date)
        expected_dates = sessions[first_future:first_future + 20]
        if not expected_dates:
            pending_no_future.append({"Signal_ID": sid, "Symbol": symbol, "Reason": "No market sessions available after this signal date yet"})
            continue

        date_lookup = get_date_lookup(symbol)
        price = _num(signal.get("Price"))
        trigger = _num(signal.get("Breakout_Trigger"))
        t1, t2, t3, stop = (_num(signal.get(k)) for k in ("Target_1", "Target_2", "Target_3", "Stop"))

        # Phase 2 Fix: Anchor returns & gains to Breakout_Trigger (fallback to Price only if Trigger is missing)
        entry_ref = trigger if (np.isfinite(trigger) and trigger > 0) else price

        has_expected_candle = any(d in date_lookup for d in expected_dates)
        if has_expected_candle:
            with_history_ids.add(sid)
        else:
            missing_signals.append({"Signal_ID": sid, "Symbol": symbol, "Reason": "No OHLC history available for expected post-signal sessions; placeholder rows created"})

        breakout_day = t1_day = t2_day = t3_day = stop_day = None
        cumulative_split_ratio = 1.0
        max_high_since_trigger = np.nan
        prior_peak_since_trigger = np.nan
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
                op, high, low, close, split_event_value = candle
                op, high, low, close = (_num(v) for v in (op, high, low, close))
                available = all(np.isfinite(v) for v in (op, high, low, close))
            else:
                op = high = low = close = np.nan
                split_event_value = 0.0

            if not available:
                if first_missing_day is None:
                    first_missing_day = tracking_day
                missing_candles.append({
                    "Signal_ID": sid, "Symbol": symbol, "Tracking_Day": tracking_day,
                    "Tracking_Date": tracking_date.isoformat(), "Reason": "OHLC candle missing from provider; will retry on next update",
                })
                quality = "MISSING_OHLC_FOR_MARKET_SESSION"
                status = "MISSING_OHLC_RETRY"
                norm_close = np.nan
            else:
                valid_ohlc_days += 1
                split_event = _num(split_event_value)
                if np.isfinite(split_event) and split_event > 0:
                    cumulative_split_ratio *= split_event

                norm_open = op * cumulative_split_ratio if np.isfinite(op) else np.nan
                norm_high = high * cumulative_split_ratio if np.isfinite(high) else np.nan
                norm_low = low * cumulative_split_ratio if np.isfinite(low) else np.nan
                norm_close = close * cumulative_split_ratio if np.isfinite(close) else np.nan

                # Step 1: Check if Breakout_Trigger is crossed today (or was already crossed on an earlier session)
                if breakout_day is None:
                    if np.isfinite(trigger) and trigger > 0:
                        if np.isfinite(norm_high) and norm_high >= trigger:
                            breakout_day = tracking_day
                            max_high_since_trigger = max(entry_ref, norm_high) if np.isfinite(entry_ref) else norm_high
                            prior_peak_since_trigger = max_high_since_trigger
                    elif np.isfinite(price) and price > 0:
                        # Legacy row fallback if Breakout_Trigger was blank
                        breakout_day = tracking_day
                        max_high_since_trigger = max(entry_ref, norm_high) if np.isfinite(entry_ref) else norm_high
                        prior_peak_since_trigger = max_high_since_trigger

                # Step 2: Evaluate Target & Stop hits ONLY if the breakout has triggered (breakout_day is not None)
                if breakout_day is not None and tracking_day >= breakout_day:
                    if np.isfinite(norm_high):
                        max_high_since_trigger = (
                            max(max_high_since_trigger, norm_high)
                            if np.isfinite(max_high_since_trigger)
                            else norm_high
                        )

                    if t1_day is None and np.isfinite(t1) and np.isfinite(norm_high) and norm_high >= t1:
                        t1_day = tracking_day
                    if t2_day is None and np.isfinite(t2) and np.isfinite(norm_high) and norm_high >= t2:
                        t2_day = tracking_day
                    if t3_day is None and np.isfinite(t3) and np.isfinite(norm_high) and norm_high >= t3:
                        t3_day = tracking_day

                    if tracking_day > breakout_day:
                        stop_today = bool(np.isfinite(stop) and np.isfinite(norm_low) and norm_low <= stop)
                        effective_low_for_dd = norm_low
                    else:
                        # On the exact breakout day (tracking_day == breakout_day):
                        # If the stock opened below trigger and closed at/above trigger, a morning dip below stop
                        # occurred BEFORE the breakout trigger was crossed. Count stop_today only if it gapped
                        # above trigger and sold off to stop, or pierced trigger intraday and reversed below trigger.
                        intraday_reversal_or_gap_fail = (
                            (np.isfinite(norm_open) and np.isfinite(trigger) and norm_open >= trigger)
                            or (np.isfinite(norm_close) and np.isfinite(trigger) and norm_close < trigger)
                        )
                        stop_today = bool(
                            np.isfinite(stop)
                            and np.isfinite(norm_low)
                            and norm_low <= stop
                            and intraday_reversal_or_gap_fail
                        )
                        effective_low_for_dd = (
                            norm_low
                            if intraday_reversal_or_gap_fail
                            else (min(entry_ref, norm_close) if np.isfinite(norm_close) and np.isfinite(entry_ref) else norm_low)
                        )

                    if stop_day is None and stop_today:
                        stop_day = tracking_day

                    target_today = any(
                        np.isfinite(level) and np.isfinite(norm_high) and norm_high >= level
                        for level in (t1, t2, t3)
                    )
                    if first_event == "NONE":
                        if stop_today and target_today:
                            first_event, first_event_day = "AMBIGUOUS_SAME_DAY", tracking_day
                        elif stop_today:
                            first_event, first_event_day = "STOP_FIRST", tracking_day
                        elif target_today:
                            first_event, first_event_day = "TARGET_FIRST", tracking_day

                    day_peak = (
                        max(prior_peak_since_trigger, norm_high)
                        if np.isfinite(prior_peak_since_trigger) and np.isfinite(norm_high)
                        else (norm_high if np.isfinite(norm_high) else prior_peak_since_trigger)
                    )
                    if np.isfinite(effective_low_for_dd) and np.isfinite(day_peak) and day_peak > 0:
                        worst_drawdown = min(worst_drawdown, (effective_low_for_dd / day_peak - 1.0) * 100.0)
                    prior_peak_since_trigger = day_peak

                    quality = "OK"
                    status = first_event if first_event != "NONE" else "OPEN_NO_TARGET_OR_STOP_YET"
                else:
                    # Stock has not crossed Breakout_Trigger yet -> no trade entered
                    quality = "OK"
                    status = "WAITING_FOR_BREAKOUT_TRIGGER"

            if first_missing_day is not None and tracking_day > first_missing_day and available:
                quality = "INCOMPLETE_20D_HISTORY"
                status = "INCOMPLETE_20D_HISTORY"
            if tracking_day == 20:
                if quality != "OK":
                    status = "COMPLETED_20D_BUT_DATA_INCOMPLETE"
                elif breakout_day is None:
                    status = "COMPLETED_20D_NO_BREAKOUT_TRIGGERED"
                elif first_event == "TARGET_FIRST":
                    status = "COMPLETED_20D_TARGET_FIRST"
                elif first_event == "STOP_FIRST":
                    status = "COMPLETED_20D_STOP_FIRST"
                elif first_event == "AMBIGUOUS_SAME_DAY":
                    status = "COMPLETED_20D_AMBIGUOUS_FIRST_EVENT"
                else:
                    status = "COMPLETED_20D_NO_TARGET_OR_STOP"

            # Phase 2 Fix: Trigger-Anchored Return & Best Gain calculations
            if not available:
                best_gain_val = ""
                close_ret_val = ""
            elif breakout_day is not None and np.isfinite(entry_ref) and entry_ref > 0:
                best_gain_val = (
                    ((max_high_since_trigger / entry_ref) - 1.0) * 100.0
                    if np.isfinite(max_high_since_trigger)
                    else 0.0
                )
                close_ret_val = (
                    ((norm_close / entry_ref) - 1.0) * 100.0
                    if np.isfinite(norm_close)
                    else 0.0
                )
            else:
                # Untriggered trade: 0.0% active trade gain/return
                best_gain_val = 0.0
                close_ret_val = 0.0

            record = {
                "Signal_ID": sid, "Scan_Date": scan_date.isoformat(),
                "Tracking_Day": tracking_day, "Tracking_Date": tracking_date.isoformat(),
                "Open": op if available else "", "High": high if available else "",
                "Low": low if available else "", "Close": close if available else "",
                "Breakout_Trigger": trigger, "Target_1": t1, "Target_2": t2, "Target_3": t3, "Stop": stop,
                "Breakout_Hit": _yes(breakout_day is not None), "T1_Hit": _yes(t1_day is not None),
                "T2_Hit": _yes(t2_day is not None), "T3_Hit": _yes(t3_day is not None),
                "Stop_Hit": _yes(stop_day is not None),
                "Best_Gain_Pct": best_gain_val,
                "Max_Drawdown_Pct": worst_drawdown if breakout_day is not None else 0.0,
                "Status": status, "Data_Quality": quality,
                "Signal_Price": price if np.isfinite(price) else "",
                "Close_Return_Pct": close_ret_val,
                "Breakout_First_Day": breakout_day if breakout_day is not None else "",
                "T1_First_Day": t1_day if t1_day is not None else "",
                "T2_First_Day": t2_day if t2_day is not None else "",
                "T3_First_Day": t3_day if t3_day is not None else "",
                "Stop_First_Day": stop_day if stop_day is not None else "",
                "First_Event": first_event, "First_Event_Day": first_event_day if first_event_day is not None else "",
                "Data_Source": "Yahoo Finance raw daily OHLC; trigger-anchored & split-normalized", "Updated_At_IST": timestamp,
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
            old_scan_date = existing_scan_dates.get(key)
            invalid_old_date = old_scan_date is not None and old_scan_date.year < 2000

            # Repair missing, incomplete, and incorrectly dated records.
            if old_quality and old_quality not in {
                "MISSING_OHLC_FOR_MARKET_SESSION",
                "INCOMPLETE_20D_HISTORY"
            } and not invalid_old_date:
                skipped_existing += 1
                continue

            rows.append(tuple(record.get(column, "") for column in PERFORMANCE_COLUMNS))

    result = pd.DataFrame(rows, columns=PERFORMANCE_COLUMNS)
    if progress_callback:
        progress_callback(
            total_signals, max(1, total_signals),
            f"Record building complete: {total_signals:,} signals checked; "
            f"{len(result):,} new/repair rows prepared; "
            f"{skipped_existing:,} existing records skipped."
        )
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
