"""Matured-signal reconciliation and bounded combination analysis.

The live scanner never imports this module. This is research-only code that
compares saved signal-day features with observed 20-trading-day outcomes.
It deliberately reports when a time-based holdout is not available.
"""
from __future__ import annotations

from itertools import combinations
from datetime import datetime
from zoneinfo import ZoneInfo

import numpy as np
import pandas as pd

IST = ZoneInfo("Asia/Kolkata")
# Simplified, user-friendly columns for the final exported Google Sheet
ANALYSIS_OUTPUT_COLUMNS = [
    "Analysis_Timestamp_IST", 
    "Outcome", 
    "Setup_Rules", 
    "Times_Occurred",
    "Win_Rate_%", 
    "Avg_Profit_%", 
    "Stop_Hit_Rate_%",
    "Overall_Score_(0-100)"
]

# Thresholds are fixed in advance to limit arbitrary curve fitting.
# Expanded to include Delivery_Pct, Resistance_Touches, Risk_Reward, and Relative Strength.
DEFAULT_THRESHOLDS = {
    "Rating": [7, 8, 9, 10],
    "Distance_Pct": [0.5, 1, 2, 3, 5],  # smaller distance is preferable, so <=
    "RVOL": [0.9, 1.15, 1.4, 1.8, 2.5],
    "ADX": [20, 25, 35],
    "RSI": [50, 55, 60, 65, 70],
    "Score": [60, 70, 80, 90],
    "Rank_Score": [40, 50, 60, 70, 80],
    "Delivery_Pct": [35, 50, 65],
    "Resistance_Touches": [3, 4, 6],
    "Risk_Reward": [1.5, 2.0, 2.5],
    "NIFTY_Relative_Strength_Pct": [0.0, 3.0, 5.0],
    "Relative_Strength_60D_Pct": [0.0, 5.0, 10.0],
    "Component_Proximity": [0.5, 0.7, 0.85],
    "Component_Resistance": [0.25, 0.5, 0.75],
    "Component_Volume": [0.5, 0.7, 0.85],
    "Component_Trend": [0.5, 0.7],
    "Component_Momentum": [0.5, 0.7],
    "Component_ADX": [0.5, 0.7],
    "Component_Squeeze": [0.5, 0.7],
    "Component_Relative_Strength": [0.5, 0.7],
    "Component_Candle": [0.5, 0.7],
    "Component_Market_Regime": [0.5, 0.7],
}

# Bounded range conditions capture "sweet spot" momentum without over-extension.
RANGE_CONDITIONS = [
    ("RSI", "RSI_55_68", 55.0, 68.0),
    ("RSI", "RSI_50_65", 50.0, 65.0),
    ("ADX", "ADX_20_40", 20.0, 40.0),
    ("Distance_Pct", "Distance_Pct_0_2", 0.0, 2.0),
]


def _to_binary(series: pd.Series) -> pd.Series:
    if pd.api.types.is_bool_dtype(series):
        return series.astype(float)
    as_text = series.astype(str).str.strip().str.upper()
    mapped = as_text.map({"YES": 1.0, "TRUE": 1.0, "1": 1.0, "NO": 0.0, "FALSE": 0.0, "0": 0.0})
    numeric = pd.to_numeric(series, errors="coerce")
    return mapped.where(mapped.notna(), numeric)


def _derive_trade_setup(df: pd.DataFrame) -> pd.Series:
    """Reconstructs the exact 3 trade setup categories used on the dashboard."""
    adx = pd.to_numeric(df.get("ADX", pd.Series(0.0, index=df.index)), errors="coerce").fillna(0.0)
    rsi = pd.to_numeric(df.get("RSI", pd.Series(0.0, index=df.index)), errors="coerce").fillna(0.0)
    dist = pd.to_numeric(df.get("Distance_Pct", pd.Series(99.0, index=df.index)), errors="coerce").fillna(99.0)

    setup = pd.Series("Positional (2-6w)", index=df.index, dtype=object)
    short_mask = rsi >= 55.0
    swing_mask = (dist <= 2.0) & (rsi >= 60.0) & (adx >= 20.0)
    setup.loc[short_mask] = "Short Term (1-3w)"
    setup.loc[swing_mask] = "Breakout Swing (3-10d)"
    return setup


