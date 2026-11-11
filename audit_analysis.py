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
# These exactly match what the dashboard UI looks for to draw the Top 3 Cards.
ANALYSIS_OUTPUT_COLUMNS = [
    "Analysis_Timestamp_IST", 
    "Outcome_Goal", 
    "Setup_Rules", 
    "Times_Occurred",
    "Win_Rate_%", 
    "Avg_Profit_%", 
    "Stop_Hit_Rate_%",
    "Overall_Score_(0-100)"
]

# Thresholds synchronized with Scanner v2 institutional anti-trap and scoring tiers.
DEFAULT_THRESHOLDS = {
    "Rating": [7, 8, 9, 10],
    "Distance_Pct": [0.5, 1.0, 1.5, 2.0, 3.0, 5.0], 
    "RVOL": [1.0, 1.3, 1.5, 1.8, 2.2],
    "ADX": [20, 25, 35],
    "RSI": [54, 58, 60, 65, 70],
    "Score": [65, 75, 80, 85, 90],
    "Rank_Score": [55, 65, 70, 75, 80, 85],
    "Delivery_Pct": [40, 50, 55, 65],
    "Resistance_Touches": [3, 4, 5],
    "Risk_Reward": [1.5, 2.0, 2.5],
    "NIFTY_Relative_Strength_Pct": [0.0, 2.0, 5.0, 10.0],
    "Relative_Strength_60D_Pct": [0.0, 5.0, 10.0],
    "Component_Proximity": [0.7, 0.82, 0.92],
    "Component_Resistance": [0.5, 0.75, 0.9],
    "Component_Volume": [0.55, 0.70, 0.85],
    "Component_Trend": [0.65, 0.75, 0.9],
    "Component_Momentum": [0.6, 0.8, 0.9],
    "Component_ADX": [0.6, 0.75, 0.9],
    "Component_Squeeze": [0.65, 0.85, 1.0],
    "Component_Relative_Strength": [0.6, 0.78, 0.95],
    "Component_Candle": [0.8, 1.0],
    "Component_Market_Regime": [0.55, 1.0],
}

# Bounded range conditions capture Scanner v2 "sweet spot" momentum & VCP contraction without over-extension.
RANGE_CONDITIONS = [
    ("RSI", "RSI_54_70_SweetSpot", 54.0, 70.0),
    ("RSI", "RSI_58_68_Prime", 58.0, 68.0),
    ("ADX", "ADX_20_40_Trend", 20.0, 40.0),
    ("Distance_Pct", "Distance_Pct_-0.5_2.0_EntryZone", -0.5, 2.0),
    ("ATR_Ratio", "ATR_Ratio_0.4_0.85_VCP_Squeeze", 0.40, 0.85),
    ("ATR_Ratio", "ATR_Ratio_0.4_0.95_TightBase", 0.40, 0.95),
]


def _to_binary(series: pd.Series) -> pd.Series:
    if pd.api.types.is_bool_dtype(series):
        return series.astype(float)
    as_text = series.astype(str).str.strip().str.upper()
    mapped = as_text.map({"YES": 1.0, "TRUE": 1.0, "1": 1.0, "NO": 0.0, "FALSE": 0.0, "0": 0.0})
    numeric = pd.to_numeric(series, errors="coerce")
    return mapped.where(mapped.notna(), numeric)


def _derive_trade_setup(df: pd.DataFrame) -> pd.Series:
    """Reconstructs the exact 4 trade setup categories used on the app.py dashboard."""
    adx = pd.to_numeric(df.get("ADX", pd.Series(0.0, index=df.index)), errors="coerce").fillna(0.0)
    rsi = pd.to_numeric(df.get("RSI", pd.Series(0.0, index=df.index)), errors="coerce").fillna(0.0)
    dist = pd.to_numeric(df.get("Distance_Pct", pd.Series(99.0, index=df.index)), errors="coerce").fillna(99.0)

    setup = pd.Series("Long Term (3-8m)", index=df.index, dtype=object)
    pos_mask = (dist <= 7.0) & (rsi >= 50.0)
    short_mask = (dist <= 4.0) & (rsi >= 55.0)
    swing_mask = (dist <= 2.0) & (rsi >= 60.0) & (adx >= 20.0)

    setup.loc[pos_mask] = "Positional (2-6w)"
    setup.loc[short_mask] = "Short Term (1-3w)"
    setup.loc[swing_mask] = "Breakout Swing (3-10d)"
    return setup


