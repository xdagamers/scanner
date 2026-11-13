"""Matured-signal reconciliation and bounded combination analysis (Phase 3 Upgraded).

The live scanner never imports this module. This is research-only code that
compares saved signal-day features with observed 20-trading-day outcomes.

Upgrades implemented in Phase 3:
  1. Strict Triggered-Trade Outcome Filtering & Legacy Self-Healing:
     In build_completed_outcomes(), all trade execution outcomes (T1/T2/T3_Hit,
     T1/T2/T3_Before_Stop, Stop_Hit, Stop_Before_Target) are restricted strictly to
     signals that actually crossed Breakout_Trigger (Breakout_Hit == 1). Untriggered
     signals are masked as NaN on post-entry trade outcomes so they never corrupt
     win-rate or stop-rate calculations, while remaining available when evaluating
     "Breakout_Hit" (trigger conversion rate).
     Also self-heals legacy Daily_Performance rows where a pre-trigger dip below Stop
     was recorded before Breakout_First_Day.
  2. Trigger-Anchored Return Reconciliation:
     Reconciles Return_20D_Pct against Breakout_Trigger_Current_Basis (or Breakout_Trigger)
     for triggered trades so historical rows reflect true post-trigger trade returns.
  3. Phase 1 & 3 Feature Integration:
     Integrates Sector_Relative_Strength_Pct (now computed in Phase 1 scanner.py),
     Scale-Invariant MACD (% of price), Deliverable Turnover in ₹ Cr, and 4-Pillar
     Institutional Synergy rules (RSI + MACD + ADX + Delivery/Volume).
"""
from __future__ import annotations

from itertools import combinations
from datetime import datetime
from zoneinfo import ZoneInfo

import numpy as np
import pandas as pd

IST = ZoneInfo("Asia/Kolkata")

# Exact schema expected by app.py and Google Sheets Analysis_Results tab
ANALYSIS_OUTPUT_COLUMNS = [
    "Analysis_Timestamp_IST",
    "Outcome_Goal",
    "Setup_Rules",
    "Times_Occurred",
    "Win_Rate_%",
    "Avg_Profit_%",
    "Stop_Hit_Rate_%",
    "Overall_Score_(0-100)",
]

# Distinct feature families so combinations mix complementary dimensions
# (e.g., RSI + MACD + ADX + Delivery + Sector RS + Proximity) without pairing collinear duplicates.
FAMILY_MAP = {
    "Rating": "OVERALL_QUALITY",
    "Score": "OVERALL_QUALITY",
    "Rank_Score": "OVERALL_QUALITY",
    "Distance_Pct": "PROXIMITY",
    "Component_Proximity": "PROXIMITY",
    "Pct_Below_52W_High": "STRUCTURAL_HIGH_PROXIMITY",
    "RVOL": "VOLUME_DEMAND",
    "Component_Volume": "VOLUME_DEMAND",
    "UD_Vol_Ratio_20D": "VOLUME_ACCUMULATION",
    "Volume_Accumulation": "VOLUME_ACCUMULATION",
    "Delivery_Pct": "INSTITUTIONAL_DELIVERY_PCT",
    "Deliverable_Qty": "INSTITUTIONAL_DELIVERY_QTY",
    "Deliverable_Turnover_Cr": "INSTITUTIONAL_DELIVERY_QTY",
    "Delivery_Conviction": "INSTITUTIONAL_DELIVERY_SYNERGY",
    "ADX": "TREND_STRENGTH",
    "Component_ADX": "TREND_STRENGTH",
    "EMA_Structure": "TREND_STRUCTURE",
    "Component_Trend": "TREND_STRUCTURE",
    "RSI": "RSI_MOMENTUM",
    "Component_Momentum": "RSI_MOMENTUM",
    "MACD": "MACD_MOMENTUM",
    "MACD_Pct_Price": "MACD_MOMENTUM",
    "MACD_Regime": "MACD_MOMENTUM",
    "Candle_CLV": "CANDLE_CLOSING_STRENGTH",
    "Candlestick": "CANDLE_PATTERN",
    "Component_Candle": "CANDLE_PATTERN",
    "ATR_Ratio": "VOLATILITY_SQUEEZE",
    "Component_Squeeze": "VOLATILITY_SQUEEZE",
    "NIFTY_Relative_Strength_Pct": "RELATIVE_STRENGTH",
    "Relative_Strength_60D_Pct": "RELATIVE_STRENGTH",
    "Component_Relative_Strength": "RELATIVE_STRENGTH",
    "Sector_Relative_Strength_Pct": "SECTOR_RELATIVE_STRENGTH",
    "Resistance_Touches": "RESISTANCE_QUALITY",
    "Component_Resistance": "RESISTANCE_QUALITY",
    "Risk_Reward": "RISK_REWARD",
    "Market_Regime": "MARKET_REGIME",
    "Component_Market_Regime": "MARKET_REGIME",
    "Cap_Category": "CAP_SEGMENT",
    "Trade_Setup": "SETUP_HORIZON",
    "Scanner_Status": "BREAKOUT_STATUS",
    "False_Breakout": "TRAP_RISK",
    "Anti_Trap_Status": "TRAP_RISK",
    "Institutional_Synergy": "COMPOSITE_ARCHETYPE",
}