def build_completed_outcomes(
    signals: pd.DataFrame,
    performance: pd.DataFrame,
    target_day: int = 20,
) -> tuple[pd.DataFrame, dict]:
    """Join immutable signal snapshots to fully valid Day-N results (default Day 20).

    In addition to "ever touched" flags, derive target-before-stop outcomes.
    If the daily high and low touch a target and stop on the same day, order is
    unknowable from OHLC so the corresponding before-stop outcome is NaN and is
    excluded from that outcome's denominator.
    """
    if signals is None or signals.empty:
        return pd.DataFrame(), {"signals_total": 0, "signals_matured_20d": 0, "signals_pending": 0}
    if performance is None or performance.empty:
        return pd.DataFrame(), {"signals_total": int(len(signals)), "signals_matured_20d": 0, "signals_pending": int(len(signals))}

    perf = performance.copy()
    perf["Tracking_Day"] = pd.to_numeric(perf.get("Tracking_Day"), errors="coerce")
    day_n = perf[perf["Tracking_Day"] == int(target_day)].copy()
    # Fail closed: only a row explicitly marked OK can be a final outcome.
    if "Data_Quality" in day_n:
        day_n = day_n[day_n["Data_Quality"].astype(str).str.strip().str.upper().eq("OK")]
    else:
        day_n = day_n.iloc[0:0]
    if day_n.empty or "Signal_ID" not in signals.columns:
        return pd.DataFrame(), {
            "signals_total": int(len(signals)), "signals_matured_20d": 0,
            "signals_pending": int(len(signals)),
        }
    if "Tracking_Date" in day_n.columns:
        day_n = day_n.sort_values("Tracking_Date")
    day_n = day_n.drop_duplicates("Signal_ID", keep="last")
    joined = signals.merge(day_n, on="Signal_ID", how="inner", suffixes=("_Signal", "_Performance"))
    if joined.empty:
        return joined, {"signals_total": int(len(signals)), "signals_matured_20d": 0, "signals_pending": int(len(signals))}

    signal_cols = [
        "Scan_Date", "Rating", "Distance_Pct", "RVOL", "ADX", "RSI", "Score", "Rank_Score",
        "EMA_Structure", "Market_Regime", "Candlestick", "False_Breakout", "Cap_Category",
        "Scanner_Status", "Delivery_Pct", "Deliverable_Qty", "Resistance_Touches",
        "Resistance_Recency", "Risk_Reward", "NIFTY_Relative_Strength_Pct",
        "Relative_Strength_60D_Pct", "ATR_Pct", "ATR_Ratio",
    ]
    for col in signal_cols:
        if col not in joined and f"{col}_Signal" in joined:
            joined[col] = joined[f"{col}_Signal"]

    joined["Trade_Setup"] = _derive_trade_setup(joined)
    joined["Return_20D_Pct"] = pd.to_numeric(joined.get("Close_Return_Pct"), errors="coerce")
    for outcome in ["Breakout_Hit", "T1_Hit", "T2_Hit", "T3_Hit", "Stop_Hit"]:
        if outcome in joined:
            joined[outcome] = _to_binary(joined[outcome])
    for col in ["Best_Gain_Pct", "Max_Drawdown_Pct", "Return_20D_Pct"]:
        if col in joined:
            joined[col] = pd.to_numeric(joined[col], errors="coerce")

    stop_day = pd.to_numeric(joined.get("Stop_First_Day", pd.Series(np.nan, index=joined.index)), errors="coerce")
    for label, day_col in [("T1_Before_Stop", "T1_First_Day"),
                           ("T2_Before_Stop", "T2_First_Day"),
                           ("T3_Before_Stop", "T3_First_Day")]:
        t_day = pd.to_numeric(joined.get(day_col, pd.Series(np.nan, index=joined.index)), errors="coerce")
        outcome = pd.Series(0.0, index=joined.index)
        outcome.loc[t_day.notna() & (stop_day.isna() | (t_day < stop_day))] = 1.0
        outcome.loc[t_day.notna() & stop_day.notna() & (t_day == stop_day)] = np.nan
        joined[label] = outcome

    first_event = joined.get("First_Event", pd.Series("NONE", index=joined.index)).astype(str).str.upper()
    stop_first = pd.Series(0.0, index=joined.index)
    stop_first.loc[first_event.eq("STOP_FIRST")] = 1.0
    stop_first.loc[first_event.eq("AMBIGUOUS_SAME_DAY")] = np.nan
    joined["Stop_Before_Target"] = stop_first

    return joined, {
        "signals_total": int(len(signals)),
        "signals_matured_20d": int(joined["Signal_ID"].nunique()),
        "signals_pending": max(0, int(len(signals)) - int(joined["Signal_ID"].nunique())),
    }