def build_completed_outcomes(
    signals: pd.DataFrame,
    performance: pd.DataFrame,
    target_day: int = 20,
) -> tuple[pd.DataFrame, dict]:
    """Join immutable signal snapshots to fully valid Day-N results (default Day 20)."""
    if signals is None or signals.empty:
        return pd.DataFrame(), {"signals_total": 0, "signals_matured_20d": 0, "signals_pending": 0}
    if performance is None or performance.empty:
        return pd.DataFrame(), {"signals_total": int(len(signals)), "signals_matured_20d": 0, "signals_pending": int(len(signals))}

    perf = performance.copy()
    perf["Tracking_Day"] = pd.to_numeric(perf.get("Tracking_Day"), errors="coerce")
    day_n = perf[perf["Tracking_Day"] == int(target_day)].copy()
    
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
        "Component_Proximity", "Component_Resistance", "Component_Volume", "Component_Trend",
        "Component_Momentum", "Component_ADX", "Component_Squeeze", "Component_Relative_Strength",
        "Component_Candle", "Component_Market_Regime", "Explanation",
    ]
    for col in signal_cols:
        if col not in joined and f"{col}_Signal" in joined:
            joined[col] = joined[f"{col}_Signal"]

    joined["Trade_Setup"] = _derive_trade_setup(joined)

    # Derive Scanner v2 Anti-Trap Flags from saved component scores and explanation string
    comp_vol_num = pd.to_numeric(joined.get("Component_Volume", pd.Series(0.5, index=joined.index)), errors="coerce").fillna(0.5)
    false_bo_bin = _to_binary(joined.get("False_Breakout", pd.Series(False, index=joined.index))).fillna(0.0)
    expl_series = joined.get("Explanation", pd.Series("", index=joined.index)).astype(str)

    has_trap = (false_bo_bin > 0) | (comp_vol_num <= 0.10) | expl_series.str.contains("WARNING", case=False, na=False)
    joined["Anti_Trap_Status"] = np.where(has_trap, "TRAP_WARNING", "CLEAN_SETUP")

    has_20d_acc = expl_series.str.contains("20D accumulation", case=False, na=False) | (comp_vol_num >= 0.70)
    joined["Volume_Accumulation"] = np.where(has_20d_acc, "CONFIRMED", "NEUTRAL")

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
    is_stop_goal: bool = False,
) -> float:
    """Computes a 0-100 composite edge & consistency score to rank combinations."""
    wr = float(win_rate) if np.isfinite(win_rate) else 0.0
    sr = float(stop_rate) if np.isfinite(stop_rate) else 50.0
    ret = float(avg_ret) if np.isfinite(avg_ret) else 0.0

    if is_stop_goal:
        # When evaluating "Stop_Before_Target" (finding trap setups to avoid), higher stop rate = higher warning score
        base = (wr * 0.65) + (np.clip(-ret * 2.5, 0.0, 20.0))
    else:
        base = (wr * 0.50) + (max(0.0, 100.0 - sr) * 0.20) + (np.clip(ret * 2.5, -15.0, 20.0))

    if total_unique_dates > 1:
        dispersion_ratio = min(1.0, unique_dates_count / max(2.0, total_unique_dates * 0.5))
        base += dispersion_ratio * 15.0

    if has_holdout and np.isfinite(train_wr) and np.isfinite(holdout_wr):
        drift = abs(holdout_wr - train_wr)
        if holdout_wr < train_wr - 15.0:
            base -= min(20.0, (train_wr - holdout_wr) * 0.6)
        elif drift <= 10.0 and holdout_wr >= 55.0:
            base += 8.0 

    return round(float(np.clip(base, 0.0, 100.0)), 1)


