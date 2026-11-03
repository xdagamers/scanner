import io
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

import numpy as np
import pandas as pd
import requests

IST = ZoneInfo("Asia/Kolkata")

NSE_BHAVDATA_URL = "https://nsearchives.nseindia.com/products/content/sec_bhavdata_full_{ddmmyyyy}.csv"
NSE_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
    "Accept": "text/csv,text/plain,*/*",
    "Accept-Language": "en-US,en;q=0.9",
    "Referer": "https://www.nseindia.com/",
}

_DELIVERY_CACHE = {
    "date_str": None,
    "df": None,
}


def _fetch_bhavdata_for_date(target_date):
    """Downloads and parses NSE security-wise deliverable positions CSV for a specific date."""
    ddmmyyyy = target_date.strftime("%d%m%Y")
    url = NSE_BHAVDATA_URL.format(ddmmyyyy=ddmmyyyy)
    try:
        response = requests.get(url, headers=NSE_HEADERS, timeout=12)
        if response.status_code != 200 or not response.text.strip():
            return None

        raw_df = pd.read_csv(io.StringIO(response.text))
        raw_df.columns = [str(c).strip().upper() for c in raw_df.columns]

        required = {"SYMBOL", "SERIES", "DELIV_QTY", "DELIV_PER"}
        if not required.issubset(set(raw_df.columns)):
            return None

        raw_df["SYMBOL"] = raw_df["SYMBOL"].astype(str).str.strip().str.upper()
        raw_df["SERIES"] = raw_df["SERIES"].astype(str).str.strip().str.upper()

        # Keep primary equity series (EQ and BE)
        eq_df = raw_df[raw_df["SERIES"].isin(["EQ", "BE"])].copy()
        if eq_df.empty:
            return None

        eq_df["DELIV_PER"] = pd.to_numeric(eq_df["DELIV_PER"], errors="coerce")
        eq_df["DELIV_QTY"] = pd.to_numeric(eq_df["DELIV_QTY"], errors="coerce")

        eq_df = eq_df.sort_values("SERIES").drop_duplicates(subset=["SYMBOL"], keep="first")
        eq_df["delivery_date"] = target_date.strftime("%Y-%m-%d")

        return eq_df[["SYMBOL", "DELIV_PER", "DELIV_QTY", "delivery_date"]].rename(
            columns={
                "SYMBOL": "symbol",
                "DELIV_PER": "delivery_pct",
                "DELIV_QTY": "deliverable_qty",
            }
        )
    except Exception:
        return None


def fetch_latest_delivery_Map(report_date=None, max_lookback_days=7):
    """Finds the most recent completed NSE EOD delivery report within the lookback window."""
    now_ist = datetime.now(IST)
    if report_date is None:
        # Before 18:30 IST, today's full Bhavcopy may not be published yet; start from today and step back
        start_date = now_ist.date()
    elif isinstance(report_date, str):
        start_date = datetime.strptime(report_date[:10], "%Y-%m-%d").date()
    else:
        start_date = report_date

    cache_key = start_date.strftime("%Y-%m-%d")
    if _DELIVERY_CACHE["date_str"] == cache_key and _DELIVERY_CACHE["df"] is not None:
        return _DELIVERY_CACHE["df"]

    for offset in range(max_lookback_days + 1):
        candidate_date = start_date - timedelta(days=offset)
        if candidate_date.weekday() >= 5:
            continue
        df_delivery = _fetch_bhavdata_for_date(candidate_date)
        if df_delivery is not None and not df_delivery.empty:
            _DELIVERY_CACHE["date_str"] = cache_key
            _DELIVERY_CACHE["df"] = df_delivery
            return df_delivery

    return pd.DataFrame(columns=["symbol", "delivery_pct", "deliverable_qty", "delivery_date"])


def enrich_shortlist_with_delivery(shortlist_df, report_date=None):
    """Merges EOD delivery_pct and deliverable_qty into the scanner shortlist DataFrame."""
    if shortlist_df is None or shortlist_df.empty:
        return shortlist_df

    out = shortlist_df.copy()
    for col in ["delivery_pct", "deliverable_qty", "delivery_date"]:
        if col in out.columns:
            out = out.drop(columns=[col])

    delivery_df = fetch_latest_delivery_Map(report_date=report_date)
    if delivery_df.empty:
        out["delivery_pct"] = np.nan
        out["deliverable_qty"] = np.nan
        out["delivery_date"] = None
        return out

    out["_clean_sym"] = out["symbol"].astype(str).str.strip().str.upper().str.replace(".NS", "", regex=False)
    merged = out.merge(
        delivery_df,
        left_on="_clean_sym",
        right_on="symbol",
        how="left",
        suffixes=("", "_dly"),
    )

    if "symbol_dly" in merged.columns:
        merged = merged.drop(columns=["symbol_dly"])
    merged = merged.drop(columns=["_clean_sym"])

    merged["delivery_pct"] = merged["delivery_pct"].round(1)
    return merged