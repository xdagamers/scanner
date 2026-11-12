"""Persistent audit logging for the NIFTY breakout scanner."""
from __future__ import annotations
from datetime import datetime
from pathlib import Path
import uuid
import numpy as np
import pandas as pd

AUDIT_DIR = Path(__file__).resolve().parent / "audit_data"
SIGNAL_LOG = AUDIT_DIR / "scanner_audit_signals.csv"

# Updated to match your exact Google Sheet header order
AUDIT_COLUMNS = [
    "Signal_ID", "Audit_Run_ID", "Scan_Timestamp_IST", "Scan_Date",
    "Scanner_Period", "Max_Distance_Pct", "Universe_Result_Count", "Result_Position",
    "Scanner_Rank", "Symbol", "Company", "Cap_Category",
    "Price", "Breakout_Level", "Breakout_Trigger", "Target_1", "Target_2", "Target_3", "Stop",
    "Distance_Pct", "Rank_Score", "Score", "Rating", "Scanner_Status",
    "RVOL", "RSI", "MACD", "ADX", "ATR_Pct", "ATR_Ratio",
    "EMA_Structure", "Candlestick", "Resistance_Touches", "Resistance_Recency",
    "Relative_Strength_60D_Pct", "NIFTY_Relative_Strength_Pct", "Sector_Relative_Strength_Pct",
    "Market_Regime", "False_Breakout", "False_Breakout_Age", "Risk_Reward",
    "Component_Proximity", "Component_Resistance", "Component_Volume", "Component_Trend",
    "Component_Momentum", "Component_ADX", "Component_Squeeze", "Component_Relative_Strength",
    "Component_Candle", "Component_Market_Regime",
    "Weight_Proximity", "Weight_Resistance", "Weight_Volume", "Weight_Trend",
    "Weight_Momentum", "Weight_ADX", "Weight_Squeeze", "Weight_Relative_Strength",
    "Weight_Candle", "Weight_Market_Regime", "Explanation",
    "Delivery_Pct", "Deliverable_Qty",
    "UD_Vol_Ratio_20D", "Candle_CLV", "Pct_Below_52W_High", "Distribution_Trap", "Overhead_Wall_Trap", "Overextended_Trap"
]

def _num(row, key, default=np.nan):
    value = row.get(key, default)
    try:
        value = float(value)
        return value if np.isfinite(value) else default
    except Exception:
        return default

def _clean_opt(val):
    if val is None or pd.isna(val):
        return ""
    s = str(val).strip()
    return "" if s.lower() in {"nan", "none", "<na>"} else val

