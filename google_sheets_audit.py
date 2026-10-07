"""Free Google Sheets bridge using a Google Apps Script Web App.

No Google Cloud service-account credentials are required. The Streamlit app
sends audit batches to the Apps Script endpoint, which appends them to the
Google Sheet. This module contains no scanner logic.
"""
from __future__ import annotations

from datetime import datetime
import uuid
from typing import Any

import pandas as pd
import requests

SHEET_ID_DEFAULT = "1Mp1Cper3L7Hiv-JzzNXP_CtlUwJ7PVbHgFPYANlcGNc"
SIGNALS_TAB = "Audit_Signals"
RUNS_TAB = "Audit_Runs"
PERFORMANCE_TAB = "Daily_Performance"
ANALYSIS_TAB = "Analysis_Results"


def _config(secrets):
    url = str(secrets.get("AUDIT_APPS_SCRIPT_URL", "")).strip()
    token = str(secrets.get("AUDIT_TOKEN", "")).strip()
    sheet_id = str(secrets.get("AUDIT_SHEET_ID", SHEET_ID_DEFAULT)).strip()
    if not url:
        raise RuntimeError("AUDIT_APPS_SCRIPT_URL is missing from Streamlit Secrets.")
    if not token:
        raise RuntimeError("AUDIT_TOKEN is missing from Streamlit Secrets.")
    return url, token, sheet_id


def _post(secrets, payload: dict[str, Any]) -> dict:
    url, token, _ = _config(secrets)
    body = dict(payload)
    body["token"] = token
    try:
        response = requests.post(url, json=body, timeout=60)
    except requests.RequestException as exc:
        raise RuntimeError(f"Could not reach the Google Apps Script endpoint: {exc}") from exc

    if response.status_code != 200:
        raise RuntimeError(
            f"Google Apps Script returned HTTP {response.status_code}: {response.text[:500]}"
        )
    try:
        result = response.json()
    except ValueError as exc:
        raise RuntimeError(
            f"Google Apps Script returned a non-JSON response: {response.text[:500]}"
        ) from exc
    if not result.get("ok", False):
        raise RuntimeError(str(result.get("error", "Unknown Google Apps Script error.")))
    return result


def _get(secrets, action: str) -> dict:
    url, token, _ = _config(secrets)
    try:
        response = requests.get(
            url,
            params={"action": action, "token": token},
            timeout=30,
        )
    except requests.RequestException as exc:
        raise RuntimeError(f"Could not reach the Google Apps Script endpoint: {exc}") from exc
    if response.status_code != 200:
        raise RuntimeError(
            f"Google Apps Script returned HTTP {response.status_code}: {response.text[:500]}"
        )
    try:
        result = response.json()
    except ValueError as exc:
        raise RuntimeError(
            f"Google Apps Script returned a non-JSON response: {response.text[:500]}"
        ) from exc
    if not result.get("ok", False):
        raise RuntimeError(str(result.get("error", "Unknown Google Apps Script error.")))
    return result


def new_run_id() -> str:
    return datetime.now().strftime("AUDIT_%Y%m%d_%H%M%S") + "_" + uuid.uuid4().hex[:6]


def append_audit_batch(
    secrets,
    rows: pd.DataFrame,
    run_id: str,
    scan_timestamp_ist: str,
    scanner_period: str = "2y",
    max_distance_pct: float = 10.0,
) -> dict:
    """Append one complete audit batch; existing batches are never overwritten."""
    if rows is None or rows.empty:
        return {"saved": False, "rows": 0, "run_id": run_id, "reason": "empty_result"}

    try:
        records = rows.where(pd.notna(rows), "").to_dict(orient="records")
    except Exception as exc:
        raise RuntimeError(f"Could not prepare audit rows for Google Sheets: {exc}") from exc

    return _post(
        secrets,
        {
            "action": "append_audit_batch",
            "run_id": run_id,
            "scan_timestamp_ist": scan_timestamp_ist,
            "scanner_period": scanner_period,
            "max_distance_pct": max_distance_pct,
            "rows": records,
        },
    )


def read_audit_signals(secrets) -> pd.DataFrame:
    result = _get(secrets, "read_signals")
    return pd.DataFrame(result.get("data", []))


def read_daily_performance(secrets) -> pd.DataFrame:
    result = _get(secrets, "read_performance")
    return pd.DataFrame(result.get("data", []))


def append_performance_rows(secrets, rows: pd.DataFrame) -> dict:
    if rows is None or rows.empty:
        return {"saved": False, "rows": 0, "reason": "empty_result"}
    records = rows.where(pd.notna(rows), "").to_dict(orient="records")
    return _post(secrets, {"action": "append_performance", "rows": records})


def append_analysis_rows(secrets, analysis_df: pd.DataFrame) -> int:
    if analysis_df is None or analysis_df.empty:
        return 0
    records = analysis_df.where(pd.notna(analysis_df), "").to_dict(orient="records")
    result = _post(secrets, {"action": "append_analysis", "rows": records})
    return int(result.get("rows", 0))


def test_connection(secrets) -> dict:
    return _get(secrets, "ping")
