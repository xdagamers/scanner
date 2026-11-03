import pandas as pd
import datetime
from pathlib import Path
import urllib.request
import io

def download_nse_delivery_report(report_date=None):
    """
    Downloads the official NSE Security-wise Price-Volume-Delivery archive 
    (Full Bhavcopy) for the given date.
    """
    if not report_date:
        report_date = datetime.date.today()
    
    date_str = report_date.strftime("%d%m%Y")
    filename = f"sec_bhavdata_full_{date_str}.csv"
    
    # If already downloaded today, use local cache to avoid redundant network calls
    if Path(filename).exists():
        return filename
        
    # Official NSE public archive URL format
    url = f"https://nsearchives.nseindia.com/products/content/sec_bhavdata_full_{date_str}.csv"
    
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept": "text/csv,text/plain,*/*",
        "Referer": "https://www.nseindia.com/"
    }
    
    try:
        req = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(req, timeout=30) as response:
            content = response.read()
            with open(filename, "wb") as f:
                f.write(content)
        return filename
    except Exception as e:
        print(f"Failed to download EOD delivery report for {date_str}: {e}")
        return None

def enrich_shortlist_with_delivery(shortlisted_df, report_date=None):
    """
    Takes your final scanner shortlisted DataFrame, fetches the daily EOD file,
    and extracts delivery % and deliverable quantities exclusively for those symbols.
    """
    if shortlisted_df is None or shortlisted_df.empty:
        return shortlisted_df
        
    filename = download_nse_delivery_report(report_date)
    if not filename or not Path(filename).exists():
        # Graceful degradation: if file isn't available yet, return DataFrame with NaN delivery
        shortlisted_df["delivery_pct"] = None
        shortlisted_df["deliverable_qty"] = None
        return shortlisted_df
        
    try:
        # Read the CSV file
        df = pd.read_csv(filename)
        # Clean column names (strip whitespace and lowercase)
        df.columns = [str(c).strip().lower() for c in df.columns]
        
        # Standardize column mappings across NSE format updates
        sym_col = next((c for c in df.columns if 'symbol' in c), 'symbol')
        series_col = next((c for c in df.columns if 'series' in c), 'series')
        dly_per_col = next((c for c in df.columns if 'deliv_per' in c or 'delivery_per' in c), None)
        dly_qty_col = next((c for c in df.columns if 'deliverable_qty' in c or 'deliv_qty' in c), None)
        
        delivery_pcts = []
        delivery_qtys = []
        
        for _, row in shortlisted_df.iterrows():
            sym = str(row.get("symbol", "")).strip().upper()
            
            # Match symbol in EQ series
            match = df[(df[sym_col].str.strip().str.upper() == sym) & (df[series_col].str.strip().str.upper() == 'EQ')]
            
            if not match.empty:
                # Extract pre-calculated delivery percentage if available, otherwise compute it
                if dly_per_col and pd.notna(match.iloc[0].get(dly_per_col)):
                    dly_pct = float(match.iloc[0][dly_per_col])
                elif dly_qty_col:
                    dly_q = float(match.iloc[0].get(dly_qty_col, 0) or 0)
                    trd_q = float(match.iloc[0].get('traded_qty', 1) or 1)
                    dly_pct = (dly_q / trd_q) * 100
                else:
                    dly_pct = None
                    
                dly_q_val = float(match.iloc[0].get(dly_qty_col, 0)) if dly_qty_col else None
                
                delivery_pcts.append(round(dly_pct, 2) if dly_pct is not None else None)
                delivery_qtys.append(dly_q_val)
            else:
                delivery_pcts.append(None)
                delivery_qtys.append(None)
                
        shortlisted_df["delivery_pct"] = delivery_pcts
        shortlisted_df["deliverable_qty"] = delivery_qtys
        
    except Exception as e:
        print(f"Error parsing EOD delivery file: {e}")
        shortlisted_df["delivery_pct"] = None
        shortlisted_df["deliverable_qty"] = None
        
    return shortlisted_df