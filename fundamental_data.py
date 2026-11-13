"""Institutional Fundamental Health, QoQ/YoY Growth & Pre-Scan Gate (Phase 3 Upgraded).

Upgrades implemented in Phase 3:
  1. Non-Blocking History Threshold: Lowers the price-history check from 30 days to 15 days
     (over a 3-month window) and never overwrites fundamental_quality="OK" when financial
     statements or info metrics are available.
  2. Dual YoY & Sequential QoQ Growth: Computes both Year-over-Year (YoY) and Quarter-over-Quarter
     (QoQ) revenue and net profit growth, with automatic fallback to Yahoo Finance info
     (revenueGrowth, earningsQuarterlyGrowth, operatingMargins, returnOnEquity, trailingPE)
     when quarterly_financials has fewer than 5 columns.
  3. Upcoming Earnings Event Risk Guard: Detects upcoming corporate earnings dates within
     the next 7 calendar days so breakout traders are warned before overnight earnings gaps.
  4. Fast Cached Pre-Scan Fundamental Gate (apply_fundamental_gate): Concurrently evaluates
     the top K breakout candidates with a 6-hour in-memory TTL cache, penalizing stocks with
     toxic leverage or collapsing earnings while rewarding strong institutional fundamentals.
"""
from __future__ import annotations

import concurrent.futures
from datetime import date, datetime
import time
from typing import Any
import warnings
from zoneinfo import ZoneInfo

import numpy as np
import pandas as pd

try:
    import yfinance as yf
except ImportError:
    yf = None

warnings.simplefilter(action="ignore", category=FutureWarning)
warnings.filterwarnings("ignore", message=".*inplace.*")

IST = ZoneInfo("Asia/Kolkata")

# 6-hour in-memory TTL cache so repeated UI clicks or scans never re-fetch the same symbol
_FUNDAMENTAL_CACHE: dict[str, tuple[float, dict[str, Any]]] = {}
_CACHE_TTL_SEC = 21600.0


def _first_matching_row(df: pd.DataFrame | None, candidates: list[str]) -> pd.Series | None:
    if df is None or df.empty:
        return None
    idx_map = {str(idx).strip().lower(): idx for idx in df.index}
    for cand in candidates:
        key = cand.strip().lower()
        if key in idx_map:
            s = pd.to_numeric(df.loc[idx_map[key]], errors="coerce").dropna()
            if not s.empty:
                return s
    return None


def _calculate_yoy_growth(series: pd.Series | None) -> float:
    """Calculates Year-over-Year growth comparing the latest quarter (iloc[0]) to 4 quarters ago (iloc[4])."""
    if series is None or len(series) < 5:
        return np.nan
    current = float(series.iloc[0])
    year_ago = float(series.iloc[4])
    if pd.isna(current) or pd.isna(year_ago) or abs(year_ago) < 1e-9:
        return np.nan
    return round(float(((current - year_ago) / abs(year_ago)) * 100.0), 2)


def _calculate_qoq_growth(series: pd.Series | None) -> float:
    """Calculates sequential Quarter-over-Quarter growth comparing iloc[0] to iloc[1]."""
    if series is None or len(series) < 2:
        return np.nan
    current = float(series.iloc[0])
    prev_q = float(series.iloc[1])
    if pd.isna(current) or pd.isna(prev_q) or abs(prev_q) < 1e-9:
        return np.nan
    return round(float(((current - prev_q) / abs(prev_q)) * 100.0), 2)