def analyze_outcome_combinations(
    outcomes: pd.DataFrame,
    outcome_col: str = "T1_Hit",
    thresholds: dict | None = None,
    min_signals: int = 25,
    max_order: int = 3,
) -> pd.DataFrame:
    """Vectorized evaluation of 1-to-N factor combinations on matured outcome data."""
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
    is_stop_goal = str(outcome_col).strip() == "Stop_Before_Target"

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

    for col, label, low_val, high_val in RANGE_CONDITIONS:
        if col not in work.columns:
            continue
        numeric = pd.to_numeric(work[col], errors="coerce").to_numpy(dtype=float)
        mask = np.isfinite(numeric) & (numeric >= low_val) & (numeric <= high_val)
        if int(mask.sum()) >= min_sig:
            condition_list.append((col, label, mask))

    cat_cols = [
        "Trade_Setup", "Cap_Category", "Scanner_Status",
        "EMA_Structure", "Market_Regime", "Candlestick", "False_Breakout",
        "Anti_Trap_Status", "Volume_Accumulation",
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

    outcome_arr = work[outcome_col].to_numpy(dtype=float)
    ret_arr = pd.to_numeric(work.get("Return_20D_Pct", pd.Series(np.nan, index=work.index)), errors="coerce").to_numpy(dtype=float)
    stop_arr = _to_binary(work["Stop_Hit"]).to_numpy(dtype=float) if "Stop_Hit" in work.columns else np.full(n_rows, np.nan)

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

    single_ranked = sorted(
        condition_list,
        key=lambda item: (
            float(np.nanmean(outcome_arr[item[2]]) * 100.0) if item[2].any() else 0.0,
            int(item[2].sum()),
        ),
        reverse=True,
    )
    higher_order_pool = single_ranked[:36] if len(single_ranked) > 36 else single_ranked

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

        # Filter: For positive target outcomes, require >= 50% hit rate and positive return.
        # For "Stop_Before_Target" (trap discovery mode), allow negative returns so user can see high-failure combinations!
        if np.isnan(win_rate) or win_rate < 50.0:
            return
        if not is_stop_goal and (np.isnan(avg_ret) or avg_ret <= 0.0):
            return

        sel_stop = stop_arr[mask]
        valid_stop = sel_stop[np.isfinite(sel_stop)]
        stop_rate = float(valid_stop.mean() * 100.0) if len(valid_stop) else np.nan

        tr_mask = mask & train_mask
        te_mask = mask & test_mask
        tr_n = int(tr_mask.sum())
        te_n = int(te_mask.sum())
        tr_wr = float(np.nanmean(outcome_arr[tr_mask]) * 100.0) if tr_n > 0 else np.nan
        te_wr = float(np.nanmean(outcome_arr[te_mask]) * 100.0) if te_n > 0 else np.nan

        sel_dates = date_codes[mask]
        unique_dt_cnt = len(np.unique(sel_dates[sel_dates >= 0]))

        consistency = _compute_Consistency_Score(
            win_rate, avg_ret, stop_rate, tr_wr, te_wr,
            unique_dt_cnt, total_unique_dates, has_holdout,
            is_stop_goal=is_stop_goal,
        )

        output.append({
            "Analysis_Timestamp_IST": now_string,
            "Outcome_Goal": outcome_col,
            "Setup_Rules": " + ".join(condition_names),
            "Times_Occurred": n_sel,
            "Win_Rate_%": round(win_rate, 2) if np.isfinite(win_rate) else np.nan,
            "Avg_Profit_%": round(avg_ret, 2) if np.isfinite(avg_ret) else np.nan,
            "Stop_Hit_Rate_%": round(stop_rate, 2) if np.isfinite(stop_rate) else np.nan,
            "Overall_Score_(0-100)": consistency,
        })

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
    
    # Sort strictly by our primary metrics
    out = out.sort_values(
        ["Overall_Score_(0-100)", "Win_Rate_%", "Avg_Profit_%", "Times_Occurred"],
        ascending=[False, False, not is_stop_goal, False], na_position="last"
    )

    out = out[ANALYSIS_OUTPUT_COLUMNS].reset_index(drop=True)
    return out
