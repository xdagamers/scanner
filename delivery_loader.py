"""NSE EOD Delivery & Relative Delivery Baseline Loader (Phase 1 Upgraded).

Fetches the latest NSE security-wise deliverable positions (Bhavcopy) along with
a multi-session historical baseline (5-to-15 trading days prior) in parallel so the
scanner can evaluate both absolute Delivery % and Relative Delivery Expansion
without adding latency.
"""
from __future__ import annotations

import concurrent.futures
import io
from datetime import date, datetime, timedelta
from zoneinfo import ZoneInfo

import numpy as np
import pandas as pd
import requests

IST = ZoneInfo("Asia/Kolkata")

NSE_BHAVDATA_URL = "https://nsearchives.nseindia.com/products/content/sec_bhavdata_full_{ddmmyyyy}.csv"
NSE_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
    ),
    "Accept": "text/csv,text/plain,*/*",
    "Accept-Language": "en-US,en;q=0.9",
    "Referer": "https://www.nseindia.com/",
}

_DELIVERY_CACHE: dict = {
    "date_str": None,
    "timestamp": 0.0,
    "df": None,
    "dict_map": None,
}


def _fetch_bhavdata_for_date(target_date: date, timeout: float = 8.0) -> pd.DataFrame | None:
    """Downloads and parses NSE security-wise deliverable positions CSV for a specific date."""
    ddmmyyyy = target_date.strftime("%d%m%Y")
    url = NSE_BHAVDATA_URL.format(ddmmyyyy=ddmmyyyy)
    try:
        response = requests.get(url, headers=NSE_HEADERS, timeout=timeout)
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
        if "TTL_TRD_QNTY" in eq_df.columns:
            eq_df["TTL_TRD_QNTY"] = pd.to_numeric(eq_df["TTL_TRD_QNTY"], errors="coerce")
        else:
            eq_df["TTL_TRD_QNTY"] = np.nan

        eq_df = eq_df.sort_values("SERIES").drop_duplicates(subset=["SYMBOL"], keep="first")
        eq_df["delivery_date"] = target_date.strftime("%Y-%m-%d")

        return eq_df[["SYMBOL", "DELIV_PER", "DELIV_QTY", "TTL_TRD_QNTY", "delivery_date"]].rename(
            columns={
                "SYMBOL": "symbol",
                "DELIV_PER": "delivery_pct",
                "DELIV_QTY": "deliverable_qty",
                "TTL_TRD_QNTY": "traded_qty",
            }
        )
    except Exception:
        return None


def _candidate_weekdays(start_date: date, count: int) -> list[date]:
    """Returns up to `count` weekdays stepping backward from `start_date`."""
    out: list[date] = []
    cur = start_date
    steps = 0
    while len(out) < count and steps < count * 3:
        if cur.weekday() < 5:
            out.append(cur)
        cur -= timedelta(days=1)
        steps += 1
    return out