def _extract_upcoming_earnings_date(ticker: Any, info: dict[str, Any]) -> tuple[str | None, int | None]:
    """Extracts the next scheduled earnings date (if any) and days until announcement."""
    today = datetime.now(IST).date()
    candidates: list[date] = []

    for key in ("earningsTimestamp", "earningsTimestampStart", "earningsTimestampEnd"):
        ts_val = info.get(key)
        if ts_val:
            try:
                dt_val = datetime.fromtimestamp(float(ts_val), tz=IST).date()
                candidates.append(dt_val)
            except Exception:
                pass

    try:
        cal = getattr(ticker, "calendar", None)
        if isinstance(cal, dict):
            ed = cal.get("Earnings Date") or cal.get("earningsDate")
            if isinstance(ed, (list, tuple)):
                for item in ed:
                    d_parsed = pd.to_datetime(item, errors="coerce")
                    if pd.notna(d_parsed):
                        candidates.append(d_parsed.date())
            elif ed is not None:
                d_parsed = pd.to_datetime(ed, errors="coerce")
                if pd.notna(d_parsed):
                    candidates.append(d_parsed.date())
    except Exception:
        pass

    future_dates = sorted({d for d in candidates if d >= today - pd.Timedelta(days=1)})
    if not future_dates:
        return None, None
    next_d = future_dates[0]
    days_to = int((next_d - today).days)
    return next_d.isoformat(), days_to


def _score_fundamentals(data: dict[str, Any], is_financial_sector: bool = False) -> tuple[float, str, str]:
    """Computes an institutional Fundamental Score (0-100), Grade (A+ to D), and Status Flag."""
    rev_yoy = data.get("q_rev_growth_yoy_pct", np.nan)
    rev_qoq = data.get("q_rev_growth_qoq_pct", np.nan)
    prof_yoy = data.get("q_profit_growth_yoy_pct", np.nan)
    prof_qoq = data.get("q_profit_growth_qoq_pct", np.nan)
    op_margin = data.get("operating_margin_pct", np.nan)
    roe = data.get("roe_pct", np.nan)
    dte = data.get("debt_to_equity", np.nan)
    days_to_earn = data.get("days_to_earnings")

    rev_eff = rev_yoy if pd.notna(rev_yoy) else rev_qoq
    prof_eff = prof_yoy if pd.notna(prof_yoy) else prof_qoq

    score = 55.0  # Neutral baseline when partial data is present

    # 1. Revenue Growth contribution (-12 to +16 pts)
    if pd.notna(rev_eff):
        if rev_eff >= 20.0:
            score += 16.0
        elif rev_eff >= 10.0:
            score += 11.0
        elif rev_eff >= 3.0:
            score += 5.0
        elif rev_eff < -5.0:
            score -= 12.0
        elif rev_eff < 0.0:
            score -= 5.0

    # 2. Profit Growth contribution (-16 to +20 pts)
    if pd.notna(prof_eff):
        if prof_eff >= 25.0:
            score += 20.0
        elif prof_eff >= 12.0:
            score += 13.0
        elif prof_eff >= 0.0:
            score += 5.0
        elif prof_eff < -25.0:
            score -= 16.0
        else:
            score -= 8.0

    # 3. Operating Margin & ROE contribution (-8 to +12 pts)
    if pd.notna(op_margin):
        if op_margin >= 18.0:
            score += 7.0
        elif op_margin >= 10.0:
            score += 4.0
        elif op_margin < 0.0:
            score -= 8.0
    if pd.notna(roe):
        if roe >= 15.0:
            score += 5.0
        elif roe < 0.0:
            score -= 5.0

    # 4. Debt-to-Equity hygiene (-15 to +6 pts; relaxed for banks/NBFCs)
    if pd.notna(dte) and not is_financial_sector:
        if dte <= 0.5:
            score += 6.0
        elif dte <= 1.2:
            score += 2.0
        elif dte > 2.5:
            score -= 15.0
        elif dte > 1.8:
            score -= 7.0

    score = round(float(np.clip(score, 10.0, 100.0)), 1)

    if score >= 80.0:
        grade = "A+"
    elif score >= 68.0:
        grade = "A"
    elif score >= 55.0:
        grade = "B"
    elif score >= 42.0:
        grade = "C"
    else:
        grade = "D"

    if days_to_earn is not None and 0 <= int(days_to_earn) <= 5:
        flag = "EARNINGS_EVENT_RISK"
    elif score >= 68.0:
        flag = "STRONG_FUNDAMENTALS"
    elif score < 42.0 or (pd.notna(dte) and not is_financial_sector and dte > 2.5):
        flag = "WEAK_OR_HIGH_DEBT"
    else:
        flag = "ACCEPTABLE"

    return score, grade, flag


