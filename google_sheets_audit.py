"""Google Sheets append/read layer for the scanner audit database.

This module contains NO scanner logic. It only persists audit snapshots and
reads the accumulated audit/performance data for later analysis.
"""
from __future__ import annotations

from datetime import datetime
from typing import Iterable
import uuid

import pandas as pd

SHEET_ID_DEFAULT = "1Mp1Cper3L7Hiv-JzzNXP_CtlUwJ7PVbHgFPYANlcGNc"
SIGNALS_TAB = "Audit_Signals"
RUNS_TAB = "Audit_Runs"
PERFORMANCE_TAB = "Daily_Performance"
ANALYSIS_TAB = "Analysis_Results"


def _service_account_client(secrets):
    try:
        import gspread
    except ImportError as exc:
        raise RuntimeError("gspread is not installed. Add gspread and google-auth to requirements.txt.") from exc

    if "gcp_service_account" not in secrets:
        raise RuntimeError("Google service-account credentials are missing from Streamlit Secrets.")

    creds = dict(secrets["gcp_service_account"])
    return gspread.service_account_from_dict(creds)


def _clean(value):
    if value is None:
        return ""
    try:
        if pd.isna(value):
            return ""
    except Exception:
        pass
    if isinstance(value, bool):
        return "TRUE" if value else "FALSE"
    return value


def _ensure_sheet(spreadsheet, title, headers):
    try:
        ws = spreadsheet.worksheet(title)
    except Exception:
        ws = spreadsheet.add_worksheet(title=title, rows=1000, cols=max(20, len(headers) + 5))
    existing = ws.row_values(1)
    if not existing:
        ws.append_row(headers, value_input_option="USER_ENTERED")
    return ws


def open_audit_book(secrets):
    client = _service_account_client(secrets)
    sheet_id = str(secrets.get("AUDIT_SHEET_ID", SHEET_ID_DEFAULT))
    book = client.open_by_key(sheet_id)
    return book


def ensure_audit_schema(secrets, signal_headers: Iterable[str], performance_headers: Iterable[str]):
    book = open_audit_book(secrets)
    _ensure_sheet(book, SIGNALS_TAB, list(signal_headers))
    _ensure_sheet(book, RUNS_TAB, [
        "Audit_Run_ID", "Scan_Timestamp_IST", "Scan_Date", "Rows_Expected", "Rows_Appended",
        "Scanner_Period", "Max_Distance_Pct", "App_Status", "Write_Timestamp_IST"
    ])
    _ensure_sheet(book, PERFORMANCE_TAB, list(performance_headers))
    _ensure_sheet(book, ANALYSIS_TAB, [
        "Analysis_Timestamp_IST", "Outcome", "Combination", "Signals", "Success_Rate_Pct",
        "Avg_Return_Pct", "Median_Return_Pct", "Avg_Best_Gain_Pct", "Avg_Max_Drawdown_Pct",
        "Train_Test_Split", "Notes"
    ])
    return book


def _batch_exists(runs_ws, run_id: str) -> bool:
    values = runs_ws.col_values(1)
    return run_id in set(values)


def append_audit_batch(secrets, rows: pd.DataFrame, run_id: str, scan_timestamp_ist: str,
                       scanner_period: str = "2y", max_distance_pct: float = 10.0) -> dict:
    """Append one audit scan batch; never overwrite existing rows.

    The run log is created first as PENDING. This makes retries safe: if the
    signal rows were already appended but the final status update failed, the
    same run ID is recognized and the rows are not appended twice.
    """
    if rows is None or rows.empty:
        return {"saved": False, "rows": 0, "run_id": run_id, "reason": "empty_result"}

    from audit_logger import AUDIT_COLUMNS

    book = ensure_audit_schema(secrets, AUDIT_COLUMNS, [
        "Signal_ID", "Scan_Date", "Tracking_Day", "Tracking_Date", "Open", "High", "Low", "Close",
        "Breakout_Trigger", "Target_1", "Target_2", "Target_3", "Stop", "Breakout_Hit", "T1_Hit",
        "T2_Hit", "T3_Hit", "Stop_Hit", "Best_Gain_Pct", "Max_Drawdown_Pct", "Status", "Data_Quality"
    ])
    signals_ws = book.worksheet(SIGNALS_TAB)
    runs_ws = book.worksheet(RUNS_TAB)

    existing_values = runs_ws.col_values(1)
    if run_id in set(existing_values):
        return {"saved": True, "duplicate": True, "rows": 0, "run_id": run_id, "reason": "batch_already_exists"}

    # Create an auditable run record first.
    runs_ws.append_row([
        run_id,
        scan_timestamp_ist,
        str(scan_timestamp_ist).split(" ")[0],
        len(rows),
        0,
        scanner_period,
        max_distance_pct,
        "PENDING",
        "",
    ], value_input_option="USER_ENTERED", insert_data_option="INSERT_ROWS")
    run_row_number = len(runs_ws.get_all_values())

    out = rows.copy().reindex(columns=AUDIT_COLUMNS, fill_value="")
    matrix = [[_clean(v) for v in row] for row in out.itertuples(index=False, name=None)]
    signals_ws.append_rows(matrix, value_input_option="USER_ENTERED", insert_data_option="INSERT_ROWS")

    runs_ws.update_cell(run_row_number, 5, len(matrix))
    runs_ws.update_cell(run_row_number, 8, "APPENDED")
    runs_ws.update_cell(run_row_number, 9, datetime.now().astimezone().strftime("%Y-%m-%d %H:%M:%S %Z"))

    return {"saved": True, "duplicate": False, "rows": len(matrix), "run_id": run_id, "reason": "appended"}


def new_run_id() -> str:
    return datetime.now().strftime("AUDIT_%Y%m%d_%H%M%S") + "_" + uuid.uuid4().hex[:6]


def read_audit_signals(secrets) -> pd.DataFrame:
    book = open_audit_book(secrets)
    ws = book.worksheet(SIGNALS_TAB)
    records = ws.get_all_records()
    return pd.DataFrame(records)


def read_daily_performance(secrets) -> pd.DataFrame:
    book = open_audit_book(secrets)
    ws = book.worksheet(PERFORMANCE_TAB)
    records = ws.get_all_records()
    return pd.DataFrame(records)


def append_analysis_rows(secrets, analysis_df: pd.DataFrame) -> int:
    if analysis_df is None or analysis_df.empty:
        return 0
    book = open_audit_book(secrets)
    ws = book.worksheet(ANALYSIS_TAB)
    values = [[_clean(v) for v in row] for row in analysis_df.itertuples(index=False, name=None)]
    ws.append_rows(values, value_input_option="USER_ENTERED", insert_data_option="INSERT_ROWS")
    return len(values)