def _compute_Consistency_Score(
    win_rate: float,
    avg_ret: float,
    stop_rate: float,
    train_wr: float,
    holdout_wr: float,
    unique_dates_count: int,
    total_unique_dates: int,
    has_holdout: bool,
) -> float:
    """Computes a 0-100 composite edge & consistency score to rank combinations."""
    wr = float(win_rate) if np.isfinite(win_rate) else 0.0
    sr = float(stop_rate) if np.isfinite(stop_rate) else 50.0
    ret = float(avg_ret) if np.isfinite(avg_ret) else 0.0

    # Base score from win rate (50% weight) + low stop rate bonus (20% weight) + return bonus (15% weight)
    base = (wr * 0.50) + (max(0.0, 100.0 - sr) * 0.20) + (np.clip(ret * 2.5, -15.0, 20.0))

    # Date dispersion bonus (up to 15 points): rewards setups that appear across multiple scan dates
    if total_unique_dates > 1:
        dispersion_ratio = min(1.0, unique_dates_count / max(2.0, total_unique_dates * 0.5))
        base += dispersion_ratio * 15.0

    # Out-of-sample stability adjustment when time holdout exists
    if has_holdout and np.isfinite(train_wr) and np.isfinite(holdout_wr):
        drift = abs(holdout_wr - train_wr)
        # Penalize severe overfitting where holdout collapses vs train
        if holdout_wr < train_wr - 15.0:
            base -= min(20.0, (train_wr - holdout_wr) * 0.6)
        elif drift <= 10.0 and holdout_wr >= 55.0:
            base += 8.0  # Stability bonus

    return round(float(np.clip(base, 0.0, 100.0)), 1)