# Crisp, non-overlapping institutional tiers aligned with Scanner v3
DEFAULT_THRESHOLDS = {
    "Rating": [7, 8],
    "Score": [65, 75, 82],
    "Rank_Score": [65, 75, 82],
    "Distance_Pct": [1.0, 2.0, 3.5],
    "Pct_Below_52W_High": [5.0, 10.0, 15.0],
    "RVOL": [1.25, 1.5, 2.0],
    "UD_Vol_Ratio_20D": [1.2, 1.35, 1.6],
    "Delivery_Pct": [45, 55, 65],
    "Deliverable_Qty": [100_000, 250_000, 500_000],
    "Deliverable_Turnover_Cr": [2.5, 5.0, 15.0],
    "ADX": [20, 25, 30],
    "RSI": [55, 60, 65],
    "MACD": [0.0, 1.0],
    "MACD_Pct_Price": [0.15, 0.35, 0.75],
    "Candle_CLV": [0.55, 0.70],
    "Resistance_Touches": [3, 4],
    "Risk_Reward": [1.5, 2.0, 2.5],
    "NIFTY_Relative_Strength_Pct": [2.0, 5.0, 10.0],
    "Sector_Relative_Strength_Pct": [2.0, 5.0, 8.0],
    "Relative_Strength_60D_Pct": [5.0, 12.0],
    "Component_Volume": [0.70, 0.85],
    "Component_Trend": [0.75, 0.90],
    "Component_Momentum": [0.80, 0.90],
    "Component_ADX": [0.70, 0.85],
    "Component_Squeeze": [0.65, 0.85],
    "Component_Relative_Strength": [0.60, 0.78, 0.95],
}

# Bounded range conditions capture "sweet spot" zones without parabolic exhaustion
RANGE_CONDITIONS = [
    ("RSI", "RSI_55_68_PrimeZone", 55.0, 68.0),
    ("RSI", "RSI_54_70_SweetSpot", 54.0, 70.0),
    ("RSI", "RSI_60_72_PowerMomentum", 60.0, 72.0),
    ("ADX", "ADX_20_35_SweetSpotTrend", 20.0, 35.0),
    ("ADX", "ADX_22_40_InstitutionalTrend", 22.0, 40.0),
    ("MACD_Pct_Price", "MACD_Pct_0.10_1.50_HealthySpread", 0.10, 1.50),
    ("MACD_Pct_Price", "MACD_Pct_0.25_2.50_StrongImpulse", 0.25, 2.50),
    ("Delivery_Pct", "Delivery_Pct_50_85_DematAccumulation", 50.0, 85.0),
    ("Delivery_Pct", "Delivery_Pct_55_90_HeavyDelivery", 55.0, 90.0),
    ("UD_Vol_Ratio_20D", "UD_Vol_1.25_2.50_SteadyAccumulation", 1.25, 2.50),
    ("Candle_CLV", "Candle_CLV_0.60_1.00_HighClose", 0.60, 1.00),
    ("Distance_Pct", "Distance_-0.5_2.0_TriggerZone", -0.5, 2.0),
    ("Distance_Pct", "Distance_0.0_3.0_PreBreakout", 0.0, 3.0),
    ("Pct_Below_52W_High", "Within_8Pct_Of_52W_High", 0.0, 8.0),
    ("ATR_Ratio", "ATR_Ratio_<=0.85_VCP_Squeeze", 0.20, 0.85),
    ("ATR_Ratio", "ATR_Ratio_<=0.95_TightBase", 0.20, 0.95),
]

# Columns where "<=" is the constructive direction
LESS_EQUAL_THRESHOLD_COLS = {"Distance_Pct", "Pct_Below_52W_High"}


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