def fetch_latest_delivery_Map(report_date=None, max_lookback_days: int = 7) -> pd.DataFrame:
    """Finds the most recent completed NSE EOD delivery report and computes a multi-session baseline."""
    now_ist = datetime.now(IST)
    if report_date is None:
        # Before 18:15 IST, today's full Bhavcopy is rarely published; start from yesterday first if early
        start_date = now_ist.date() if now_ist.hour >= 18 else (now_ist.date() - timedelta(days=1))
    elif isinstance(report_date, str):
        start_date = datetime.strptime(report_date[:10], "%Y-%m-%d").date()
    else:
        start_date = report_date

    cache_key = start_date.strftime("%Y-%m-%d")
    now_ts = now_ist.timestamp()
    if (
        _DELIVERY_CACHE["date_str"] == cache_key
        and _DELIVERY_CACHE["df"] is not None
        and (now_ts - float(_DELIVERY_CACHE.get("timestamp", 0.0))) < 1800
    ):
        return _DELIVERY_CACHE["df"]

    df_latest = None
    latest_date_used = None
    for offset in range(max_lookback_days + 1):
        candidate_date = start_date - timedelta(days=offset)
        if candidate_date.weekday() >= 5:
            continue
        df_try = _fetch_bhavdata_for_date(candidate_date, timeout=7.0)
        if df_try is not None and not df_try.empty:
            df_latest = df_try
            latest_date_used = candidate_date
            break

    if df_latest is None or df_latest.empty or latest_date_used is None:
        empty_cols = [
            "symbol", "delivery_pct", "deliverable_qty", "delivery_date",
            "delivery_pct_base", "deliverable_qty_base", "deliv_expansion_ratio",
        ]
        return pd.DataFrame(columns=empty_cols)

    # Fetch up to 3 historical anchor sessions (~4, ~8, ~13 trading days back) in parallel
    # to establish a fast, low-latency 20-day proxy baseline without downloading 20 files.
    prior_weekdays = _candidate_weekdays(latest_date_used - timedelta(days=1), 16)
    anchor_indices = [idx for idx in (3, 7, 12) if idx < len(prior_weekdays)]
    anchor_dates = [prior_weekdays[idx] for idx in anchor_indices]

    baseline_frames: list[pd.DataFrame] = []
    if anchor_dates:
        with concurrent.futures.ThreadPoolExecutor(max_workers=len(anchor_dates)) as pool:
            futs = [pool.submit(_fetch_bhavdata_for_date, d, 4.5) for d in anchor_dates]
            for fut in concurrent.futures.as_completed(futs):
                try:
                    res = fut.result()
                    if res is not None and not res.empty:
                        baseline_frames.append(res[["symbol", "delivery_pct", "deliverable_qty"]])
                except Exception:
                    continue

    out = df_latest.copy()
    if baseline_frames:
        concat_base = pd.concat(baseline_frames, ignore_index=True)
        grouped = (
            concat_base.groupby("symbol", as_index=False)
            .agg(
                delivery_pct_base=("delivery_pct", "median"),
                deliverable_qty_base=("deliverable_qty", "median"),
            )
        )
        out = out.merge(grouped, on="symbol", how="left")
    else:
        out["delivery_pct_base"] = np.nan
        out["deliverable_qty_base"] = np.nan

    out["delivery_pct_base"] = out["delivery_pct_base"].fillna(out["delivery_pct"])
    out["deliverable_qty_base"] = out["deliverable_qty_base"].fillna(out["deliverable_qty"])

    valid_base_qty = out["deliverable_qty_base"].where(out["deliverable_qty_base"] > 0, np.nan)
    out["deliv_expansion_ratio"] = (out["deliverable_qty"] / valid_base_qty).round(2).fillna(1.0)
    out["delivery_pct"] = out["delivery_pct"].round(1)
    out["delivery_pct_base"] = out["delivery_pct_base"].round(1)

    dict_map = {}
    for row in out.to_dict(orient="records"):
        sym = str(row.get("symbol", "")).strip().upper()
        if sym:
            dict_map[sym] = row

    _DELIVERY_CACHE["date_str"] = cache_key
    _DELIVERY_CACHE["timestamp"] = now_ts
    _DELIVERY_CACHE["df"] = out
    _DELIVERY_CACHE["dict_map"] = dict_map
    return out


def get_delivery_lookup_dict(report_date=None) -> dict[str, dict]:
    """Returns an O(1) symbol -> delivery metrics dictionary for pre-score integration in scanner.py."""
    fetch_latest_delivery_Map(report_date=report_date)
    return _DELIVERY_CACHE.get("dict_map") or {}


def enrich_shortlist_with_delivery(shortlist_df: pd.DataFrame, report_date=None) -> pd.DataFrame:
    """Merges EOD delivery_pct, deliverable_qty, and baseline metrics into the scanner shortlist DataFrame."""
    if shortlist_df is None or shortlist_df.empty:
        return shortlist_df

    # Fast path: if scanner.py already enriched delivery_pct during pre-scoring, return cleanly
    if (
        "delivery_pct" in shortlist_df.columns
        and "deliverable_qty" in shortlist_df.columns
        and shortlist_df["delivery_pct"].notna().any()
    ):
        out_fast = shortlist_df.copy()
        out_fast["delivery_pct"] = pd.to_numeric(out_fast["delivery_pct"], errors="coerce").round(1)
        return out_fast

    out = shortlist_df.copy()
    drop_cols = [
        c for c in ["delivery_pct", "deliverable_qty", "delivery_date", "delivery_pct_base", "deliverable_qty_base", "deliv_expansion_ratio"]
        if c in out.columns
    ]
    if drop_cols:
        out = out.drop(columns=drop_cols)

    delivery_df = fetch_latest_delivery_Map(report_date=report_date)
    if delivery_df.empty:
        out["delivery_pct"] = np.nan
        out["deliverable_qty"] = np.nan
        out["delivery_date"] = None
        return out

    merge_cols = [
        c for c in ["symbol", "delivery_pct", "deliverable_qty", "delivery_date", "delivery_pct_base", "deliverable_qty_base", "deliv_expansion_ratio"]
        if c in delivery_df.columns
    ]
    out["_clean_sym"] = out["symbol"].astype(str).str.strip().str.upper().str.replace(".NS", "", regex=False)
    merged = out.merge(
        delivery_df[merge_cols],
        left_on="_clean_sym",
        right_on="symbol",
        how="left",
        suffixes=("", "_dly"),
    )

    if "symbol_dly" in merged.columns:
        merged = merged.drop(columns=["symbol_dly"])
    merged = merged.drop(columns=["_clean_sym"])

    merged["delivery_pct"] = pd.to_numeric(merged["delivery_pct"], errors="coerce").round(1)
    return merged