def analyze_outcome_combinations(
    outcomes: pd.DataFrame,
    outcome_col: str = "T1_Hit",
    thresholds: dict | None = None,
    min_signals: int = 25,
    max_order: int = 3,
) -> pd.DataFrame:
    """Vectorized evaluation of 1-to-N factor combinations on matured outcome data.

    Uses fast NumPy bitmasks and pre-filtered single conditions to evaluate
    expanded technical, delivery, cap, and setup combinations while ranking by
    both out-of-sample consistency and risk-adjusted expectancy.
    """
    if outcomes is None or outcomes.empty or outcome_col not in outcomes.columns:
        return pd.DataFrame(columns=ANALYSIS_OUTPUT_COLUMNS)

    thresholds = thresholds or DEFAULT_THRESHOLDS
    work = outcomes.copy()
    work[outcome_col] = _to_binary(work[outcome_col])
    work = work.loc[work[outcome_col].notna()].copy()
    if work.empty or len(work) < max(1, int(min_signals)):
        return pd.DataFrame(columns=ANALYSIS_OUTPUT_COLUMNS)

    if "Trade_Setup" not in work.columns:
        work["Trade_Setup"] = _derive_trade_setup(work)

    n_rows = len(work)
    min_sig = max(1, int(min_signals))

    # Build candidate condition bitmasks (only keep conditions that have >= min_signals on their own)
    condition_list: list[tuple[str, str, np.ndarray]] = []

    for col, values in thresholds.items():
        if col not in work.columns:
            continue
        numeric = pd.to_numeric(work[col], errors="coerce").to_numpy(dtype=float)
        for value in values:
            if col == "Distance_Pct":
                mask = np.isfinite(numeric) & (numeric <= float(value))
                label = f"{col}<={value}"
            else:
                mask = np.isfinite(numeric) & (numeric >= float(value))
                label = f"{col}>={value}"
            if int(mask.sum()) >= min_sig:
                condition_list.append((col, label, mask))

    # Add bounded sweet-spot range conditions
    for col, label, low_val, high_val in RANGE_CONDITIONS:
        if col not in work.columns:
            continue
        numeric = pd.to_numeric(work[col], errors="coerce").to_numpy(dtype=float)
        mask = np.isfinite(numeric) & (numeric >= low_val) & (numeric <= high_val)
        if int(mask.sum()) >= min_sig:
            condition_list.append((col, label, mask))

    # Add categorical scanner features including Trade_Setup, Cap_Category, Scanner_Status
    cat_cols = [
        "Trade_Setup", "Cap_Category", "Scanner_Status",
        "EMA_Structure", "Market_Regime", "Candlestick", "False_Breakout",
    ]
    for col in cat_cols:
        if col not in work.columns:
            continue
        series_str = work[col].astype(str).str.strip()
        valid_mask = ~series_str.str.lower().isin(["", "nan", "none", "<na>"])
        counts = series_str[valid_mask].value_counts()
        for value, count in counts.items():
            if int(count) < min_sig:
                continue
            label_value = str(value).upper() if col == "False_Breakout" else str(value)
            mask = series_str.eq(str(value)).to_numpy(dtype=bool)
            condition_list.append((col, f"{col}={label_value}", mask))

    if not condition_list:
        return pd.DataFrame(columns=ANALYSIS_OUTPUT_COLUMNS)

    # Pre-extract metric arrays for fast vectorized slicing
    outcome_arr = work[outcome_col].to_numpy(dtype=float)
    ret_arr = pd.to_numeric(work.get("Return_20D_Pct", pd.Series(np.nan, index=work.index)), errors="coerce").to_numpy(dtype=float)
    stop_arr = _to_binary(work["Stop_Hit"]).to_numpy(dtype=float) if "Stop_Hit" in work.columns else np.full(n_rows, np.nan)

    # Date dispersion & chronological Train/Holdout split
    scan_dates_series = pd.to_datetime(work.get("Scan_Date", pd.Series(dtype=str)), errors="coerce").dt.date
    unique_dates = sorted(set(scan_dates_series.dropna()))
    total_unique_dates = max(1, len(unique_dates))
    date_codes = pd.Categorical(scan_dates_series).codes

    has_holdout = len(unique_dates) >= 5
    if has_holdout:
        cut_idx = max(1, int(len(unique_dates) * 0.75))
        train_dates = set(unique_dates[:cut_idx])
        test_dates = set(unique_dates[cut_idx:])
        train_mask = scan_dates_series.isin(train_dates).to_numpy(dtype=bool)
        test_mask = scan_dates_series.isin(test_dates).to_numpy(dtype=bool)
    else:
        train_mask = np.ones(n_rows, dtype=bool)
        test_mask = np.zeros(n_rows, dtype=bool)

    # If user requests 3-way or 4-way combinations and condition_list is large,
    # bound the higher-order search to the top 32 most informative single conditions
    # so execution always finishes in < 1 second without freezing Streamlit.
    single_ranked = sorted(
        condition_list,
        key=lambda item: (
            float(np.nanmean(outcome_arr[item[2]]) * 100.0) if item[2].any() else 0.0,
            int(item[2].sum()),
        ),
        reverse=True,
    )
    higher_order_pool = single_ranked[:32] if len(single_ranked) > 32 else single_ranked

    output = []
    now_string = datetime.now(IST).strftime("%Y-%m-%d %H:%M:%S IST")

    def evaluate_mask(mask: np.ndarray, condition_names: list[str]):
        n_sel = int(mask.sum())
        if n_sel < min_sig:
            return

        sel_out = outcome_arr[mask]
        win_rate = float(np.nanmean(sel_out) * 100.0) if len(sel_out) else np.nan

        sel_ret = ret_arr[mask]
        valid_ret = sel_ret[np.isfinite(sel_ret)]
        avg_ret = float(valid_ret.mean()) if len(valid_ret) else np.nan

        sel_stop = stop_arr[mask]
        valid_stop = sel_stop[np.isfinite(sel_stop)]
        stop_rate = float(valid_stop.mean() * 100.0) if len(valid_stop) else np.nan

        # Train & Holdout stats just for consistency score calculation (not exported)
        tr_mask = mask & train_mask
        te_mask = mask & test_mask
        tr_n = int(tr_mask.sum())
        te_n = int(te_mask.sum())
        tr_wr = float(np.nanmean(outcome_arr[tr_mask]) * 100.0) if tr_n > 0 else np.nan
        te_wr = float(np.nanmean(outcome_arr[te_mask]) * 100.0) if te_n > 0 else np.nan

        # Distinct scan dates covered by this combination
        sel_dates = date_codes[mask]
        unique_dt_cnt = len(np.unique(sel_dates[sel_dates >= 0]))

        consistency = _compute_Consistency_Score(
            win_rate, avg_ret, stop_rate, tr_wr, te_wr,
            unique_dt_cnt, total_unique_dates, has_holdout,
        )

        output.append({
            "Analysis_Timestamp_IST": now_string,
            "Outcome": outcome_col,
            "Setup_Rules": " + ".join(condition_names),
            "Times_Occurred": n_sel,
            "Win_Rate_%": round(win_rate, 2) if np.isfinite(win_rate) else np.nan,
            "Avg_Profit_%": round(avg_ret, 2) if np.isfinite(avg_ret) else np.nan,
            "Stop_Hit_Rate_%": round(stop_rate, 2) if np.isfinite(stop_rate) else np.nan,
            "Overall_Score_(0-100)": consistency,
        })

    # Order 1 & 2 evaluate all valid conditions; Order 3+ uses the top pool
    max_ord = max(1, min(int(max_order), 4))
    for order in range(1, max_ord + 1):
        pool = condition_list if order <= 2 else higher_order_pool
        for items in combinations(pool, order):
            families = [x[0] for x in items]
            if len(set(families)) != len(families):
                continue
            combined_mask = items[0][2].copy()
            for _, _, m in items[1:]:
                combined_mask &= m
                if int(combined_mask.sum()) < min_sig:
                    break
            else:
                evaluate_mask(combined_mask, [x[1] for x in items])

    if not output:
        return pd.DataFrame(columns=ANALYSIS_OUTPUT_COLUMNS)

    out = pd.DataFrame(output)
    
    # Sort strictly by our primary, easy-to-understand metrics
    out = out.sort_values(
        ["Overall_Score_(0-100)", "Win_Rate_%", "Avg_Profit_%", "Times_Occurred"],
        ascending=[False, False, False, False], na_position="last"
    )

    out = out[ANALYSIS_OUTPUT_COLUMNS].reset_index(drop=True)
    return out