def _engineer_institutional_features(joined: pd.DataFrame) -> pd.DataFrame:
    """Engineers scale-invariant MACD, Deliverable Turnover, and multi-factor synergy states."""
    idx = joined.index
    price = pd.to_numeric(joined.get("Price", pd.Series(np.nan, index=idx)), errors="coerce")
    rsi = pd.to_numeric(joined.get("RSI", pd.Series(np.nan, index=idx)), errors="coerce")
    macd_val = pd.to_numeric(joined.get("MACD", pd.Series(np.nan, index=idx)), errors="coerce")
    adx_val = pd.to_numeric(joined.get("ADX", pd.Series(np.nan, index=idx)), errors="coerce")
    rvol = pd.to_numeric(joined.get("RVOL", pd.Series(np.nan, index=idx)), errors="coerce")
    deliv_pct = pd.to_numeric(joined.get("Delivery_Pct", pd.Series(np.nan, index=idx)), errors="coerce")
    deliv_qty = pd.to_numeric(joined.get("Deliverable_Qty", pd.Series(np.nan, index=idx)), errors="coerce")
    dist_pct = pd.to_numeric(joined.get("Distance_Pct", pd.Series(np.nan, index=idx)), errors="coerce")
    atr_ratio = pd.to_numeric(joined.get("ATR_Ratio", pd.Series(np.nan, index=idx)), errors="coerce")

    comp_vol = pd.to_numeric(joined.get("Component_Volume", pd.Series(0.5, index=idx)), errors="coerce").fillna(0.5)
    comp_mom = pd.to_numeric(joined.get("Component_Momentum", pd.Series(0.5, index=idx)), errors="coerce").fillna(0.5)
    ema_struct = joined.get("EMA_Structure", pd.Series("", index=idx)).astype(str).str.strip()
    expl_series = joined.get("Explanation", pd.Series("", index=idx)).astype(str)

    # 1. Native Scanner Columns with Fallback to Explanation Regex for Legacy Rows
    ud_native = pd.to_numeric(joined.get("UD_Vol_Ratio_20D", pd.Series(np.nan, index=idx)), errors="coerce")
    ud_extracted = pd.to_numeric(
        expl_series.str.extract(r"20D accumulation \(([0-9.]+)x U/D vol\)", expand=False),
        errors="coerce",
    )
    joined["UD_Vol_Ratio_20D"] = ud_native.where(ud_native.notna(), ud_extracted)
    ud_ratio = joined["UD_Vol_Ratio_20D"]

    clv_native = pd.to_numeric(joined.get("Candle_CLV", pd.Series(np.nan, index=idx)), errors="coerce")
    joined["Candle_CLV"] = clv_native
    clv = joined["Candle_CLV"].fillna(0.5)

    pct_52w_native = pd.to_numeric(joined.get("Pct_Below_52W_High", pd.Series(np.nan, index=idx)), errors="coerce")
    joined["Pct_Below_52W_High"] = pct_52w_native

    # 2. Scale-Invariant MACD (% of Price) & MACD Regime
    valid_price = price.where(price > 0, np.nan)
    joined["MACD_Pct_Price"] = (macd_val / valid_price) * 100.0
    macd_pct = joined["MACD_Pct_Price"]

    macd_regime = pd.Series("MACD_NEUTRAL_OR_BEARISH", index=idx, dtype=object)
    macd_pos = macd_val > 0
    macd_expanding = macd_pos & ((comp_mom >= 0.85) | (macd_pct >= 0.25))
    macd_regime.loc[macd_pos] = "MACD_POSITIVE"
    macd_regime.loc[macd_expanding] = "MACD_BULLISH_EXPANSION"
    macd_regime.loc[macd_val < 0] = "MACD_NEGATIVE_DRAG"
    joined["MACD_Regime"] = macd_regime

    # 3. Deliverable Turnover in ₹ Crores & Institutional Delivery Conviction
    joined["Deliverable_Turnover_Cr"] = (valid_price * deliv_qty) / 10_000_000.0
    deliv_cr = joined["Deliverable_Turnover_Cr"]

    deliv_conviction = pd.Series("DELIVERY_UNSPECIFIED", index=idx, dtype=object)
    has_deliv = deliv_pct.notna()
    deliv_conviction.loc[has_deliv & (deliv_pct < 35.0)] = "LOW_DELIVERY_SPECULATIVE"
    deliv_conviction.loc[has_deliv & (deliv_pct >= 35.0) & (deliv_pct < 50.0)] = "MODERATE_DELIVERY"
    deliv_conviction.loc[has_deliv & (deliv_pct >= 50.0)] = "HIGH_DELIVERY_ACCUMULATION"
    inst_footprint = (
        has_deliv
        & (deliv_pct >= 50.0)
        & ((rvol >= 1.25) | (ud_ratio >= 1.25) | (deliv_cr >= 5.0) | (deliv_qty >= 200_000))
        & (clv >= 0.50)
    )
    deliv_conviction.loc[inst_footprint] = "INSTITUTIONAL_DEMAT_ABSORPTION"
    joined["Delivery_Conviction"] = deliv_conviction

    # 4. Anti-Trap Status (Native Trap Flags + Legacy Fallback)
    false_bo_bin = _to_binary(joined.get("False_Breakout", pd.Series(False, index=idx))).fillna(0.0)
    dist_trap_bin = _to_binary(joined.get("Distribution_Trap", pd.Series(False, index=idx))).fillna(0.0)
    wall_trap_bin = _to_binary(joined.get("Overhead_Wall_Trap", pd.Series(False, index=idx))).fillna(0.0)
    overext_trap_bin = _to_binary(joined.get("Overextended_Trap", pd.Series(False, index=idx))).fillna(0.0)

    has_trap = (
        (false_bo_bin > 0)
        | (dist_trap_bin > 0)
        | (wall_trap_bin > 0)
        | (overext_trap_bin > 0)
        | (comp_vol <= 0.10)
        | expl_series.str.contains("WARNING", case=False, na=False)
    )
    joined["Anti_Trap_Status"] = np.where(has_trap, "TRAP_WARNING", "CLEAN_SETUP")

    has_20d_acc = (
        (ud_ratio >= 1.25)
        | expl_series.str.contains("20D accumulation", case=False, na=False)
        | (comp_vol >= 0.70)
    )
    joined["Volume_Accumulation"] = np.where(has_20d_acc, "ACCUMULATION_CONFIRMED", "NEUTRAL_OR_LOW")

    # 5. Multi-Factor Institutional Synergy Archetypes (RSI + MACD + ADX + Delivery working together)
    synergy = pd.Series("STANDARD_SETUP", index=idx, dtype=object)

    trinity_mask = (
        (rsi >= 55.0) & (rsi <= 70.0)
        & (macd_val > 0)
        & (adx_val >= 20.0) & (adx_val <= 42.0)
        & ema_struct.eq("Bullish")
        & (~has_trap)
    )
    synergy.loc[trinity_mask] = "TRINITY_RSI_MACD_ADX_ALIGNED"

    vcp_spring_mask = (
        (atr_ratio <= 0.92)
        & has_20d_acc
        & (rsi >= 54.0) & (rsi <= 70.0)
        & (macd_val >= 0)
        & (~has_trap)
    )
    synergy.loc[vcp_spring_mask] = "VCP_ACCUMULATION_SPRING"

    sniper_mask = (
        (dist_pct >= -0.5) & (dist_pct <= 3.0)
        & (rsi >= 55.0) & (rsi <= 70.0)
        & (macd_val > 0)
        & (adx_val >= 20.0)
        & ((deliv_pct >= 50.0) | (rvol >= 1.35) | (ud_ratio >= 1.30))
        & (~has_trap)
    )
    synergy.loc[sniper_mask] = "SNIPER_INSTITUTIONAL_BREAKOUT"

    trap_archetype_mask = (
        has_trap
        | (rsi > 74.0)
        | (rsi < 48.0)
        | ((rvol >= 1.4) & has_deliv & (deliv_pct < 32.0))
        | ((adx_val < 16.0) & (macd_val < 0))
    )
    synergy.loc[trap_archetype_mask & (~trinity_mask) & (~sniper_mask)] = "HIGH_TRAP_OR_CHURN_RISK"

    joined["Institutional_Synergy"] = synergy
    return joined


