"""Free Google Sheets bridge using a Google Apps Script Web App."""
from __future__ import annotations
from datetime import datetime
import time
import uuid
from typing import Any
import pandas as pd
import requests

SHEET_ID_DEFAULT = "1Mp1Cper3L7Hiv-JzzNXP_CtlUwJ7PVbHgFPYANlcGNc"
SIGNALS_TAB = "Audit_Signals"
RUNS_TAB = "Audit_Runs"
PERFORMANCE_TAB = "Daily_Performance"
ANALYSIS_TAB = "Analysis_Results"

EXPECTED_ANALYSIS_HEADERS = [
    "Analysis_Timestamp_IST", "Outcome_Goal", "Setup_Rules", "Times_Occurred",
    "Win_Rate_%", "Avg_Profit_%", "Stop_Hit_Rate_%", "Overall_Score_(0-100)"
]

def _config(secrets):
    url = str(secrets.get("AUDIT_APPS_SCRIPT_URL", "")).strip()
    token = str(secrets.get("AUDIT_TOKEN", "")).strip()
    sheet_id = str(secrets.get("AUDIT_SHEET_ID", SHEET_ID_DEFAULT)).strip()
    if not url: raise RuntimeError("AUDIT_APPS_SCRIPT_URL missing.")
    if not token: raise RuntimeError("AUDIT_TOKEN missing.")
    return url, token, sheet_id

def _post(secrets, payload: dict[str, Any]) -> dict:
    url, token, _ = _config(secrets)
    body = dict(payload)
    body["token"] = token
    try:
        response = requests.post(url, json=body, timeout=180)
    except requests.RequestException as exc:
        raise RuntimeError(f"Could not reach Apps Script: {exc}") from exc
    if response.status_code != 200:
        raise RuntimeError(f"Apps Script HTTP {response.status_code}")
    result = response.json()
    if not result.get("ok", False):
        raise RuntimeError(str(result.get("error", "Unknown error.")))
    return result

def _get(secrets, action: str) -> dict:
    url, token, _ = _config(secrets)
    try:
        response = requests.get(url, params={"action": action, "token": token}, timeout=180)
    except requests.RequestException as exc:
        raise RuntimeError(f"Could not reach Apps Script: {exc}") from exc
    if response.status_code != 200:
        raise RuntimeError(f"Apps Script HTTP {response.status_code}")
    result = response.json()
    if not result.get("ok", False):
        raise RuntimeError(str(result.get("error", "Unknown error.")))
    return result

def new_run_id() -> str:
    return datetime.now().strftime("AUDIT_%Y%m%d_%H%M%S") + "_" + uuid.uuid4().hex[:6]

def append_audit_batch(
    secrets, rows: pd.DataFrame, run_id: str, scan_timestamp_ist: str,
    scanner_period: str = "2y", max_distance_pct: float = 10.0,
) -> dict:
    if rows is None or rows.empty:
        return {"saved": False, "rows": 0, "run_id": run_id, "reason": "empty_result"}
    try:
        clean_df = rows.copy()
        if "Symbol" in clean_df.columns:
            valid_sym = clean_df["Symbol"].notna() & clean_df["Symbol"].astype(str).str.strip().ne("")
            clean_df = clean_df[valid_sym].copy()
        if clean_df.empty: return {"saved": False, "rows": 0, "run_id": run_id, "reason": "empty_after_filter"}
        
        # FIX: Directly convert to dict without aggressive 'where' dropping which wiped the new floats/bools
        clean_df = clean_df.fillna("")
        records = clean_df.to_dict(orient="records")
    except Exception as exc:
        raise RuntimeError(f"Could not prepare rows: {exc}") from exc

    return _post(secrets, {
        "action": "append_audit_batch", "run_id": run_id, "scan_timestamp_ist": scan_timestamp_ist,
        "scanner_period": scanner_period, "max_distance_pct": max_distance_pct, "rows": records,
    })

def read_audit_signals(secrets) -> pd.DataFrame:
    return pd.DataFrame(_get(secrets, "read_signals").get("data", []))

def read_daily_performance(secrets) -> pd.DataFrame:
    return pd.DataFrame(_get(secrets, "read_performance").get("data", []))

def read_final_performance(secrets) -> pd.DataFrame:
    return pd.DataFrame(_get(secrets, "read_final_performance").get("data", []))

def append_performance_rows(secrets, rows: pd.DataFrame, batch_size: int = 400, progress_callback=None) -> dict:
    if rows is None or rows.empty: return {"saved": False, "rows": 0, "expected": 0, "reason": "empty_result", "batches": 0}
    records = rows.fillna("").to_dict(orient="records")
    written = updated = skipped = 0
    results = []
    size = min(400, max(1, int(batch_size)))
    for batch_index, start in enumerate(range(0, len(records), size), start=1):
        batch = records[start:start + size]
        if progress_callback: progress_callback(start, len(records), f"Writing batch {batch_index}...")
        result = _post(secrets, {"action": "append_performance", "rows": batch})
        written += int(result.get("rows", 0))
        updated += int(result.get("updated", 0))
        skipped += int(result.get("skipped_duplicates", 0))
        results.append(result)
        time.sleep(1.5)
    return {"saved": written > 0 or updated > 0, "rows": written, "updated": updated, "expected": len(records), "skipped_duplicates": skipped, "batches": len(results), "reason": "appended_or_repaired"}

def read_performance_keys(secrets) -> pd.DataFrame:
    return pd.DataFrame(_get(secrets, "read_performance_keys").get("data", []), columns=["Signal_ID", "Tracking_Day", "Data_Quality", "Scan_Date"])

def read_watchlist(secrets) -> pd.DataFrame:
    return pd.DataFrame(_get(secrets, "read_watchlist").get("data", []))

def append_analysis_rows(secrets, analysis_df: pd.DataFrame) -> int:
    if analysis_df is None or analysis_df.empty: return 0
    return int(_post(secrets, {"action": "append_analysis", "rows": analysis_df.fillna("").to_dict(orient="records")}).get("rows", 0))

def test_connection(secrets) -> dict:
    return _get(secrets, "ping")

def append_watchlist_row(secrets, row_dict: dict) -> dict:
    if not row_dict: return {"saved": False, "reason": "empty"}
    return _post(secrets, {"action": "append_watchlist", "row": row_dict})

def delete_watchlist_row(secrets, symbol: str) -> dict:
    clean_sym = str(symbol).strip().upper()
    if not clean_sym: return {"ok": False, "reason": "empty_symbol"}
    return _post(secrets, {"action": "delete_watchlist", "symbol": clean_sym, "Symbol": clean_sym, "payload": {"Symbol": clean_sym}})

def log_paper_trade(secrets, trade_data):
    return _post(secrets, {"action": "log_paper_trade", "row": trade_data})

def get_paper_trades(secrets):
    try: return pd.DataFrame(_get(secrets, "get_paper_trades").get("data", []))
    except Exception as e: return pd.DataFrame()

def close_paper_trade(secrets, trade_id, exit_price, pnl, target_hit=None):
    from zoneinfo import ZoneInfo
    return _post(secrets, {"action": "close_paper_trade", "trade_id": str(trade_id), "exit_price": float(exit_price), "pnl": float(pnl), "target_hit": str(target_hit) if target_hit else "", "exit_date": datetime.now(ZoneInfo("Asia/Kolkata")).strftime("%Y-%m-%d %H:%M:%S")})