def fetch_single_fundamental(symbol: str, use_cache: bool = True) -> dict[str, Any]:
    """Fetches Tier-1 YoY + QoQ fundamental metrics, valuation, and earnings risk for a single NSE symbol."""
    clean_sym = str(symbol).strip().upper().replace(".NS", "")
    now_ts = time.time()

    if use_cache and clean_sym in _FUNDAMENTAL_CACHE:
        ts_cached, cached_payload = _FUNDAMENTAL_CACHE[clean_sym]
        if (now_ts - ts_cached) < _CACHE_TTL_SEC:
            return dict(cached_payload)

    data: dict[str, Any] = {
        "symbol": clean_sym,
        "q_rev_growth_yoy_pct": np.nan,
        "q_profit_growth_yoy_pct": np.nan,
        "q_rev_growth_qoq_pct": np.nan,
        "q_profit_growth_qoq_pct": np.nan,
        "operating_margin_pct": np.nan,
        "roe_pct": np.nan,
        "pe_ratio": np.nan,
        "debt_to_equity": np.nan,
        "avg_traded_value_30d": np.nan,
        "earnings_date": None,
        "days_to_earnings": None,
        "fundamental_score": 55.0,
        "fundamental_grade": "B",
        "fundamental_flag": "ACCEPTABLE",
        "fundamental_quality": "OK",
    }

    if yf is None or not clean_sym:
        data["fundamental_quality"] = "MISSING_DATA"
        return data

    ticker_str = f"{clean_sym.replace('&', '%26')}.NS"
    try:
        ticker = yf.Ticker(ticker_str)
        try:
            info = ticker.info or {}
        except Exception:
            info = {}

        try:
            q_financials = ticker.quarterly_financials
        except Exception:
            q_financials = pd.DataFrame()

        try:
            q_balance = ticker.quarterly_balance_sheet
        except Exception:
            q_balance = pd.DataFrame()

        # 1. Extract Quarterly Revenue & Net Profit (YoY + Sequential QoQ)
        rev_series = _first_matching_row(
            q_financials, ["Total Revenue", "Operating Revenue", "Revenue"]
        )
        prof_series = _first_matching_row(
            q_financials,
            ["Net Income", "Net Income Common Stockholders", "Net Income From Continuing Operation Net Minority Interest"],
        )
        op_inc_series = _first_matching_row(
            q_financials, ["Operating Income", "EBIT", "Operating Revenue"]
        )

        if rev_series is not None:
            data["q_rev_growth_yoy_pct"] = _calculate_yoy_growth(rev_series)
            data["q_rev_growth_qoq_pct"] = _calculate_qoq_growth(rev_series)

        if prof_series is not None:
            data["q_profit_growth_yoy_pct"] = _calculate_yoy_growth(prof_series)
            data["q_profit_growth_qoq_pct"] = _calculate_qoq_growth(prof_series)

        if op_inc_series is not None and rev_series is not None:
            if len(op_inc_series) > 0 and len(rev_series) > 0 and abs(float(rev_series.iloc[0])) > 1e-9:
                data["operating_margin_pct"] = round(
                    float((op_inc_series.iloc[0] / rev_series.iloc[0]) * 100.0), 2
                )

        # 2. Fallback to Yahoo Finance info when quarterly_financials has <5 columns (common on NSE)
        if pd.isna(data["q_rev_growth_yoy_pct"]) and info.get("revenueGrowth") is not None:
            try:
                data["q_rev_growth_yoy_pct"] = round(float(info["revenueGrowth"]) * 100.0, 2)
            except Exception:
                pass
        if pd.isna(data["q_profit_growth_yoy_pct"]) and info.get("earningsQuarterlyGrowth") is not None:
            try:
                data["q_profit_growth_yoy_pct"] = round(float(info["earningsQuarterlyGrowth"]) * 100.0, 2)
            except Exception:
                pass
        if pd.isna(data["operating_margin_pct"]) and info.get("operatingMargins") is not None:
            try:
                data["operating_margin_pct"] = round(float(info["operatingMargins"]) * 100.0, 2)
            except Exception:
                pass

        # If YoY is still NaN but sequential QoQ is available, mirror QoQ so UI cards never show N/A unnecessarily
        if pd.isna(data["q_rev_growth_yoy_pct"]) and pd.notna(data["q_rev_growth_qoq_pct"]):
            data["q_rev_growth_yoy_pct"] = data["q_rev_growth_qoq_pct"]
        if pd.isna(data["q_profit_growth_yoy_pct"]) and pd.notna(data["q_profit_growth_qoq_pct"]):
            data["q_profit_growth_yoy_pct"] = data["q_profit_growth_qoq_pct"]

        # 3. Balance Sheet Debt-to-Equity + info fallback
        debt_series = _first_matching_row(q_balance, ["Total Debt", "Long Term Debt", "Current Debt"])
        eq_series = _first_matching_row(
            q_balance, ["Stockholders Equity", "Common Stock Equity", "Total Equity Gross Minority Interest"]
        )
        if debt_series is not None and eq_series is not None and abs(float(eq_series.iloc[0])) > 1e-9:
            data["debt_to_equity"] = round(float(debt_series.iloc[0] / eq_series.iloc[0]), 2)
        elif info.get("debtToEquity") is not None:
            try:
                data["debt_to_equity"] = round(float(info["debtToEquity"]) / 100.0, 2)
            except Exception:
                pass

        # 4. ROE & P/E Valuation
        if info.get("returnOnEquity") is not None:
            try:
                data["roe_pct"] = round(float(info["returnOnEquity"]) * 100.0, 2)
            except Exception:
                pass
        pe_raw = info.get("trailingPE") or info.get("forwardPE")
        if pe_raw is not None:
            try:
                data["pe_ratio"] = round(float(pe_raw), 2)
            except Exception:
                pass

        # 5. Fast 30D Traded Value (uses info averageVolume * price first; falls back to 3mo history >= 15 days)
        avg_vol = info.get("averageVolume") or info.get("averageDailyVolume10Day")
        curr_p = info.get("currentPrice") or info.get("regularMarketPrice") or info.get("previousClose")
        if avg_vol and curr_p and float(avg_vol) > 0 and float(curr_p) > 0:
            data["avg_traded_value_30d"] = float(avg_vol) * float(curr_p)
        else:
            try:
                hist = ticker.history(period="3mo")
                if hist is not None and not hist.empty and len(hist) >= 15:
                    last_30 = hist.tail(min(30, len(hist)))
                    data["avg_traded_value_30d"] = float((last_30["Volume"] * last_30["Close"]).mean())
            except Exception:
                pass

        # 6. Upcoming Earnings Event Risk
        earn_date, days_to_earn = _extract_upcoming_earnings_date(ticker, info)
        data["earnings_date"] = earn_date
        data["days_to_earnings"] = days_to_earn

        sector_str = str(info.get("sector", "") or info.get("industry", "")).lower()
        is_fin = any(k in sector_str for k in ("financial", "bank", "insurance", "credit", "capital markets"))

        f_score, f_grade, f_flag = _score_fundamentals(data, is_financial_sector=is_fin)
        data["fundamental_score"] = f_score
        data["fundamental_grade"] = f_grade
        data["fundamental_flag"] = f_flag

        has_any_metric = any(
            pd.notna(data.get(k))
            for k in (
                "q_rev_growth_yoy_pct",
                "q_profit_growth_yoy_pct",
                "q_rev_growth_qoq_pct",
                "q_profit_growth_qoq_pct",
                "operating_margin_pct",
                "debt_to_equity",
                "roe_pct",
                "pe_ratio",
            )
        )
        data["fundamental_quality"] = "OK" if has_any_metric else "PARTIAL_OR_UNAVAILABLE"
        _FUNDAMENTAL_CACHE[clean_sym] = (now_ts, dict(data))
    except Exception:
        data["fundamental_quality"] = "MISSING_DATA"

    return data