def build_completed_outcomes(
    signals: pd.DataFrame,
    performance: pd.DataFrame,
    target_day: int = 20,
) -> tuple[pd.DataFrame, dict]:
    """Join immutable signal snapshots to valid Day-N results and enforce Triggered-Trade Outcome rules."""
    empty_summary = {
        "signals_total": int(len(signals)) if signals is not None else 0,
        "signals_matured_20d": 0,
        "signals_triggered_20d": 0,
        "signals_untriggered_20d": 0,
        "signals_pending": int(len(signals)) if signals is not None else 0,
    }
    if signals is None or signals.empty:
        return pd.DataFrame(), empty_summary
    if performance is None or performance.empty:
        return pd.DataFrame(), empty_summary

    perf = performance.copy()
    perf["Tracking_Day"] = pd.to_numeric(perf.get("Tracking_Day"), errors="coerce")
    day_n = perf[perf["Tracking_Day"] == int(target_day)].copy()

    if "Data_Quality" in day_n:
        day_n = day_n[day_n["Data_Quality"].astype(str).str.strip().str.upper().eq("OK")]
    else:
        day_n = day_n.iloc[0:0]

    if day_n.empty or "Signal_ID" not in signals.columns:
        return pd.DataFrame(), empty_summary

    if "Tracking_Date" in day_n.columns:
        day_n = day_n.sort_values("Tracking_Date")
    day_n = day_n.drop_duplicates("Signal_ID", keep="last")
    joined = signals.merge(day_n, on="Signal_ID", how="inner", suffixes=("_Signal", "_Performance"))

    if joined.empty:
        return joined, empty_summary

    signal_cols = [
        "Scan_Date", "Price", "Breakout_Level", "Breakout_Trigger",
        "Rating", "Distance_Pct", "RVOL", "ADX", "RSI", "MACD",
        "Score", "Rank_Score", "EMA_Structure", "Market_Regime", "Candlestick",
        "False_Breakout", "Cap_Category", "Scanner_Status", "Delivery_Pct", "Deliverable_Qty",
        "Resistance_Touches", "Resistance_Recency", "Risk_Reward",
        "NIFTY_Relative_Strength_Pct", "Sector_Relative_Strength_Pct", "Relative_Strength_60D_Pct",
        "ATR_Pct", "ATR_Ratio",
        "Component_Proximity", "Component_Resistance", "Component_Volume", "Component_Trend",
        "Component_Momentum", "Component_ADX", "Component_Squeeze", "Component_Relative_Strength",
        "Component_Candle", "Component_Market_Regime", "Explanation",
        "UD_Vol_Ratio_20D", "Candle_CLV", "Pct_Below_52W_High",
        "Distribution_Trap", "Overhead_Wall_Trap", "Overextended_Trap",
    ]
    for col in signal_cols:
        if col not in joined and f"{col}_Signal" in joined:
            joined[col] = joined[f"{col}_Signal"]

    joined["Trade_Setup"] = _derive_trade_setup(joined)
    joined = _engineer_institutional_features(joined)

    # --- Phase 3 Fix: Triggered-Trade Outcome Rules & Legacy Self-Healing ---
    for outcome in ["Breakout_Hit", "T1_Hit", "T2_Hit", "T3_Hit", "Stop_Hit"]:
        if outcome in joined:
            joined[outcome] = _to_binary(joined[outcome])

    b_day = pd.to_numeric(joined.get("Breakout_First_Day", pd.Series(np.nan, index=joined.index)), errors="coerce")
    b_hit = joined.get("Breakout_Hit", pd.Series(0.0, index=joined.index)).fillna(0.0)
    triggered_mask = (b_hit > 0.0) | b_day.notna()
    joined["Breakout_Hit"] = np.where(triggered_mask, 1.0, 0.0)

    stop_day_raw = pd.to_numeric(joined.get("Stop_First_Day", pd.Series(np.nan, index=joined.index)), errors="coerce")
    # Self-heal legacy rows where a stop was logged on a day strictly prior to Breakout_First_Day
    pre_trigger_stop_mask = stop_day_raw.notna() & b_day.notna() & (stop_day_raw < b_day)
    stop_day = stop_day_raw.where(~pre_trigger_stop_mask, np.nan)
    joined["Stop_First_Day"] = stop_day

    if "Stop_Hit" in joined.columns:
        stop_hit_clean = joined["Stop_Hit"].where(~pre_trigger_stop_mask, 0.0)
        joined["Stop_Hit"] = stop_hit_clean.where(triggered_mask, np.nan)

    for hit_col, day_col in [("T1_Hit", "T1_First_Day"), ("T2_Hit", "T2_First_Day"), ("T3_Hit", "T3_First_Day")]:
        t_day = pd.to_numeric(joined.get(day_col, pd.Series(np.nan, index=joined.index)), errors="coerce")
        if hit_col in joined.columns:
            joined[hit_col] = joined[hit_col].where(triggered_mask, np.nan)

    for label, day_col in [
        ("T1_Before_Stop", "T1_First_Day"),
        ("T2_Before_Stop", "T2_First_Day"),
        ("T3_Before_Stop", "T3_First_Day"),
    ]:
        t_day = pd.to_numeric(joined.get(day_col, pd.Series(np.nan, index=joined.index)), errors="coerce")
        outcome = pd.Series(np.nan, index=joined.index, dtype=float)
        outcome.loc[triggered_mask] = 0.0
        win_cond = triggered_mask & t_day.notna() & (stop_day.isna() | (t_day < stop_day))
        ambig_cond = triggered_mask & t_day.notna() & stop_day.notna() & (t_day == stop_day)
        outcome.loc[win_cond] = 1.0
        outcome.loc[ambig_cond] = np.nan
        joined[label] = outcome

    # Recompute Stop_Before_Target strictly for triggered trades using sanitized stop_day vs earliest target day
    t1_d = pd.to_numeric(joined.get("T1_First_Day", pd.Series(np.nan, index=joined.index)), errors="coerce")
    t2_d = pd.to_numeric(joined.get("T2_First_Day", pd.Series(np.nan, index=joined.index)), errors="coerce")
    t3_d = pd.to_numeric(joined.get("T3_First_Day", pd.Series(np.nan, index=joined.index)), errors="coerce")
    earliest_target_day = pd.concat([t1_d, t2_d, t3_d], axis=1).min(axis=1)

    stop_first = pd.Series(np.nan, index=joined.index, dtype=float)
    stop_first.loc[triggered_mask] = 0.0
    stop_win_cond = triggered_mask & stop_day.notna() & (earliest_target_day.isna() | (stop_day < earliest_target_day))
    stop_ambig_cond = triggered_mask & stop_day.notna() & earliest_target_day.notna() & (stop_day == earliest_target_day)
    stop_first.loc[stop_win_cond] = 1.0
    stop_first.loc[stop_ambig_cond] = np.nan
    joined["Stop_Before_Target"] = stop_first

    # Reconcile Trigger-Anchored Return_20D_Pct for triggered trades
    raw_close_ret = pd.to_numeric(joined.get("Close_Return_Pct", pd.Series(np.nan, index=joined.index)), errors="coerce")
    close_20d = pd.to_numeric(joined.get("Close", pd.Series(np.nan, index=joined.index)), errors="coerce")
    split_rat = pd.to_numeric(joined.get("Cumulative_Split_Ratio", pd.Series(1.0, index=joined.index)), errors="coerce").fillna(1.0)
    split_rat = split_rat.where(split_rat > 0, 1.0)
    trig_price = pd.to_numeric(joined.get("Breakout_Trigger", pd.Series(np.nan, index=joined.index)), errors="coerce")

    recalc_trig_ret = (((close_20d * split_rat) / trig_price.where(trig_price > 0, np.nan)) - 1.0) * 100.0
    ret_20d = recalc_trig_ret.where(recalc_trig_ret.notna(), raw_close_ret)
    joined["Return_20D_Pct"] = ret_20d.where(triggered_mask, np.nan)

    for col in ["Best_Gain_Pct", "Max_Drawdown_Pct"]:
        if col in joined:
            joined[col] = pd.to_numeric(joined[col], errors="coerce").where(triggered_mask, np.nan)

    matured_cnt = int(joined["Signal_ID"].nunique())
    triggered_cnt = int(joined.loc[triggered_mask, "Signal_ID"].nunique())
    untriggered_cnt = max(0, matured_cnt - triggered_cnt)

    return joined, {
        "signals_total": int(len(signals)),
        "signals_matured_20d": matured_cnt,
        "signals_triggered_20d": triggered_cnt,
        "signals_untriggered_20d": untriggered_cnt,
        "signals_pending": max(0, int(len(signals)) - matured_cnt),
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
    n_sel: int = 15,
    min_sig: int = 15,
    is_stop_goal: bool = False,
    n_factors: int = 1,
) -> float:
    """Computes a 0-100 composite edge & consistency score with sample-size & multi-factor synergy weighting."""
    wr = float(win_rate) if np.isfinite(win_rate) else 0.0
    sr = float(stop_rate) if np.isfinite(stop_rate) else 50.0
    ret = float(avg_ret) if np.isfinite(avg_ret) else 0.0

    sample_bonus = min(7.0, max(0.0, (n_sel - min_sig) / max(5.0, float(min_sig))) * 4.0)
    synergy_bonus = min(4.0, max(0, n_factors - 1) * 1.5) if wr >= 60.0 else 0.0

    if is_stop_goal:
        base = (wr * 0.60) + (np.clip(-ret * 2.5, 0.0, 20.0)) + sample_bonus + synergy_bonus
    else:
        base = (wr * 0.48) + (max(0.0, 100.0 - sr) * 0.20) + (np.clip(ret * 2.2, -15.0, 18.0)) + sample_bonus + synergy_bonus

    if total_unique_dates > 1:
        dispersion_ratio = min(1.0, unique_dates_count / max(2.0, total_unique_dates * 0.5))
        base += dispersion_ratio * 12.0

    if has_holdout and np.isfinite(train_wr) and np.isfinite(holdout_wr):
        drift = abs(holdout_wr - train_wr)
        if holdout_wr < train_wr - 15.0:
            base -= min(20.0, (train_wr - holdout_wr) * 0.6)
        elif drift <= 10.0 and holdout_wr >= 55.0:
            base += 7.0

    return round(float(np.clip(base, 0.0, 100.0)), 1)


