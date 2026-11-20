"""Firewall 40 — Institutional Survivor Scanner Module.

Runs as a zero-overhead, selectable strategy layer on top of the existing
Scanner v3 universe output + EOD delivery + fundamental gate data.
"""
from __future__ import annotations

import numpy as np
import pandas as pd


def _num(val, default=0.0):
    try:
        if pd.isna(val):
            return default
        return float(val)
    except Exception:
        return default


def run_firewall_40(df: pd.DataFrame, max_stocks: int = 40, max_per_sector: int = 5) -> pd.DataFrame:
    """Filter a scanned universe DataFrame down to the Top 40 Institutional Survivors."""
    if df is None or df.empty:
        return pd.DataFrame()

    work = df.copy()
    passed_rows = []

    for idx, row in work.iterrows():
        # --- STAGE 1: Fundamental & Event Shield ---
        f_grade = str(row.get("fundamental_grade", "") or "").strip().upper()
        f_flag = str(row.get("fundamental_flag", "") or "").strip().upper()
        f_score = _num(row.get("fundamental_score"), 60.0)

        # Hard veto: upcoming earnings binary gap or failing fundamental grade
        if f_flag == "EARNINGS_EVENT_RISK":
            continue
        if f_grade == "D":
            continue

        # --- STAGE 2: Anti-Trap & 52-Week High Proximity ---
        if bool(row.get("false_breakout", False)):
            continue
        comp_vol = _num(row.get("component_volume"), 0.5)
        if comp_vol <= 0.10:
            continue

        pct_below_52w = _num(row.get("pct_below_52w"), 0.0)
        if pct_below_52w > 25.0:
            continue

        clv = _num(row.get("clv"), 0.55)
        if clv < 0.40:
            continue

        # --- STAGE 3: Trend & Momentum Health ---
        rsi = _num(row.get("rsi"), 55.0)
        adx = _num(row.get("adx"), 20.0)
        if rsi < 48.0 or rsi > 76.0:
            continue
        if adx < 16.0:
            continue

        # --- STAGE 4: Institutional Footprint Scoring ---
        base_score = _num(row.get("score"), 50.0)
        dly_pct = _num(row.get("delivery_pct"), 0.0)
        dly_exp = _num(row.get("deliv_expansion_ratio"), 1.0)
        ud_ratio = _num(row.get("ud_vol_ratio"), 1.0)
        sec_rs = _num(row.get("sector_relative_strength"), 0.0)
        sqz = _num(row.get("squeeze"), 0.5)

        inst_bonus = 0.0
        if dly_pct >= 50.0:
            inst_bonus += 6.0
        if dly_exp >= 1.25:
            inst_bonus += 6.0
        if ud_ratio >= 1.20:
            inst_bonus += 5.0
        if sec_rs > 0.0:
            inst_bonus += min(6.0, sec_rs * 0.8)
        if sqz >= 0.75:
            inst_bonus += 4.0
        if f_grade in {"A+", "A"}:
            inst_bonus += 6.0

        fw_score = min(100.0, round(base_score * 0.65 + f_score * 0.20 + inst_bonus, 2))

        row_dict = row.to_dict()
        row_dict["firewall_score"] = fw_score
        row_dict["firewall_passed"] = True
        row_dict["scanner_tag"] = "🛡️ FIREWALL 40"
        passed_rows.append(row_dict)

    if not passed_rows:
        return pd.DataFrame(columns=list(df.columns) + ["firewall_score", "firewall_passed", "scanner_tag"])

    res = pd.DataFrame(passed_rows)
    res = res.sort_values(
        by=[c for c in ["firewall_score", "score", "distance_pct"] if c in res.columns],
        ascending=[False, False, True][:sum(c in res.columns for c in ["firewall_score", "score", "distance_pct"])],
        kind="stable",
    ).reset_index(drop=True)

    # --- STAGE 5: Sector Diversification Cap (Max 5 per Sector) ---
    sector_col = next((c for c in ["sector", "Sector", "industry"] if c in res.columns), None)
    if sector_col:
        capped = []
        sector_counts = {}
        for _, r in res.iterrows():
            sec = str(r.get(sector_col, "General") or "General").strip()
            cnt = sector_counts.get(sec, 0)
            if cnt < max_per_sector:
                capped.append(r)
                sector_counts[sec] = cnt + 1
            if len(capped) >= max_stocks:
                break
        res = pd.DataFrame(capped).reset_index(drop=True)
    else:
        res = res.head(max_stocks).reset_index(drop=True)

    return res


def apply_scanner_mode(df: pd.DataFrame, mode: str) -> pd.DataFrame:
    """Apply the user-selected scanner mode without altering Scanner v3's core logic."""
    if df is None or df.empty:
        return pd.DataFrame()

    mode_str = str(mode or "Scanner v3 (Classic Momentum)")

    if "Firewall 40" in mode_str:
        return run_firewall_40(df, max_stocks=40, max_per_sector=5)

    if "Dual Mode" in mode_str:
        fw_df = run_firewall_40(df, max_stocks=40, max_per_sector=5)
        fw_syms = set(fw_df["symbol"].astype(str).str.upper().tolist()) if not fw_df.empty and "symbol" in fw_df.columns else set()
        fw_scores = (
            dict(zip(fw_df["symbol"].astype(str).str.upper(), fw_df["firewall_score"]))
            if not fw_df.empty and "symbol" in fw_df.columns
            else {}
        )
        out = df.copy()
        out["firewall_passed"] = out["symbol"].astype(str).str.upper().isin(fw_syms)
        out["firewall_score"] = out["symbol"].astype(str).str.upper().map(fw_scores).fillna(0.0)
        out["scanner_tag"] = np.where(out["firewall_passed"], "🏆 DUAL CONFIRMED", "🚀 SCANNER V3")
        # Boost Dual Confirmed stocks to the top while preserving score order inside each group
        sort_cols = ["firewall_passed"] + [c for c in ["rank_score", "score", "distance_pct"] if c in out.columns]
        asc = [False] + [False, False, True][: len(sort_cols) - 1]
        out = out.sort_values(sort_cols, ascending=asc, kind="stable").reset_index(drop=True)
        return out

    # Default: Classic Scanner v3 untouched
    out = df.copy()
    out["firewall_passed"] = False
    out["scanner_tag"] = "🚀 SCANNER V3"
    return out