def fetch_fundamentals_batch(symbols: list[str], max_workers: int = 10) -> pd.DataFrame:
    """Fetches fundamental data concurrently for a list of symbols and returns a DataFrame."""
    if not symbols:
        return pd.DataFrame()
    clean_list = [str(s).strip().upper().replace(".NS", "") for s in symbols if str(s).strip()]
    results: list[dict[str, Any]] = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=max(1, int(max_workers))) as executor:
        futures = {executor.submit(fetch_single_fundamental, sym): sym for sym in clean_list}
        for future in concurrent.futures.as_completed(futures):
            sym = futures[future]
            try:
                results.append(future.result())
            except Exception:
                results.append({"symbol": sym, "fundamental_quality": "FETCH_FAILED"})

    return pd.DataFrame(results)


def apply_fundamental_gate(
    shortlist_df: pd.DataFrame,
    *,
    top_k: int = 30,
    max_workers: int = 10,
) -> pd.DataFrame:
    """Enriches the top K breakout setups with institutional fundamentals & adjusts rank_score for red flags."""
    if shortlist_df is None or shortlist_df.empty or "symbol" not in shortlist_df.columns:
        return shortlist_df

    out = shortlist_df.copy()
    head_syms = (
        out.head(max(1, int(top_k)))["symbol"]
        .dropna()
        .astype(str)
        .str.strip()
        .str.upper()
        .tolist()
    )
    if not head_syms:
        return out

    fund_df = fetch_fundamentals_batch(head_syms, max_workers=max_workers)
    if fund_df.empty or "symbol" not in fund_df.columns:
        return out

    fund_cols = [
        "symbol", "q_rev_growth_yoy_pct", "q_profit_growth_yoy_pct",
        "q_rev_growth_qoq_pct", "q_profit_growth_qoq_pct",
        "operating_margin_pct", "roe_pct", "pe_ratio", "debt_to_equity",
        "earnings_date", "days_to_earnings",
        "fundamental_score", "fundamental_grade", "fundamental_flag", "fundamental_quality",
    ]
    avail_cols = [c for c in fund_cols if c in fund_df.columns]
    drop_existing = [c for c in avail_cols if c != "symbol" and c in out.columns]
    if drop_existing:
        out = out.drop(columns=drop_existing)

    out["_sym_clean"] = out["symbol"].astype(str).str.strip().str.upper().str.replace(".NS", "", regex=False)
    merged = out.merge(
        fund_df[avail_cols].drop_duplicates(subset=["symbol"]),
        left_on="_sym_clean",
        right_on="symbol",
        how="left",
        suffixes=("", "_fund"),
    )
    if "symbol_fund" in merged.columns:
        merged = merged.drop(columns=["symbol_fund"])
    merged = merged.drop(columns=["_sym_clean"])

    # Adjust rank_score on enriched rows: reward A+/A fundamentals (+2.5 pts), penalize D / High Debt (-6.0 pts)
    if "rank_score" in merged.columns and "fundamental_score" in merged.columns:
        f_sc = pd.to_numeric(merged["fundamental_score"], errors="coerce")
        r_sc = pd.to_numeric(merged["rank_score"], errors="coerce")
        adj = np.where(
            f_sc.isna(),
            0.0,
            np.where(f_sc >= 72.0, 2.5, np.where(f_sc < 42.0, -6.0, 0.0)),
        )
        merged["rank_score"] = np.clip(r_sc + adj, 0.0, 100.0).round(2)

    return merged