def analyze_outcome_combinations(
    outcomes: pd.DataFrame,
    outcome_col: str = "T1_Hit",
    thresholds: dict | None = None,
    min_signals: int = 25,
    max_order: int = 3,
) -> pd.DataFrame:
    """Vectorized evaluation of 1-to-N factor combinations on matured triggered outcome data."""
    if outcomes is None or outcomes.empty or outcome_col not in outcomes.columns:
        return pd.DataFrame(columns=ANALYSIS_OUTPUT_COLUMNS)

    thresholds = thresholds or DEFAULT_THRESHOLDS
    work = outcomes.copy()
    work[outcome_col] = _to_binary(work[outcome_col])
    # Automatically filters to triggered trades for T1/T2/T3/Stop goals (where untriggered rows are NaN)
    work = work.loc[work[outcome_col].notna()].copy()

    if work.empty:
        return pd.DataFrame(columns=ANALYSIS_OUTPUT_COLUMNS)

    if "Trade_Setup" not in work.columns:
        work["Trade_Setup"] = _derive_trade_setup(work)
    if "Institutional_Synergy" not in work.columns or "MACD_Pct_Price" not in work.columns:
        work = _engineer_institutional_features(work)

    n_rows = len(work)
    min_sig = max(1, int(min_signals))
    if n_rows < min_sig:
        return pd.DataFrame(columns=ANALYSIS_OUTPUT_COLUMNS)

    is_stop_goal = str(outcome_col).strip() == "Stop_Before_Target"
    is_breakout_goal = str(outcome_col).strip() == "Breakout_Hit"

    condition_list: list[tuple[str, str, np.ndarray]] = []

    for col, values in thresholds.items():
        if col not in work.columns:
            continue
        fam = FAMILY_MAP.get(col, col)
        numeric = pd.to_numeric(work[col], errors="coerce").to_numpy(dtype=float)
        for value in values:
            if col in LESS_EQUAL_THRESHOLD_COLS:
                mask = np.isfinite(numeric) & (numeric <= float(value))
                label = f"{col}<={value}%"
            elif col == "Deliverable_Qty":
                mask = np.isfinite(numeric) & (numeric >= float(value))
                label = f"Deliverable_Qty>={int(value):,}"
            elif col == "Deliverable_Turnover_Cr":
                mask = np.isfinite(numeric) & (numeric >= float(value))
                label = f"Deliv_Turnover>=₹{value}Cr"
            elif col == "MACD_Pct_Price":
                mask = np.isfinite(numeric) & (numeric >= float(value))
                label = f"MACD_Pct>={value}%"
            else:
                mask = np.isfinite(numeric) & (numeric >= float(value))
                label = f"{col}>={value}"
            if int(mask.sum()) >= min_sig:
                condition_list.append((fam, label, mask))

    for col, label, low_val, high_val in RANGE_CONDITIONS:
        if col not in work.columns:
            continue
        fam = FAMILY_MAP.get(col, col)
        numeric = pd.to_numeric(work[col], errors="coerce").to_numpy(dtype=float)
        mask = np.isfinite(numeric) & (numeric >= low_val) & (numeric <= high_val)
        if int(mask.sum()) >= min_sig:
            condition_list.append((fam, label, mask))

    if is_stop_goal:
        if "RSI" in work.columns:
            rsi_num = pd.to_numeric(work["RSI"], errors="coerce").to_numpy(dtype=float)
            m_overbought = np.isfinite(rsi_num) & (rsi_num > 72.0)
            if int(m_overbought.sum()) >= min_sig:
                condition_list.append(("RSI_MOMENTUM", "RSI>72_Overheated", m_overbought))
            m_weak_rsi = np.isfinite(rsi_num) & (rsi_num < 52.0)
            if int(m_weak_rsi.sum()) >= min_sig:
                condition_list.append(("RSI_MOMENTUM", "RSI<52_WeakMomentum", m_weak_rsi))
        if "MACD" in work.columns:
            macd_num = pd.to_numeric(work["MACD"], errors="coerce").to_numpy(dtype=float)
            m_neg_macd = np.isfinite(macd_num) & (macd_num < 0.0)
            if int(m_neg_macd.sum()) >= min_sig:
                condition_list.append(("MACD_MOMENTUM", "MACD<0_BearishMomentum", m_neg_macd))
        if "ADX" in work.columns:
            adx_num = pd.to_numeric(work["ADX"], errors="coerce").to_numpy(dtype=float)
            m_choppy = np.isfinite(adx_num) & (adx_num < 18.0)
            if int(m_choppy.sum()) >= min_sig:
                condition_list.append(("TREND_STRENGTH", "ADX<18_ChoppyRange", m_choppy))
        if "RVOL" in work.columns:
            rvol_num = pd.to_numeric(work["RVOL"], errors="coerce").to_numpy(dtype=float)
            m_low_vol = np.isfinite(rvol_num) & (rvol_num < 1.0)
            if int(m_low_vol.sum()) >= min_sig:
                condition_list.append(("VOLUME_DEMAND", "RVOL<1.0_LowDemand", m_low_vol))
        if "Delivery_Pct" in work.columns:
            deliv_num = pd.to_numeric(work["Delivery_Pct"], errors="coerce").to_numpy(dtype=float)
            m_low_deliv = np.isfinite(deliv_num) & (deliv_num < 35.0)
            if int(m_low_deliv.sum()) >= min_sig:
                condition_list.append(("INSTITUTIONAL_DELIVERY_PCT", "Delivery_Pct<35_IntradayChurn", m_low_deliv))
        if "Candle_CLV" in work.columns:
            clv_num = pd.to_numeric(work["Candle_CLV"], errors="coerce").to_numpy(dtype=float)
            m_weak_clv = np.isfinite(clv_num) & (clv_num < 0.40)
            if int(m_weak_clv.sum()) >= min_sig:
                condition_list.append(("CANDLE_CLOSING_STRENGTH", "Candle_CLV<0.40_UpperWickRejection", m_weak_clv))

    cat_cols = [
        "Institutional_Synergy",
        "MACD_Regime",
        "Delivery_Conviction",
        "Volume_Accumulation",
        "Anti_Trap_Status",
        "Trade_Setup",
        "Cap_Category",
        "Scanner_Status",
        "EMA_Structure",
        "Market_Regime",
        "Candlestick",
        "False_Breakout",
    ]
    for col in cat_cols:
        if col not in work.columns:
            continue
        fam = FAMILY_MAP.get(col, col)
        series_str = work[col].astype(str).str.strip()
        valid_mask = ~series_str.str.lower().isin(["", "nan", "none", "<na>", "delivery_unspecified", "standard_setup"])
        counts = series_str[valid_mask].value_counts()
        for value, count in counts.items():
            if int(count) < min_sig:
                continue
            label_value = str(value).upper() if col == "False_Breakout" else str(value)
            mask = series_str.eq(str(value)).to_numpy(dtype=bool)
            condition_list.append((fam, f"{col}={label_value}", mask))

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

    CORE_FAMILIES = {
        "RSI_MOMENTUM",
        "MACD_MOMENTUM",
        "TREND_STRENGTH",
        "INSTITUTIONAL_DELIVERY_PCT",
        "INSTITUTIONAL_DELIVERY_QTY",
        "INSTITUTIONAL_DELIVERY_SYNERGY",
        "VOLUME_ACCUMULATION",
        "VOLUME_DEMAND",
        "SECTOR_RELATIVE_STRENGTH",
        "COMPOSITE_ARCHETYPE",
    }

    single_ranked = sorted(
        condition_list,
        key=lambda item: (
            (float(np.nanmean(outcome_arr[item[2]]) * 100.0) if item[2].any() else 0.0)
            + (3.0 if item[0] in CORE_FAMILIES else 0.0),
            int(item[2].sum()),
        ),
        reverse=True,
    )
    higher_order_pool = single_ranked[:44] if len(single_ranked) > 44 else single_ranked

    output = []
    now_string = datetime.now(IST).strftime("%Y-%m-%d %H:%M:%S IST")

    def evaluate_mask(mask: np.ndarray, condition_names: list[str], min_req: int):
        n_sel = int(mask.sum())
        if n_sel < min_req:
            return

        sel_out = outcome_arr[mask]
        win_rate = float(np.nanmean(sel_out) * 100.0) if len(sel_out) else np.nan

        sel_ret = ret_arr[mask]
        valid_ret = sel_ret[np.isfinite(sel_ret)]
        avg_ret = float(valid_ret.mean()) if len(valid_ret) else (0.0 if is_breakout_goal else np.nan)

        if np.isnan(win_rate) or win_rate < 50.0:
            return
        if not is_stop_goal and not is_breakout_goal and (np.isnan(avg_ret) or avg_ret <= 0.0):
            return

        sel_stop = stop_arr[mask]
        valid_stop = sel_stop[np.isfinite(sel_stop)]
        stop_rate = float(valid_stop.mean() * 100.0) if len(valid_stop) else 0.0

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
            n_sel=n_sel, min_sig=min_req, is_stop_goal=is_stop_goal,
            n_factors=len(condition_names),
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
                evaluate_mask(combined_mask, [x[1] for x in items], min_sig)

    # Dedicated 4-Factor Institutional Core Pass (RSI + MACD + ADX + Delivery/Volume)
    rsi_pool = [c for c in single_ranked if c[0] == "RSI_MOMENTUM"][:4]
    macd_pool = [c for c in single_ranked if c[0] == "MACD_MOMENTUM"][:4]
    adx_pool = [c for c in single_ranked if c[0] == "TREND_STRENGTH"][:4]
    deliv_vol_pool = [
        c for c in single_ranked
        if c[0] in {"INSTITUTIONAL_DELIVERY_PCT", "INSTITUTIONAL_DELIVERY_QTY", "INSTITUTIONAL_DELIVERY_SYNERGY", "VOLUME_ACCUMULATION", "VOLUME_DEMAND"}
    ][:6]

    four_factor_min = max(8, int(round(min_sig * 0.70))) if min_sig >= 12 else min_sig
    for r_cond in rsi_pool:
        for m_cond in macd_pool:
            m12 = r_cond[2] & m_cond[2]
            if int(m12.sum()) < four_factor_min:
                continue
            for a_cond in adx_pool:
                m123 = m12 & a_cond[2]
                if int(m123.sum()) < four_factor_min:
                    continue
                for d_cond in deliv_vol_pool:
                    m1234 = m123 & d_cond[2]
                    if int(m1234.sum()) >= four_factor_min:
                        evaluate_mask(
                            m1234,
                            [r_cond[1], m_cond[1], a_cond[1], d_cond[1]],
                            four_factor_min,
                        )

    if not output:
        return pd.DataFrame(columns=ANALYSIS_OUTPUT_COLUMNS)

    out = pd.DataFrame(output)

    out["_rule_len"] = out["Setup_Rules"].str.len()
    out = out.sort_values(
        ["Overall_Score_(0-100)", "Win_Rate_%", "Avg_Profit_%", "Times_Occurred", "_rule_len"],
        ascending=[False, False, not is_stop_goal, False, True],
        na_position="last",
    )
    out = out.drop_duplicates(
        subset=["Times_Occurred", "Win_Rate_%", "Avg_Profit_%", "Stop_Hit_Rate_%"],
        keep="first",
    ).drop(columns=["_rule_len"])

    out = out[ANALYSIS_OUTPUT_COLUMNS].reset_index(drop=True)
    return out
