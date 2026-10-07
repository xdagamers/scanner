"""Bounded combination analysis for the scanner audit dataset.

The analysis is deliberately kept separate from scanner.py. It evaluates the
observed data rather than changing the live scanner.
"""
from __future__ import annotations

from itertools import combinations
import numpy as np
import pandas as pd

DEFAULT_THRESHOLDS = {
    "Rating": [7, 8, 9, 10],
    "Distance_Pct": [0.5, 1, 2, 3, 5],
    "RVOL": [0.9, 1.15, 1.4, 1.8, 2.5],
    "ADX": [20, 25, 35],
    "RSI": [50, 55, 60, 65, 70],
    "Score": [60, 70, 80, 90],
    "Rank_Score": [40, 50, 60, 70, 80],
}


def _event_pct(group: pd.DataFrame, col: str) -> float:
    return pd.to_numeric(group[col], errors="coerce").mean() if col in group else np.nan


def evaluate_filter(df: pd.DataFrame, outcome_col: str, mask: pd.Series) -> dict:
    g = df.loc[mask].copy()
    if g.empty:
        return {"Signals": 0, "Success_Rate_Pct": np.nan}
    outcome = pd.to_numeric(g[outcome_col], errors="coerce").dropna()
    return {
        "Signals": int(len(g)),
        "Success_Rate_Pct": float(outcome.mean() * 100) if len(outcome) else np.nan,
        "Avg_Return_Pct": _event_pct(g, "Return_20D_Pct"),
        "Median_Return_Pct": pd.to_numeric(g.get("Return_20D_Pct"), errors="coerce").median() if "Return_20D_Pct" in g else np.nan,
        "Avg_Best_Gain_Pct": _event_pct(g, "Best_Gain_Pct"),
        "Avg_Max_Drawdown_Pct": _event_pct(g, "Max_Drawdown_Pct"),
    }


def analyze_single_and_pair_combinations(df: pd.DataFrame, outcome_col: str = "T1_Hit",
                                         thresholds: dict | None = None, min_signals: int = 30) -> pd.DataFrame:
    """Test individual thresholds and bounded pairs; then sort by success rate.

    This intentionally does not brute-force every possible subset of every raw
    value. That would overfit badly. Use the holdout/walk-forward process before
    changing the live scanner.
    """
    thresholds = thresholds or DEFAULT_THRESHOLDS
    work = df.copy()
    rows = []

    conditions = []
    for col, vals in thresholds.items():
        if col not in work.columns:
            continue
        numeric = pd.to_numeric(work[col], errors="coerce")
        for value in vals:
            conditions.append((f"{col}>={value}", numeric >= value))

    for name, mask in conditions:
        stats = evaluate_filter(work, outcome_col, mask)
        if stats["Signals"] >= min_signals:
            rows.append({"Combination": name, **stats})

    for (name_a, mask_a), (name_b, mask_b) in combinations(conditions, 2):
        mask = mask_a & mask_b
        stats = evaluate_filter(work, outcome_col, mask)
        if stats["Signals"] >= min_signals:
            rows.append({"Combination": f"{name_a} AND {name_b}", **stats})

    out = pd.DataFrame(rows)
    if out.empty:
        return out
    return out.sort_values(["Success_Rate_Pct", "Signals"], ascending=[False, False]).reset_index(drop=True)


def walk_forward_split_dates(df: pd.DataFrame, date_col: str = "Scan_Date", train_days: int = 60, test_days: int = 20):
    dates = pd.to_datetime(df[date_col], errors="coerce").dropna().sort_values().unique()
    if len(dates) < train_days + test_days:
        return []
    splits = []
    step = test_days
    i = train_days
    while i + test_days <= len(dates):
        train = dates[:i]
        test = dates[i:i+test_days]
        splits.append((train[0], train[-1], test[0], test[-1]))
        i += step
    return splits
