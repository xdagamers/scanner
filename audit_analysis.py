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
ANALYSIS_OUTPUT_COLUMNS = [
    # Keep the existing Analysis_Results header order first; appended columns
    # are added to the right by Apps Script without deleting prior results.
    "Analysis_Timestamp_IST", "Outcome", "Combination", "Signals",
    "Success_Rate_Pct", "Avg_Return_Pct", "Median_Return_Pct",
    "Avg_Best_Gain_Pct", "Avg_Max_Drawdown_Pct", "Train_Test_Split", "Notes",
    "Train_Signals", "Train_Success_Rate_Pct", "Holdout_Signals",
    "Holdout_Success_Rate_Pct", "Stop_Rate_Pct",
]

# Thresholds are fixed in advance to limit arbitrary curve fitting.
DEFAULT_THRESHOLDS = {
    "Rating": [7, 8, 9, 10],
    "Distance_Pct": [0.5, 1, 2, 3, 5],  # smaller distance is preferable, so <=
    "RVOL": [0.9, 1.15, 1.4, 1.8, 2.5],
    "ADX": [20, 25, 35],
    "RSI": [50, 55, 60, 65, 70],
    "Score": [60, 70, 80, 90],
    "Rank_Score": [40, 50, 60, 70, 80],
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


def _to_binary(series: pd.Series) -> pd.Series:
    if pd.api.types.is_bool_dtype(series):
        return series.astype(float)
    as_text = series.astype(str).str.strip().str.upper()
    mapped = as_text.map({"YES": 1.0, "TRUE": 1.0, "1": 1.0, "NO": 0.0, "FALSE": 0.0, "0": 0.0})
    numeric = pd.to_numeric(series, errors="coerce")
    return mapped.where(mapped.notna(), numeric)


def build_completed_outcomes(signals: pd.DataFrame, performance: pd.DataFrame) -> tuple[pd.DataFrame, dict]:
    """Join immutable signal snapshots to fully valid Day-20 results.

    In addition to “ever touched” flags, derive target-before-stop outcomes.
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
    day20 = perf[perf["Tracking_Day"] == 20].copy()
    # Fail closed: only a row explicitly marked OK can be a final outcome.
    if "Data_Quality" in day20:
        day20 = day20[day20["Data_Quality"].astype(str).str.strip().str.upper().eq("OK")]
    else:
        day20 = day20.iloc[0:0]
    if day20.empty or "Signal_ID" not in signals.columns:
        return pd.DataFrame(), {
            "signals_total": int(len(signals)), "signals_matured_20d": 0,
            "signals_pending": int(len(signals)),
        }
    if "Tracking_Date" in day20.columns:
        day20 = day20.sort_values("Tracking_Date")
    day20 = day20.drop_duplicates("Signal_ID", keep="last")
    joined = signals.merge(day20, on="Signal_ID", how="inner", suffixes=("_Signal", "_Performance"))
    if joined.empty:
        return joined, {"signals_total": int(len(signals)), "signals_matured_20d": 0, "signals_pending": int(len(signals))}

    for col in ["Scan_Date", "Rating", "Distance_Pct", "RVOL", "ADX", "RSI", "Score", "Rank_Score",
                "EMA_Structure", "Market_Regime", "Candlestick", "False_Breakout"]:
        if col not in joined and f"{col}_Signal" in joined:
            joined[col] = joined[f"{col}_Signal"]
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
        target_day = pd.to_numeric(joined.get(day_col, pd.Series(np.nan, index=joined.index)), errors="coerce")
        # A missing target means not reached in the valid 20-session window.
        # A missing stop means no stop during the window. Equal days are ambiguous.
        outcome = pd.Series(0.0, index=joined.index)
        outcome.loc[target_day.notna() & (stop_day.isna() | (target_day < stop_day))] = 1.0
        outcome.loc[target_day.notna() & stop_day.notna() & (target_day == stop_day)] = np.nan
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


def _binary_or_numeric(series: pd.Series) -> pd.Series:
    return _to_binary(series)


def _metrics(frame: pd.DataFrame, outcome_col: str) -> dict:
    outcome = _binary_or_numeric(frame[outcome_col]).dropna() if outcome_col in frame else pd.Series(dtype=float)
    ret = pd.to_numeric(frame.get("Return_20D_Pct", pd.Series(dtype=float)), errors="coerce")
    gain = pd.to_numeric(frame.get("Best_Gain_Pct", pd.Series(dtype=float)), errors="coerce")
    dd = pd.to_numeric(frame.get("Max_Drawdown_Pct", pd.Series(dtype=float)), errors="coerce")
    stop = _binary_or_numeric(frame["Stop_Hit"]).dropna() if "Stop_Hit" in frame else pd.Series(dtype=float)
    return {
        "Signals": int(len(frame)),
        "Success_Rate_Pct": float(outcome.mean() * 100.0) if len(outcome) else np.nan,
        "Avg_Return_Pct": float(ret.mean()) if ret.notna().any() else np.nan,
        "Median_Return_Pct": float(ret.median()) if ret.notna().any() else np.nan,
        "Avg_Best_Gain_Pct": float(gain.mean()) if gain.notna().any() else np.nan,
        "Avg_Max_Drawdown_Pct": float(dd.mean()) if dd.notna().any() else np.nan,
        "Stop_Rate_Pct": float(stop.mean() * 100.0) if len(stop) else np.nan,
    }


def analyze_outcome_combinations(
    outcomes: pd.DataFrame,
    outcome_col: str = "T1_Hit",
    thresholds: dict | None = None,
    min_signals: int = 25,
    max_order: int = 3,
) -> pd.DataFrame:
    """Evaluate singles, pairs, and selected 3-factor combos on 20D-matured data.

    Three-factor combinations only combine distinct feature families. The
    generated results are exploratory; date holdout metrics are shown only when
    enough distinct signal dates exist. This limits overfitting risk.
    """
    if outcomes is None or outcomes.empty or outcome_col not in outcomes.columns:
        return pd.DataFrame(columns=ANALYSIS_OUTPUT_COLUMNS)
    thresholds = thresholds or DEFAULT_THRESHOLDS
    work = outcomes.copy()
    work[outcome_col] = _binary_or_numeric(work[outcome_col])
    # Ambiguous target/stop candles are intentionally omitted from this outcome's
    # success-rate denominator instead of being counted as wins or losses.
    work = work.loc[work[outcome_col].notna()].copy()
    if work.empty:
        return pd.DataFrame(columns=ANALYSIS_OUTPUT_COLUMNS)
    condition_list: list[tuple[str, str, pd.Series]] = []
    for col, values in thresholds.items():
        if col not in work.columns:
            continue
        numeric = pd.to_numeric(work[col], errors="coerce")
        for value in values:
            if col == "Distance_Pct":
                mask = numeric <= value
                label = f"{col}<={value}"
            else:
                mask = numeric >= value
                label = f"{col}>={value}"
            condition_list.append((col, label, mask.fillna(False)))

    # Categorical scanner features add useful combinations without exploding into
    # an unrestricted Cartesian search. Only sufficiently represented categories
    # are tested; numeric features remain governed by the fixed thresholds above.
    for col in ["EMA_Structure", "Market_Regime", "Candlestick", "False_Breakout"]:
        if col not in work.columns:
            continue
        values = work[col].astype(str).str.strip()
        values = values[~values.str.lower().isin(["", "nan", "none", "<na>"])]
        counts = values.value_counts()
        for value, count in counts.items():
            if int(count) < min_signals:
                continue
            label_value = str(value).upper() if col == "False_Breakout" else str(value)
            mask = work[col].astype(str).str.strip().eq(str(value))
            condition_list.append((col, f"{col}={label_value}", mask))

    # Train/test is chronological by signal date. A single-day cohort cannot
    # provide a meaningful time holdout, and is explicitly marked as such.
    dates = pd.to_datetime(work.get("Scan_Date", pd.Series(dtype=str)), errors="coerce").dropna().dt.date
    unique_dates = sorted(set(dates))
    has_holdout = len(unique_dates) >= 5
    if has_holdout:
        cut_idx = max(1, int(len(unique_dates) * 0.8))
        train_dates = set(unique_dates[:cut_idx])
        test_dates = set(unique_dates[cut_idx:])
        scan_dates = pd.to_datetime(work["Scan_Date"], errors="coerce").dt.date
        train_mask = scan_dates.isin(train_dates)
        test_mask = scan_dates.isin(test_dates)
        split_label = f"Train {min(train_dates)}–{max(train_dates)}; holdout {min(test_dates)}–{max(test_dates)}"
    else:
        train_mask = pd.Series(True, index=work.index)
        test_mask = pd.Series(False, index=work.index)
        split_label = "NO_TIME_HOLDOUT: fewer than 5 distinct signal dates"

    output = []
    now_string = datetime.now(IST).strftime("%Y-%m-%d %H:%M:%S IST")

    def add_combo(items):
        mask = pd.Series(True, index=work.index)
        for _, _, part in items:
            mask &= part
        selected = work.loc[mask]
        if len(selected) < min_signals:
            return
        stats = _metrics(selected, outcome_col)
        train_frame = work.loc[mask & train_mask]
        test_frame = work.loc[mask & test_mask]
        train_stats = _metrics(train_frame, outcome_col) if len(train_frame) else {"Success_Rate_Pct": np.nan, "Signals": 0}
        test_stats = _metrics(test_frame, outcome_col) if len(test_frame) else {"Success_Rate_Pct": np.nan, "Signals": 0}
        condition_names = [x[1] for x in items]
        output.append({
            "Analysis_Timestamp_IST": now_string,
            "Outcome": outcome_col,
            "Combination": " AND ".join(condition_names),
            **stats,
            "Train_Test_Split": split_label,
            "Notes": (
                f"Stop rate={stats['Stop_Rate_Pct']:.1f}% if available. "
                f"Train n={train_stats.get('Signals', 0)}, train success={train_stats.get('Success_Rate_Pct', np.nan):.1f}%; "
                f"holdout n={test_stats.get('Signals', 0)}, holdout success={test_stats.get('Success_Rate_Pct', np.nan):.1f}%. "
                "Exploratory result; do not change live scanner until walk-forward/out-of-sample results support it."
            ),
            "Train_Signals": int(train_stats.get("Signals", 0)),
            "Train_Success_Rate_Pct": train_stats.get("Success_Rate_Pct", np.nan),
            "Holdout_Signals": int(test_stats.get("Signals", 0)),
            "Holdout_Success_Rate_Pct": test_stats.get("Success_Rate_Pct", np.nan),
            "Stop_Rate_Pct": stats.get("Stop_Rate_Pct", np.nan),
        })

    for order in range(1, min(max_order, 3) + 1):
        for items in combinations(condition_list, order):
            families = [x[0] for x in items]
            if len(set(families)) != len(families):
                continue
            add_combo(items)

    if not output:
        return pd.DataFrame(columns=ANALYSIS_OUTPUT_COLUMNS)
    out = pd.DataFrame(output, columns=ANALYSIS_OUTPUT_COLUMNS)
    # When chronological holdout results exist, rank primarily by holdout success;
    # otherwise report exploratory full-sample ranking without implying validation.
    if has_holdout and out["Holdout_Success_Rate_Pct"].notna().any():
        out = out.sort_values(
            ["Holdout_Success_Rate_Pct", "Holdout_Signals", "Success_Rate_Pct", "Signals"],
            ascending=[False, False, False, False], na_position="last"
        )
    else:
        out = out.sort_values(
            ["Success_Rate_Pct", "Signals", "Avg_Return_Pct"],
            ascending=[False, False, False], na_position="last"
        )
    return out.reset_index(drop=True)