def build_scan_snapshot(
    result: pd.DataFrame,
    *,
    run_id: str,
    scan_timestamp_ist: str,
    scanner_period: str = "2y",
    max_distance_pct: float = 10.0,
) -> pd.DataFrame:
    if result is None or result.empty:
        return pd.DataFrame(columns=AUDIT_COLUMNS)

    # Filter out any ghost rows created by outer merges in delivery_loader.py
    clean_res = result.copy()
    if "symbol" in clean_res.columns:
        valid_sym = (
            clean_res["symbol"].notna()
            & clean_res["symbol"].astype(str).str.strip().ne("")
            & ~clean_res["symbol"].astype(str).str.strip().str.lower().isin(["nan", "none", "<na>"])
        )
        clean_res = clean_res[valid_sym].copy()
    if "price" in clean_res.columns:
        valid_price = pd.to_numeric(clean_res["price"], errors="coerce") > 0
        clean_res = clean_res[valid_price].copy()

    if clean_res.empty:
        return pd.DataFrame(columns=AUDIT_COLUMNS)

    scan_date = str(scan_timestamp_ist).split(" ")[0]
    rows = []
    for pos, (_, row) in enumerate(clean_res.reset_index(drop=True).iterrows(), start=1):
        symbol = str(row.get("symbol", "")).strip()
        if not symbol or symbol.lower() in {"nan", "none"}:
            continue
        t1 = _num(row, "target1")
        t2 = _num(row, "target2")
        t3 = _num(row, "target3")
        if not np.isfinite(t3) and np.isfinite(t1) and np.isfinite(t2):
            t3 = t2 + (t2 - t1)
        weights = row.get("weights") if isinstance(row.get("weights"), dict) else {}
        signal_id = f"{scan_date}_{symbol}_{run_id}"
        
        rows.append({
            "Signal_ID": signal_id,
            "Audit_Run_ID": run_id,
            "Scan_Timestamp_IST": scan_timestamp_ist,
            "Scan_Date": scan_date,
            "Scanner_Period": scanner_period,
            "Max_Distance_Pct": max_distance_pct,
            "Universe_Result_Count": len(clean_res),
            "Result_Position": pos,
            "Scanner_Rank": row.get("rank", pos),
            "Symbol": symbol,
            "Company": row.get("company_name", symbol),
            "Cap_Category": row.get("cap_category", ""),
            "Price": _num(row, "price"),
            "Breakout_Level": _num(row, "breakout_level"),
            "Breakout_Trigger": _num(row, "breakout_trigger"),
            "Target_1": t1,
            "Target_2": t2,
            "Target_3": t3,
            "Stop": _num(row, "stop_reference"),
            "Distance_Pct": _num(row, "distance_pct"),
            "Rank_Score": _num(row, "rank_score"),
            "Score": _num(row, "score"),
            "Rating": row.get("rating", ""),
            "Scanner_Status": row.get("status", ""),
            "RVOL": _num(row, "rvol"),
            "RSI": _num(row, "rsi"),
            "MACD": _num(row, "macd"),
            "ADX": _num(row, "adx"),
            "ATR_Pct": _num(row, "atr_pct"),
            "ATR_Ratio": _num(row, "atr_ratio"),
            "EMA_Structure": row.get("ema_structure", ""),
            "Candlestick": row.get("candlestick", ""),
            "Resistance_Touches": _num(row, "resistance_touches"),
            "Resistance_Recency": _num(row, "resistance_recency"),
            "Relative_Strength_60D_Pct": _num(row, "relative_strength"),
            "NIFTY_Relative_Strength_Pct": _num(row, "nifty_relative_strength"),
            "Sector_Relative_Strength_Pct": _num(row, "sector_relative_strength"),
            "Market_Regime": row.get("market_regime", ""),
            "False_Breakout": bool(row.get("false_breakout", False)),
            "False_Breakout_Age": _num(row, "false_breakout_age"),
            "Risk_Reward": _num(row, "risk_reward"),
            "Component_Proximity": _num(row, "component_proximity"),
            "Component_Resistance": _num(row, "component_resistance"),
            "Component_Volume": _num(row, "component_volume"),
            "Component_Trend": _num(row, "component_trend"),
            "Component_Momentum": _num(row, "component_momentum"),
            "Component_ADX": _num(row, "component_adx"),
            "Component_Squeeze": _num(row, "component_squeeze"),
            "Component_Relative_Strength": _num(row, "component_relative_strength"),
            "Component_Candle": _num(row, "component_candle"),
            "Component_Market_Regime": _num(row, "component_market_regime"),
            "Weight_Proximity": _num(weights, "proximity"),
            "Weight_Resistance": _num(weights, "resistance"),
            "Weight_Volume": _num(weights, "volume"),
            "Weight_Trend": _num(weights, "trend"),
            "Weight_Momentum": _num(weights, "momentum"),
            "Weight_ADX": _num(weights, "adx"),
            "Weight_Squeeze": _num(weights, "squeeze"),
            "Weight_Relative_Strength": _num(weights, "relative_strength"),
            "Weight_Candle": _num(weights, "candle"),
            "Weight_Market_Regime": _num(weights, "market_regime"),
            "Explanation": row.get("explanation", ""),
            "Delivery_Pct": _clean_opt(row.get("delivery_pct", "")),
            "Deliverable_Qty": _clean_opt(row.get("deliverable_qty", "")),
            "UD_Vol_Ratio_20D": _num(row, "ud_vol_ratio"),
            "Candle_CLV": _num(row, "clv"),
            "Pct_Below_52W_High": _num(row, "pct_below_52w"),
            "Distribution_Trap": bool(row.get("is_distribution_trap", False)),
            "Overhead_Wall_Trap": bool(row.get("overhead_wall_trap", False)),
            "Overextended_Trap": bool(row.get("is_overextended", False))
        })
    return pd.DataFrame(rows, columns=AUDIT_COLUMNS)

def append_scan_snapshot(
    result: pd.DataFrame,
    *,
    scan_timestamp_ist: str,
    scanner_period: str = "2y",
    max_distance_pct: float = 10.0,
    signal_log_path: str | Path = SIGNAL_LOG,
    run_id: str | None = None,
) -> dict:
    if result is None or result.empty:
        return {"saved": False, "rows": 0, "run_id": None, "path": str(signal_log_path), "reason": "empty_result"}

    path = Path(signal_log_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    run_id = run_id or (datetime.now().strftime("%Y%m%d_%H%M%S") + "_" + uuid.uuid4().hex[:6])
    out = build_scan_snapshot(
        result,
        run_id=run_id,
        scan_timestamp_ist=scan_timestamp_ist,
        scanner_period=scanner_period,
        max_distance_pct=max_distance_pct,
    )
    write_header = not path.exists() or path.stat().st_size == 0
    out.to_csv(path, mode="a", header=write_header, index=False, encoding="utf-8-sig")
    return {"saved": True, "rows": len(out), "run_id": run_id, "path": str(path), "reason": "appended"}

def read_signal_audit(signal_log_path: str | Path = SIGNAL_LOG) -> pd.DataFrame:
    path = Path(signal_log_path)
    if not path.exists() or path.stat().st_size == 0:
        return pd.DataFrame(columns=AUDIT_COLUMNS)
    return pd.read_csv(path)
