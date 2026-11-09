import time
import pandas as pd
from datetime import datetime
from zoneinfo import ZoneInfo
import gspread
from google.oauth2.service_account import Credentials
import textwrap

def append_audit_batch(secrets, pending_rows, run_id, scan_timestamp_ist, scanner_period, max_distance_pct):
    return {"saved": True, "rows": len(pending_rows), "run_id": run_id}

def new_run_id():
    return int(time.time())

def read_audit_signals(secrets):
    return pd.DataFrame()

def read_performance_keys(secrets):
    return pd.DataFrame()

def read_final_performance(secrets):
    return pd.DataFrame()

def append_performance_rows(secrets, new_performance, batch_size=400, progress_callback=None):
    return {"batches": 0, "rows": 0, "updated": 0, "skipped_duplicates": 0}

def append_analysis_rows(secrets, stored_analysis):
    return 0

def append_watchlist_row(secrets, payload):
    return True

def read_watchlist(secrets):
    return pd.DataFrame()

def get_google_creds(secrets):
    pk = secrets.get("GCP_PRIVATE_KEY", "")
    
    # --- THE PEM FIXER ---
    # Extracts the mangled key, removes all formatting, and perfectly reconstructs 
    # the 64-character chunking that cryptography.io strictly requires.
    if "-----BEGIN PRIVATE KEY-----" in pk:
        core = pk.split("-----BEGIN PRIVATE KEY-----")[-1].split("-----END PRIVATE KEY-----")[0]
        core = core.replace('\\n', '').replace('\n', '').replace(' ', '')
        chunked = textwrap.fill(core, 64)
        pk = f"-----BEGIN PRIVATE KEY-----\n{chunked}\n-----END PRIVATE KEY-----\n"
        
    return {
        "type": "service_account",
        "project_id": secrets.get("GCP_PROJECT_ID"),
        "private_key_id": secrets.get("GCP_PRIVATE_KEY_ID"),
        "private_key": pk,
        "client_email": secrets.get("GCP_CLIENT_EMAIL"),
        "client_id": secrets.get("GCP_CLIENT_ID"),
        "auth_uri": "https://accounts.google.com/o/oauth2/auth",
        "token_uri": "https://oauth2.googleapis.com/token",
        "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs",
        "client_x509_cert_url": secrets.get("GCP_CLIENT_CERT_URL")
    }

def log_paper_trade(secrets, trade_data):
    creds_dict = get_google_creds(secrets)
    credentials = Credentials.from_service_account_info(
        creds_dict, scopes=["https://www.googleapis.com/auth/spreadsheets"]
    )
    client = gspread.authorize(credentials)
    sheet_id = secrets.get("GOOGLE_SHEET_ID")
    doc = client.open_by_key(sheet_id)
    
    try:
        sheet = doc.worksheet("Paper_Trades")
    except gspread.exceptions.WorksheetNotFound:
        sheet = doc.add_worksheet(title="Paper_Trades", rows="1000", cols="15")
        headers = ["Trade_ID", "Symbol", "Entry_Date", "Entry_Price", "Quantity", 
                   "Invested_Capital", "Stop_Loss", "Target_1", "Target_2", "Status", "PnL"]
        sheet.insert_row(headers, index=1)
        
    row = [
        trade_data.get("Trade_ID", ""),
        trade_data.get("Symbol", ""),
        trade_data.get("Entry_Date", ""),
        trade_data.get("Entry_Price", ""),
        trade_data.get("Quantity", ""),
        trade_data.get("Invested_Capital", ""),
        trade_data.get("Stop_Loss", ""),
        trade_data.get("Target_1", ""),
        trade_data.get("Target_2", ""),
        trade_data.get("Status", "OPEN"),
        trade_data.get("PnL", "0.0")
    ]
    
    sheet.append_row(row)
    return True

def get_paper_trades(secrets):
    try:
        creds_dict = get_google_creds(secrets)
        credentials = Credentials.from_service_account_info(
            creds_dict, scopes=["https://www.googleapis.com/auth/spreadsheets"]
        )
        client = gspread.authorize(credentials)
        sheet_id = secrets.get("GOOGLE_SHEET_ID")
        doc = client.open_by_key(sheet_id)
        
        sheet = doc.worksheet("Paper_Trades")
        data = sheet.get_all_records()
        return pd.DataFrame(data)
    except Exception as e:
        print(f"Fetch error: {e}")
        return pd.DataFrame()
        
def close_paper_trade(secrets, trade_id, exit_price, pnl, target_hit=None):
    creds_dict = get_google_creds(secrets)
    credentials = Credentials.from_service_account_info(
        creds_dict, scopes=["https://www.googleapis.com/auth/spreadsheets"]
    )
    client = gspread.authorize(credentials)
    sheet_id = secrets.get("GOOGLE_SHEET_ID")
    doc = client.open_by_key(sheet_id)
    
    sheet = doc.worksheet("Paper_Trades")
    records = sheet.get_all_records()
    for i, row in enumerate(records):
        if str(row.get("Trade_ID")) == str(trade_id):
            row_idx = i + 2 
            sheet.update_cell(row_idx, 10, f"CLOSED: {target_hit}" if target_hit else "CLOSED") 
            sheet.update_cell(row_idx, 11, pnl) 
            
            headers = sheet.row_values(1)
            if "Exit_Price" not in headers:
                sheet.update_cell(1, len(headers) + 1, "Exit_Price")
                sheet.update_cell(1, len(headers) + 2, "Exit_Date")
                headers = sheet.row_values(1)
                
            exit_price_col = headers.index("Exit_Price") + 1
            exit_date_col = headers.index("Exit_Date") + 1
            
            sheet.update_cell(row_idx, exit_price_col, exit_price)
            sheet.update_cell(row_idx, exit_date_col, datetime.now(ZoneInfo("Asia/Kolkata")).strftime("%Y-%m-%d %H:%M:%S"))
            return True
    return False
