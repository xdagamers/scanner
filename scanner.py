"""NIFTY 500 Institutional Breakout & Anti-Trap Scanner (Phase 1 v3 Regime-Adaptive Engine).

Upgrades implemented in Phase 1:
  1. Pre-Score Delivery Integration: Loads NSE delivery data & multi-session baseline before scoring
     so Delivery %, Deliverable Qty, and Relative Delivery Expansion directly impact Volume & Rank scores.
  2. Relative Delivery Baseline: Compares daily Deliverable Qty against both the multi-day NSE baseline
     and the stock's 20-day average traded volume to isolate true institutional Demat absorption.
  3. True Sector Relative Strength: Preserves NSE Industry classifications in load_universe() and
     constructs equal-weighted Sector Index series in memory (zero extra API calls) so
     sector_relative_strength is accurately calculated for every stock.
  4. Market Breadth & India VIX: Computes NIFTY 500 internal breadth (% above 50 EMA & % above 200 SMA)
     plus India VIX (^INDIAVIX) alongside NIFTY 50 trend structure.
  5. Regime-Adaptive Weights & Bear-Market Gate: Dynamically shifts component weights across Bullish,
     Neutral (Sniper Mode), Overheated (Anti-Chase), and Bearish (Capital Preservation) regimes.
  6. Non-Inverting Target & Stop Math: Anchors Target 1, Target 2, and Target 3 strictly above
     max(Price, Breakout_Trigger) so targets never invert when a stock trades above resistance.
  7. Progressive VCP & Volume Dry-Up (VDU): Evaluates 20D -> 10D -> 5D range contraction and quiet
     pullback volume dry-up prior to breakout expansion.
  8. Weekly Trend Alignment & 10-Session Extension Guard: Verifies weekly trend structure (10W > 40W)
     and flags multi-week vertical spikes (>18% in 10 sessions) as overextended traps.
"""
from __future__ import annotations

import io
import time
import warnings
from typing import Any

import numpy as np
import pandas as pd
import requests

try:
    import yfinance as yf
except ImportError:
    yf = None

try:
    from delivery_loader import get_delivery_lookup_dict
except ImportError:
    def get_delivery_lookup_dict(report_date=None) -> dict:
        return {}

warnings.simplefilter(action="ignore", category=FutureWarning)

NIFTY500_URL = "https://nsearchives.nseindia.com/content/indices/ind_nifty500list.csv"
NIFTY200_URL = "https://nsearchives.nseindia.com/content/indices/ind_nifty200list.csv"
NIFTY100_URL = "https://nsearchives.nseindia.com/content/indices/ind_nifty100list.csv"

NSE_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
    ),
    "Accept": "text/csv,text/plain,*/*",
    "Referer": "https://www.nseindia.com/",
}

DEFAULT_WEIGHTS: dict[str, float] = {
    "proximity": 18.0,
    "resistance": 12.0,
    "volume": 16.0,
    "trend": 14.0,
    "momentum": 10.0,
    "adx": 8.0,
    "squeeze": 8.0,
    "relative_strength": 9.0,
    "candle": 2.0,
    "market_regime": 3.0,
}

# Regime-adaptive weight profiles (each sums to 100.0)
REGIME_WEIGHT_PROFILES: dict[str, dict[str, float]] = {
    "Bullish": {
        "proximity": 18.0,
        "resistance": 11.0,
        "volume": 18.0,
        "trend": 14.0,
        "momentum": 11.0,
        "adx": 8.0,
        "squeeze": 7.0,
        "relative_strength": 9.0,
        "candle": 2.0,
        "market_regime": 2.0,
    },
    "Neutral": {
        "proximity": 18.0,
        "resistance": 14.0,
        "volume": 18.0,
        "trend": 12.0,
        "momentum": 8.0,
        "adx": 6.0,
        "squeeze": 12.0,
        "relative_strength": 8.0,
        "candle": 2.0,
        "market_regime": 2.0,
    },
    "Overheated": {
        "proximity": 20.0,
        "resistance": 13.0,
        "volume": 17.0,
        "trend": 12.0,
        "momentum": 7.0,
        "adx": 6.0,
        "squeeze": 13.0,
        "relative_strength": 8.0,
        "candle": 2.0,
        "market_regime": 2.0,
    },
    "Bearish": {
        "proximity": 14.0,
        "resistance": 12.0,
        "volume": 16.0,
        "trend": 14.0,
        "momentum": 7.0,
        "adx": 5.0,
        "squeeze": 9.0,
        "relative_strength": 13.0,
        "candle": 2.0,
        "market_regime": 8.0,
    },
}

FALLBACK_UNIVERSE = [
    ("RELIANCE", "Reliance Industries Ltd.", "Large Cap", "Oil Gas & Consumable Fuels"),
    ("TCS", "Tata Consultancy Services Ltd.", "Large Cap", "Information Technology"),
    ("HDFCBANK", "HDFC Bank Ltd.", "Large Cap", "Financial Services"),
    ("ICICIBANK", "ICICI Bank Ltd.", "Large Cap", "Financial Services"),
    ("BHARTIARTL", "Bharti Airtel Ltd.", "Large Cap", "Telecommunication"),
    ("INFY", "Infosys Ltd.", "Large Cap", "Information Technology"),
    ("SBIN", "State Bank of India", "Large Cap", "Financial Services"),
    ("LT", "Larsen & Toubro Ltd.", "Large Cap", "Construction"),
    ("ITC", "ITC Ltd.", "Large Cap", "Fast Moving Consumer Goods"),
    ("SUNPHARMA", "Sun Pharmaceutical Industries Ltd.", "Large Cap", "Healthcare"),
    ("M&M", "Mahindra & Mahindra Ltd.", "Large Cap", "Automobile and Auto Components"),
    ("MARUTI", "Maruti Suzuki India Ltd.", "Large Cap", "Automobile and Auto Components"),
    ("TATAMOTORS", "Tata Motors Ltd.", "Large Cap", "Automobile and Auto Components"),
    ("NTPC", "NTPC Ltd.", "Large Cap", "Power"),
    ("AXISBANK", "Axis Bank Ltd.", "Large Cap", "Financial Services"),
    ("HAL", "Hindustan Aeronautics Ltd.", "Large Cap", "Capital Goods"),
    ("BEL", "Bharat Electronics Ltd.", "Large Cap", "Capital Goods"),
    ("TRENT", "Trent Ltd.", "Large Cap", "Consumer Services"),
    ("SIEMENS", "Siemens Ltd.", "Large Cap", "Capital Goods"),
    ("ABB", "ABB India Ltd.", "Large Cap", "Capital Goods"),
    ("JSWSTEEL", "JSW Steel Ltd.", "Large Cap", "Metals & Mining"),
    ("TATASTEEL", "Tata Steel Ltd.", "Large Cap", "Metals & Mining"),
    ("HINDALCO", "Hindalco Industries Ltd.", "Large Cap", "Metals & Mining"),
    ("COALINDIA", "Coal India Ltd.", "Large Cap", "Oil Gas & Consumable Fuels"),
    ("ONGC", "Oil & Natural Gas Corporation Ltd.", "Large Cap", "Oil Gas & Consumable Fuels"),
    ("IOC", "Indian Oil Corporation Ltd.", "Large Cap", "Oil Gas & Consumable Fuels"),
    ("POWERGRID", "Power Grid Corporation of India Ltd.", "Large Cap", "Power"),
    ("ULTRACEMCO", "UltraTech Cement Ltd.", "Large Cap", "Construction Materials"),
    ("AMBUJACEM", "Ambuja Cements Ltd.", "Large Cap", "Construction Materials"),
    ("GRASIM", "Grasim Industries Ltd.", "Large Cap", "Construction Materials"),
    ("BAJFINANCE", "Bajaj Finance Ltd.", "Large Cap", "Financial Services"),
    ("KOTAKBANK", "Kotak Mahindra Bank Ltd.", "Large Cap", "Financial Services"),
    ("DRREDDY", "Dr. Reddy's Laboratories Ltd.", "Large Cap", "Healthcare"),
    ("CIPLA", "Cipla Ltd.", "Large Cap", "Healthcare"),
    ("DIVISLAB", "Divi's Laboratories Ltd.", "Large Cap", "Healthcare"),
    ("GLENMARK", "Glenmark Pharmaceuticals Ltd.", "Mid Cap", "Healthcare"),
    ("MEDANTA", "Global Health Ltd.", "Mid Cap", "Healthcare"),
    ("PERSISTENT", "Persistent Systems Ltd.", "Mid Cap", "Information Technology"),
    ("COFORGE", "Coforge Ltd.", "Mid Cap", "Information Technology"),
    ("DIXON", "Dixon Technologies (India) Ltd.", "Mid Cap", "Consumer Durables"),
    ("POLYCAB", "Polycab India Ltd.", "Mid Cap", "Capital Goods"),
    ("CUMMINSIND", "Cummins India Ltd.", "Mid Cap", "Capital Goods"),
    ("APLAPOLLO", "APL Apollo Tubes Ltd.", "Mid Cap", "Capital Goods"),
    ("FEDERALBNK", "The Federal Bank Ltd.", "Mid Cap", "Financial Services"),
    ("MAHABANK", "Bank of Maharashtra", "Mid Cap", "Financial Services"),
    ("PRESTIGE", "Prestige Estates Projects Ltd.", "Mid Cap", "Realty"),
    ("GMRAIRPORT", "GMR Airports Ltd.", "Mid Cap", "Services"),
    ("NHPC", "NHPC Ltd.", "Mid Cap", "Power"),
    ("ACE", "Action Construction Equipment Ltd.", "Small Cap", "Capital Goods"),
    ("ENGINERSIN", "Engineers India Ltd.", "Small Cap", "Construction"),
    ("CHENNPETRO", "Chennai Petroleum Corporation Ltd.", "Small Cap", "Oil Gas & Consumable Fuels"),
]

_UNIVERSE_CACHE: dict[str, Any] = {"timestamp": 0.0, "df": None}
_INDEX_CACHE: dict[tuple[str, str], tuple[float, pd.DataFrame]] = {}


def _fetch_nse_csv(url: str, timeout: float = 10.0) -> pd.DataFrame | None:
    try:
        r = requests.get(url, headers=NSE_HEADERS, timeout=timeout)
        if r.status_code == 200 and r.text.strip():
            df = pd.read_csv(io.StringIO(r.text))
            df.columns = [str(c).strip() for c in df.columns]
            return df
    except Exception:
        pass
    return None


def load_universe() -> pd.DataFrame:
    """Loads NIFTY 500 universe with symbol, company_name, cap_category, and industry."""
    now_ts = time.time()
    if _UNIVERSE_CACHE["df"] is not None and (now_ts - float(_UNIVERSE_CACHE["timestamp"])) < 21600:
        return _UNIVERSE_CACHE["df"].copy()

    df500 = _fetch_nse_csv(NIFTY500_URL)
    if df500 is not None and not df500.empty:
        sym_col = next((c for c in df500.columns if c.lower() == "symbol"), None)
        name_col = next((c for c in df500.columns if "company" in c.lower()), None)
        ind_col = next((c for c in df500.columns if "industry" in c.lower()), None)

        if sym_col:
            df100 = _fetch_nse_csv(NIFTY100_URL, timeout=6.0)
            df200 = _fetch_nse_csv(NIFTY200_URL, timeout=6.0)

            large_set: set[str] = set()
            mid_set: set[str] = set()
            if df100 is not None:
                sc = next((c for c in df100.columns if c.lower() == "symbol"), None)
                if sc:
                    large_set = set(df100[sc].astype(str).str.strip().str.upper())
            if df200 is not None:
                sc = next((c for c in df200.columns if c.lower() == "symbol"), None)
                if sc:
                    all200 = set(df200[sc].astype(str).str.strip().str.upper())
                    mid_set = all200 - large_set

            rows = []
            for idx, r in df500.iterrows():
                sym = str(r.get(sym_col, "")).strip().upper()
                if not sym or sym in {"NAN", "NONE"} or "DUMMY" in sym:
                    continue
                comp = str(r.get(name_col, sym)).strip() if name_col else sym
                ind = str(r.get(ind_col, "General")).strip() if ind_col else "General"
                if large_set:
                    cap = "Large Cap" if sym in large_set else ("Mid Cap" if sym in mid_set else "Small Cap")
                else:
                    cap = "Large Cap" if idx < 100 else ("Mid Cap" if idx < 250 else "Small Cap")
                rows.append({"symbol": sym, "company_name": comp, "cap_category": cap, "industry": ind})

            if rows:
                out = pd.DataFrame(rows).drop_duplicates(subset=["symbol"]).reset_index(drop=True)
                _UNIVERSE_CACHE["timestamp"] = now_ts
                _UNIVERSE_CACHE["df"] = out
                return out.copy()

    out_fb = pd.DataFrame(
        FALLBACK_UNIVERSE, columns=["symbol", "company_name", "cap_category", "industry"]
    )
    _UNIVERSE_CACHE["timestamp"] = now_ts
    _UNIVERSE_CACHE["df"] = out_fb
    return out_fb.copy()


def _clean_ohlcv(df: pd.DataFrame | None) -> pd.DataFrame | None:
    if df is None or df.empty:
        return None
    work = df.copy()
    if isinstance(work.columns, pd.MultiIndex):
        work.columns = work.columns.get_level_values(0)
    col_map = {str(c).strip().title(): c for c in work.columns}
    req = ["Open", "High", "Low", "Close", "Volume"]
    if not all(k in col_map for k in req):
        return None
    out = work[[col_map[k] for k in req]].copy()
    out.columns = req
    for c in req:
        out[c] = pd.to_numeric(out[c], errors="coerce")
    out = out.dropna(subset=["Open", "High", "Low", "Close"]).copy()
    out["Volume"] = out["Volume"].fillna(0.0)
    out = out[(out["Close"] > 0) & (out["High"] >= out["Low"])]
    if len(out) < 60:
        return None
    return out.sort_index()


def fetch_history(symbol: str, period: str = "2y") -> pd.DataFrame | None:
    """Fetches daily OHLCV history for a single NSE symbol."""
    if yf is None:
        return None
    clean_sym = str(symbol).strip().upper().replace(".NS", "").replace("&", "%26")
    ticker = f"{clean_sym}.NS"
    try:
        raw = yf.download(
            ticker,
            period=period,
            interval="1d",
            auto_adjust=True,
            progress=False,
            threads=False,
        )
        return _clean_ohlcv(raw)
    except Exception:
        return None


def fetch_index_history(index_ticker: str = "^NSEI", period: str = "2y") -> pd.DataFrame | None:
    """Fetches cached index history (e.g. ^NSEI or ^INDIAVIX)."""
    if yf is None:
        return None
    key = (str(index_ticker).strip(), str(period).strip())
    now_ts = time.time()
    cached = _INDEX_CACHE.get(key)
    if cached and (now_ts - cached[0]) < 600:
        return cached[1].copy()
    try:
        raw = yf.download(
            index_ticker,
            period=period,
            interval="1d",
            auto_adjust=True,
            progress=False,
            threads=False,
        )
        if raw is None or raw.empty:
            return None
        work = raw.copy()
        if isinstance(work.columns, pd.MultiIndex):
            work.columns = work.columns.get_level_values(0)
        col_map = {str(c).strip().title(): c for c in work.columns}
        if "Close" not in col_map:
            return None
        cols = [k for k in ["Open", "High", "Low", "Close", "Volume"] if k in col_map]
        out = work[[col_map[k] for k in cols]].copy()
        out.columns = cols
        for c in cols:
            out[c] = pd.to_numeric(out[c], errors="coerce")
        out = out.dropna(subset=["Close"]).sort_index()
        if not out.empty:
            _INDEX_CACHE[key] = (now_ts, out)
            return out.copy()
    except Exception:
        pass
    return None


def _ema(series: pd.Series, span: int) -> pd.Series:
    return series.ewm(span=span, adjust=False).mean()


def _rsi(close: pd.Series, period: int = 14) -> pd.Series:
    delta = close.diff()
    up = delta.clip(lower=0.0)
    down = -delta.clip(upper=0.0)
    gain = up.ewm(alpha=1.0 / period, min_periods=period, adjust=False).mean()
    loss = down.ewm(alpha=1.0 / period, min_periods=period, adjust=False).mean()
    rs = gain / loss.replace(0.0, np.nan)
    return (100.0 - (100.0 / (1.0 + rs))).fillna(50.0)


def _macd(close: pd.Series) -> tuple[pd.Series, pd.Series, pd.Series]:
    fast = _ema(close, 12)
    slow = _ema(close, 26)
    macd_line = fast - slow
    signal_line = _ema(macd_line, 9)
    hist = macd_line - signal_line
    return macd_line, signal_line, hist


def _atr_and_adx(df: pd.DataFrame, period: int = 14) -> tuple[pd.Series, pd.Series, pd.Series, pd.Series]:
    high = df["High"]
    low = df["Low"]
    close = df["Close"]
    prev_close = close.shift(1)

    tr = pd.concat(
        [(high - low), (high - prev_close).abs(), (low - prev_close).abs()],
        axis=1,
    ).max(axis=1)
    atr = tr.ewm(alpha=1.0 / period, min_periods=period, adjust=False).mean()

    up_move = high.diff()
    down_move = -low.diff()

    plus_dm = pd.Series(
        np.where((up_move > down_move) & (up_move > 0), up_move, 0.0),
        index=df.index,
    )
    minus_dm = pd.Series(
        np.where((down_move > up_move) & (down_move > 0), down_move, 0.0),
        index=df.index,
    )

    atr_safe = atr.replace(0.0, np.nan)
    plus_di = 100.0 * (plus_dm.ewm(alpha=1.0 / period, min_periods=period, adjust=False).mean() / atr_safe)
    minus_di = 100.0 * (minus_dm.ewm(alpha=1.0 / period, min_periods=period, adjust=False).mean() / atr_safe)

    dx = (100.0 * (plus_di - minus_di).abs() / (plus_di + minus_di).replace(0.0, np.nan)).fillna(0.0)
    adx = dx.ewm(alpha=1.0 / period, min_periods=period, adjust=False).mean().fillna(0.0)
    return atr, adx, plus_di.fillna(0.0), minus_di.fillna(0.0)


def _detect_candlestick(df: pd.DataFrame) -> str:
    if len(df) < 3:
        return "None"
    a, b, c = df.iloc[-3], df.iloc[-2], df.iloc[-1]
    body_a = abs(float(a["Close"] - a["Open"]))
    body_b = abs(float(b["Close"] - b["Open"]))
    body_c = abs(float(c["Close"] - c["Open"]))
    rng_c = max(float(c["High"] - c["Low"]), 1e-9)
    clv_c = float(c["Close"] - c["Low"]) / rng_c

    if (
        c["Close"] > c["Open"]
        and b["Close"] < b["Open"]
        and c["Close"] >= b["Open"]
        and c["Open"] <= b["Close"]
        and clv_c >= 0.65
    ):
        return "Bullish Engulfing"
    lower_wick = min(float(c["Open"]), float(c["Close"])) - float(c["Low"])
    upper_wick = float(c["High"]) - max(float(c["Open"]), float(c["Close"]))
    if lower_wick >= 2.0 * max(body_c, 1e-6) and upper_wick <= max(body_c, 1e-6) and clv_c >= 0.60:
        return "Hammer"
    if c["Close"] > c["Open"] and (body_c / rng_c) >= 0.75:
        return "Bullish Marubozu"
    if (
        a["Close"] < a["Open"]
        and body_b < body_a * 0.5
        and c["Close"] > c["Open"]
        and c["Close"] > (a["Open"] + a["Close"]) / 2.0
    ):
        return "Morning Star"
    if (
        b["Close"] < b["Open"]
        and c["Close"] > c["Open"]
        and c["Open"] < b["Low"]
        and c["Close"] > (b["Open"] + b["Close"]) / 2.0
    ):
        return "Piercing Line"
    if (
        a["Close"] > a["Open"]
        and b["Close"] > b["Open"]
        and c["Close"] > c["Open"]
        and a["Close"] < b["Close"] < c["Close"]
        and clv_c >= 0.65
    ):
        return "Three White Soldiers"
    return "None"


def _evaluate_market_context(
    nifty_df: pd.DataFrame | None,
    vix_df: pd.DataFrame | None = None,
    breadth_50ema_pct: float | None = None,
    breadth_200sma_pct: float | None = None,
) -> dict[str, Any]:
    """Determines Market Regime and Component Score using NIFTY 50, Internal Breadth, and India VIX."""
    regime = "Neutral"
    comp_score = 0.55
    vix_val = np.nan

    if vix_df is not None and not vix_df.empty and "Close" in vix_df.columns:
        vix_s = vix_df["Close"].dropna()
        if not vix_s.empty:
            vix_val = float(vix_s.iloc[-1])

    if nifty_df is not None and len(nifty_df) >= 50:
        nc = nifty_df["Close"].dropna()
        last_n = float(nc.iloc[-1])
        n_ema20 = float(_ema(nc, 20).iloc[-1])
        n_ema50 = float(_ema(nc, 50).iloc[-1])
        n_sma200 = float(nc.rolling(200, min_periods=50).mean().iloc[-1])
        n_rsi = float(_rsi(nc, 14).iloc[-1])

        b50 = float(breadth_50ema_pct) if breadth_50ema_pct is not None and np.isfinite(breadth_50ema_pct) else 55.0

        # Bearish / High-Volatility Gate
        if (
            (last_n < n_ema50 and last_n < n_sma200)
            or b50 < 35.0
            or (np.isfinite(vix_val) and vix_val >= 23.0 and last_n < n_ema20)
        ):
            regime = "Bearish"
            comp_score = 0.15
        # Overheated Climax Gate
        elif n_rsi > 73.0 or b50 > 82.0:
            regime = "Overheated"
            comp_score = 0.70
        # Confirmed Bullish Regime
        elif last_n > n_ema20 >= n_ema50 and b50 >= 50.0 and (not np.isfinite(vix_val) or vix_val < 21.0):
            regime = "Bullish"
            comp_score = 1.00 if (last_n > n_sma200 and b50 >= 58.0) else 0.85
        else:
            regime = "Neutral"
            comp_score = 0.60 if last_n >= n_ema50 else 0.45

    weights = REGIME_WEIGHT_PROFILES.get(regime, DEFAULT_WEIGHTS).copy()
    return {
        "market_regime": regime,
        "component_market_regime": comp_score,
        "weights": weights,
        "india_vix": vix_val,
        "breadth_50ema_pct": breadth_50ema_pct,
        "breadth_200sma_pct": breadth_200sma_pct,
    }


def _find_breakout_resistance(df: pd.DataFrame, price: float, atr_v: float) -> tuple[float, int, int, bool, float]:
    """Detects institutional horizontal resistance level, touches, recency, and 20-day false breakout."""
    lookback = df.iloc[-130:-1] if len(df) > 130 else df.iloc[:-1]
    if lookback.empty:
        return price * 1.02, 1, 10, False, np.nan

    highs = lookback["High"].to_numpy(dtype=float)
    closes = lookback["Close"].to_numpy(dtype=float)
    n = len(highs)

    pivots: list[tuple[int, float]] = []
    for i in range(2, n - 2):
        if highs[i] >= highs[i - 1] and highs[i] >= highs[i - 2] and highs[i] >= highs[i + 1] and highs[i] >= highs[i + 2]:
            pivots.append((i, float(highs[i])))

    h60 = float(np.max(highs[-60:])) if n >= 10 else float(np.max(highs))
    h120 = float(np.max(highs))
    pivots.append((n - 1 - int(np.argmax(highs[-60:][::-1])) if n >= 60 else n - 1, h60))
    pivots.append((n - 1 - int(np.argmax(highs[::-1])), h120))

    zone_tol = max(atr_v * 0.65, price * 0.012)

    best_level = h60
    best_touches = 1
    best_recency = 15
    best_quality = -1.0

    for _, cand in pivots:
        dist_pct = ((cand - price) / cand) * 100.0 if cand > 0 else 99.0
        if dist_pct < -4.0 or dist_pct > 14.0:
            continue
        touch_indices = [idx for idx, h_val in enumerate(highs) if abs(h_val - cand) <= zone_tol]
        clusters: list[int] = []
        for idx in touch_indices:
            if not clusters or (idx - clusters[-1]) >= 4:
                clusters.append(idx)
        touches = max(1, len(clusters))
        recency = int(n - clusters[-1]) if clusters else 30
        prox_bonus = max(0.0, 10.0 - abs(dist_pct))
        quality = (min(touches, 6) * 3.0) + prox_bonus - (0.04 * recency)
        if quality > best_quality:
            best_quality = quality
            best_level = float(cand)
            best_touches = touches
            best_recency = recency

    recent_w = min(20, n)
    recent_highs = highs[-recent_w:]
    recent_closes = closes[-recent_w:]
    pierced = (recent_highs > best_level * 1.004) & (recent_closes < best_level * 0.995)
    if np.any(pierced) and price < best_level:
        last_fb_offset = int(recent_w - np.where(pierced)[0][-1])
        false_bo = True
        false_bo_age = float(last_fb_offset)
    else:
        false_bo = False
        false_bo_age = np.nan

    return best_level, best_touches, best_recency, false_bo, false_bo_age


def _ranking_score(
    score: float,
    distance_pct: float,
    rvol: float,
    ud_vol_ratio: float,
    delivery_pct: float,
    deliv_expansion_ratio: float,
    clv: float,
    is_distribution_trap: bool,
    overhead_wall_trap: bool,
    is_overextended: bool,
    false_breakout: bool,
    market_regime: str,
    nifty_rs: float,
) -> float:
    """Computes final institutional sorting score combining setup score, delivery conviction, and anti-trap penalties."""
    rank_val = float(score)

    if -0.8 <= distance_pct <= 2.2 and clv >= 0.55 and not is_distribution_trap:
        rank_val += 4.5
    elif 2.2 < distance_pct <= 4.0:
        rank_val += 2.0
    elif distance_pct > 7.5:
        rank_val -= 4.0

    if np.isfinite(delivery_pct):
        if delivery_pct >= 55.0 and (rvol >= 1.2 or ud_vol_ratio >= 1.25 or deliv_expansion_ratio >= 1.25):
            rank_val += 4.0
        elif delivery_pct >= 45.0 and deliv_expansion_ratio >= 1.20:
            rank_val += 2.0
        elif delivery_pct < 32.0 and rvol >= 1.4:
            rank_val -= 5.5

    if is_distribution_trap:
        rank_val -= 14.0
    if overhead_wall_trap:
        rank_val -= 8.0
    if is_overextended:
        rank_val -= 10.0
    if false_breakout and distance_pct > 0:
        rank_val -= 6.0

    if market_regime == "Bearish":
        if nifty_rs < 5.0:
            rank_val -= 15.0
        else:
            rank_val -= 5.0

    return round(float(np.clip(rank_val, 0.0, 100.0)), 2)


def score_stock(
    df: pd.DataFrame,
    nifty_df: pd.DataFrame | None = None,
    sector_df: pd.DataFrame | None = None,
    weights: dict[str, float] | None = None,
    delivery_info: dict[str, Any] | None = None,
    market_context: dict[str, Any] | None = None,
) -> dict[str, Any] | None:
    """Evaluates a single stock's OHLCV DataFrame and returns the complete 68-column compatible v3 setup dict."""
    clean = _clean_ohlcv(df)
    if clean is None or len(clean) < 120:
        return None

    close = clean["Close"]
    high = clean["High"]
    low = clean["Low"]
    open_p = clean["Open"]
    vol = clean["Volume"]

    price = float(close.iloc[-1])
    if price <= 0:
        return None

    # Liquidity floor: 20-day median daily traded value >= ₹5 Crore (5e7 INR)
    turnover_20d = (close.tail(20) * vol.tail(20)).median()
    if pd.isna(turnover_20d) or float(turnover_20d) < 50_000_000.0:
        return None

    ema20_s = _ema(close, 20)
    ema50_s = _ema(close, 50)
    sma200_s = close.rolling(200, min_periods=100).mean()

    ema20 = float(ema20_s.iloc[-1])
    ema50 = float(ema50_s.iloc[-1])
    sma200 = float(sma200_s.iloc[-1]) if pd.notna(sma200_s.iloc[-1]) else ema50

    rsi_s = _rsi(close, 14)
    rsi_v = float(rsi_s.iloc[-1])

    macd_line, macd_sig, macd_hist = _macd(close)
    macd_v = float(macd_line.iloc[-1])
    macd_s_v = float(macd_sig.iloc[-1])
    macd_h_v = float(macd_hist.iloc[-1])
    macd_h_prev = float(macd_hist.iloc[-2]) if len(macd_hist) >= 2 else 0.0

    atr_s, adx_s, plus_di_s, minus_di_s = _atr_and_adx(clean, 14)
    atr_v = float(atr_s.iloc[-1]) if pd.notna(atr_s.iloc[-1]) and float(atr_s.iloc[-1]) > 0 else price * 0.02
    atr_pct = (atr_v / price) * 100.0
    atr50 = float(atr_s.tail(50).mean()) if len(atr_s) >= 50 else atr_v
    atr_ratio = atr_v / max(atr50, 1e-9)

    adx_v = float(adx_s.iloc[-1])
    adx_prev3 = float(adx_s.iloc[-4]) if len(adx_s) >= 4 else adx_v
    plus_di = float(plus_di_s.iloc[-1])
    minus_di = float(minus_di_s.iloc[-1])

    avg_vol_20 = float(vol.iloc[-21:-1].mean()) if len(vol) > 21 else float(vol.tail(20).mean())
    today_vol = float(vol.iloc[-1])
    rvol = today_vol / max(avg_vol_20, 1.0)

    recent_20 = clean.tail(20)
    up_days_vol = float(recent_20.loc[recent_20["Close"] >= recent_20["Open"], "Volume"].sum())
    down_days_vol = float(recent_20.loc[recent_20["Close"] < recent_20["Open"], "Volume"].sum())
    ud_vol_ratio = up_days_vol / max(down_days_vol, 1.0) if down_days_vol > 0 else (2.5 if up_days_vol > 0 else 1.0)
    ud_vol_ratio = float(np.clip(ud_vol_ratio, 0.2, 5.0))

    bar_range = max(float(high.iloc[-1] - low.iloc[-1]), 1e-9)
    clv = float(close.iloc[-1] - low.iloc[-1]) / bar_range
    is_red_bar = float(close.iloc[-1]) < float(open_p.iloc[-1])

    high_252 = float(high.tail(252).max())
    pct_below_52w = max(0.0, ((high_252 - price) / max(high_252, 1e-9)) * 100.0)

    breakout_level, res_touches, res_recency, false_bo, false_bo_age = _find_breakout_resistance(clean, price, atr_v)
    breakout_buffer = min(max(0.15 * atr_v, breakout_level * 0.0025), breakout_level * 0.008)
    breakout_trigger = round(breakout_level + breakout_buffer, 2)
    distance_pct = ((breakout_level - price) / max(breakout_level, 1e-9)) * 100.0

    # Weekly Trend Filter & 10-Session Extension Guard (Phase 1 Fix 1.8)
    ret_10d_pct = ((price / float(close.iloc[-11])) - 1.0) * 100.0 if len(close) >= 11 else 0.0
    ema50_slope_20d = ((ema50 / float(ema50_s.iloc[-20])) - 1.0) * 100.0 if len(ema50_s) >= 20 else 0.0
    weekly_bullish = (price > ema50) and (ema50 >= sma200 * 0.98) and (ema50_slope_20d >= -0.5)

    extension_atr = (price - ema20) / max(atr_v, 1e-9)
    is_overextended = bool(extension_atr > 3.2 or ret_10d_pct > 18.0 or rsi_v > 75.0 or distance_pct < -3.5)

    is_distribution_trap = bool(
        (rvol >= 1.25 and is_red_bar and clv < 0.38)
        or (rvol >= 1.50 and clv < 0.28)
        or (ud_vol_ratio < 0.80 and clv < 0.45)
    )
    overhead_wall_trap = bool(pct_below_52w > 22.0 and price < sma200 * 1.02)

    # Pre-Score Delivery Metrics (Phase 1 Fix 1.1 & 1.2)
    dly_pct = np.nan
    dly_qty = np.nan
    dly_exp_ratio = 1.0
    if isinstance(delivery_info, dict) and delivery_info:
        try:
            val_p = float(delivery_info.get("delivery_pct", np.nan))
            if np.isfinite(val_p) and val_p > 0:
                dly_pct = round(val_p, 1)
        except Exception:
            pass
        try:
            val_q = float(delivery_info.get("deliverable_qty", np.nan))
            if np.isfinite(val_q) and val_q > 0:
                dly_qty = val_q
        except Exception:
            pass
        try:
            val_er = float(delivery_info.get("deliv_expansion_ratio", 1.0))
            if np.isfinite(val_er) and val_er > 0:
                dly_exp_ratio = val_er
        except Exception:
            pass

    deliv_to_avgvol_ratio = (dly_qty / max(avg_vol_20, 1.0)) if np.isfinite(dly_qty) else np.nan

    # --- COMPONENT SCORES (0.0 to 1.0) ---
    if is_overextended:
        comp_proximity = 0.15
    elif -1.5 <= distance_pct <= 0.0:
        comp_proximity = 1.00 if (clv >= 0.60 and rvol >= 1.2) else 0.82
    elif 0.0 < distance_pct <= 1.5:
        comp_proximity = 0.96
    elif 1.5 < distance_pct <= 3.0:
        comp_proximity = 0.82
    elif 3.0 < distance_pct <= 5.0:
        comp_proximity = 0.62
    elif 5.0 < distance_pct <= 7.5:
        comp_proximity = 0.40
    elif 7.5 < distance_pct <= 10.0:
        comp_proximity = 0.22
    else:
        comp_proximity = 0.10

    touch_score = min(1.0, res_touches / 4.0) * 0.75
    recency_bonus = 0.25 if 5 <= res_recency <= 45 else (0.15 if res_recency <= 75 else 0.08)
    comp_resistance = float(np.clip(touch_score + recency_bonus - (0.25 if false_bo else 0.0), 0.05, 1.0))

    if is_distribution_trap:
        comp_volume = 0.05
    else:
        rvol_pts = float(np.clip((rvol - 0.6) / 1.4, 0.0, 1.0)) * 0.45
        ud_pts = float(np.clip((ud_vol_ratio - 0.85) / 0.95, 0.0, 1.0)) * 0.35
        clv_pts = (0.20 if clv >= 0.65 else (0.12 if clv >= 0.50 else 0.0))
        vol_base = rvol_pts + ud_pts + clv_pts

        if np.isfinite(dly_pct):
            if dly_pct >= 55.0 and (dly_exp_ratio >= 1.20 or (np.isfinite(deliv_to_avgvol_ratio) and deliv_to_avgvol_ratio >= 0.55)):
                vol_base = min(1.0, vol_base + 0.18)
            elif dly_pct >= 45.0:
                vol_base = min(1.0, vol_base + 0.08)
            elif dly_pct < 32.0 and rvol >= 1.3:
                vol_base = max(0.10, vol_base - 0.22)
        comp_volume = round(float(np.clip(vol_base, 0.05, 1.0)), 3)

    if price > ema20 > ema50 > sma200:
        ema_structure = "Bullish"
        comp_trend = 1.00 if (weekly_bullish and pct_below_52w <= 15.0) else 0.88
    elif price > ema20 and price > ema50:
        ema_structure = "Bullish"
        comp_trend = 0.78 if weekly_bullish else 0.65
    elif price > ema50:
        ema_structure = "Mixed"
        comp_trend = 0.55
    else:
        ema_structure = "Bearish"
        comp_trend = 0.20

    rsi_score = 0.0
    if 56.0 <= rsi_v <= 68.0:
        rsi_score = 0.60
    elif 52.0 <= rsi_v < 56.0 or 68.0 < rsi_v <= 73.0:
        rsi_score = 0.45
    elif 48.0 <= rsi_v < 52.0:
        rsi_score = 0.25
    else:
        rsi_score = 0.10

    macd_score = 0.0
    if macd_v > 0 and macd_v > macd_s_v and macd_h_v > macd_h_prev:
        macd_score = 0.40
    elif macd_v > 0 and (macd_v > macd_s_v or macd_h_v > 0):
        macd_score = 0.28
    elif macd_h_v > macd_h_prev:
        macd_score = 0.15
    comp_momentum = round(float(np.clip(rsi_score + macd_score, 0.05, 1.0)), 3)

    adx_rising = adx_v >= adx_prev3
    di_bullish = plus_di > minus_di
    if not di_bullish:
        comp_adx = 0.20
    elif 20.0 <= adx_v <= 38.0 and adx_rising:
        comp_adx = 0.95
    elif 20.0 <= adx_v <= 45.0:
        comp_adx = 0.80
    elif 16.0 <= adx_v < 20.0 and adx_rising:
        comp_adx = 0.60
    else:
        comp_adx = 0.35

    # Progressive VCP Squeeze & Volume Dry-Up (VDU) (Phase 1 Fix 1.7)
    rng_20 = float((high.tail(20).max() - low.tail(20).min()) / max(price, 1e-9)) * 100.0
    rng_10 = float((high.tail(10).max() - low.tail(10).min()) / max(price, 1e-9)) * 100.0
    rng_5 = float((high.iloc[-6:-1].max() - low.iloc[-6:-1].min()) / max(price, 1e-9)) * 100.0 if len(high) >= 6 else rng_10

    progressive_vcp = (rng_20 > rng_10 >= rng_5 * 0.90) and (rng_10 <= 9.5)
    prior_vols = vol.iloc[-11:-1] if len(vol) >= 11 else vol.iloc[:-1]
    min_3d_vol = float(prior_vols.rolling(3).mean().min()) if len(prior_vols) >= 3 else avg_vol_20
    has_vdu = min_3d_vol <= (0.68 * max(avg_vol_20, 1.0))

    atr_comp_pts = float(np.clip((1.12 - atr_ratio) / 0.38, 0.0, 1.0)) * 0.55
    vcp_pts = 0.28 if progressive_vcp else (0.15 if rng_10 <= 8.0 else 0.0)
    vdu_pts = 0.17 if has_vdu else 0.0
    comp_squeeze = round(float(np.clip(atr_comp_pts + vcp_pts + vdu_pts, 0.10, 1.0)), 3)

    # Multi-Timeframe & True Sector Relative Strength (Phase 1 Fix 1.3)
    ret_60d = ((price / float(close.iloc[-60])) - 1.0) * 100.0 if len(close) >= 60 else ((price / float(close.iloc[0])) - 1.0) * 100.0
    ret_20d = ((price / float(close.iloc[-20])) - 1.0) * 100.0 if len(close) >= 20 else ret_60d

    nifty_rs_60d = 0.0
    nifty_rs_20d = 0.0
    if nifty_df is not None and len(nifty_df) >= 25 and "Close" in nifty_df.columns:
        nc = nifty_df["Close"].dropna()
        if len(nc) >= 60:
            n_ret60 = ((float(nc.iloc[-1]) / float(nc.iloc[-60])) - 1.0) * 100.0
            nifty_rs_60d = ret_60d - n_ret60
        if len(nc) >= 20:
            n_ret20 = ((float(nc.iloc[-1]) / float(nc.iloc[-20])) - 1.0) * 100.0
            nifty_rs_20d = ret_20d - n_ret20

    sector_rs_60d = 0.0
    if sector_df is not None and len(sector_df) >= 25 and "Close" in sector_df.columns:
        sc = sector_df["Close"].dropna()
        if len(sc) >= 60:
            s_ret60 = ((float(sc.iloc[-1]) / float(sc.iloc[-60])) - 1.0) * 100.0
            sector_rs_60d = ret_60d - s_ret60
        elif len(sc) >= 20:
            s_ret20 = ((float(sc.iloc[-1]) / float(sc.iloc[-20])) - 1.0) * 100.0
            sector_rs_60d = ret_20d - s_ret20

    blended_rs = (0.50 * nifty_rs_60d) + (0.25 * nifty_rs_20d) + (0.25 * sector_rs_60d)
    comp_rs = round(float(np.clip((blended_rs + 5.0) / 20.0, 0.05, 1.0)), 3)

    candle_name = _detect_candlestick(clean)
    comp_candle = 1.0 if candle_name != "None" else (0.55 if clv >= 0.70 and not is_red_bar else 0.0)

    ctx = market_context or _evaluate_market_context(nifty_df)
    market_regime = str(ctx.get("market_regime", "Neutral"))
    comp_regime = float(ctx.get("component_market_regime", 0.55))
    active_weights = (weights or ctx.get("weights") or DEFAULT_WEIGHTS).copy()

    raw_score = (
        comp_proximity * active_weights["proximity"]
        + comp_resistance * active_weights["resistance"]
        + comp_volume * active_weights["volume"]
        + comp_trend * active_weights["trend"]
        + comp_momentum * active_weights["momentum"]
        + comp_adx * active_weights["adx"]
        + comp_squeeze * active_weights["squeeze"]
        + comp_rs * active_weights["relative_strength"]
        + comp_candle * active_weights["candle"]
        + comp_regime * active_weights["market_regime"]
    )

    if is_distribution_trap:
        raw_score = min(raw_score, 52.0)
    if is_overextended:
        raw_score = min(raw_score, 58.0)
    if market_regime == "Bearish" and (nifty_rs_60d < 5.0 or ema_structure != "Bullish"):
        raw_score = max(15.0, raw_score - 14.0)

    score = round(float(np.clip(raw_score, 0.0, 100.0)), 2)
    rating = int(np.clip(round(score / 10.0), 1, 10))

    # Non-Inverting Target & Structural Stop-Loss Math (Phase 1 Fix 1.6)
    entry_anchor = max(price, breakout_trigger)
    swing_low_10 = float(low.tail(10).min())
    raw_stop = min(swing_low_10, ema20 - 0.5 * atr_v)
    min_stop_dist = 1.2 * atr_v
    max_stop_dist = 3.0 * atr_v
    stop_dist = float(np.clip(entry_anchor - raw_stop, min_stop_dist, max_stop_dist))
    stop_reference = round(max(0.05, min(price - 0.5 * atr_v, entry_anchor - stop_dist)), 2)

    risk_per_share = max(entry_anchor - stop_reference, 0.5 * atr_v)
    target1 = round(entry_anchor + max(1.6 * atr_v, 1.35 * risk_per_share), 2)
    target2 = round(entry_anchor + max(3.2 * atr_v, 2.60 * risk_per_share), 2)
    target3 = round(target2 + (target2 - target1), 2)

    reward_t2 = max(target2 - entry_anchor, 0.01)
    risk_reward = round(reward_t2 / max(risk_per_share, 0.01), 2)

    if price >= breakout_trigger and not is_distribution_trap and not is_overextended:
        status = "BREAKOUT CONFIRMED"
    elif -0.5 <= distance_pct <= 1.2:
        status = "TESTING RESISTANCE"
    elif 1.2 < distance_pct <= 3.0:
        status = "NEAR BREAKOUT"
    elif 3.0 < distance_pct <= 6.0:
        status = "DEVELOPING"
    else:
        status = "WATCH"

    rank_score = _ranking_score(
        score=score,
        distance_pct=distance_pct,
        rvol=rvol,
        ud_vol_ratio=ud_vol_ratio,
        delivery_pct=dly_pct,
        deliv_expansion_ratio=dly_exp_ratio,
        clv=clv,
        is_distribution_trap=is_distribution_trap,
        overhead_wall_trap=overhead_wall_trap,
        is_overextended=is_overextended,
        false_breakout=false_bo,
        market_regime=market_regime,
        nifty_rs=nifty_rs_60d,
    )

    reasons: list[str] = []
    if distance_pct <= 2.0:
        reasons.append("close to resistance")
    if res_touches >= 3:
        reasons.append(f"{res_touches} resistance touches")
    if ud_vol_ratio >= 1.25:
        reasons.append(f"20D accumulation ({ud_vol_ratio:.2f}x U/D vol)")
    if np.isfinite(dly_pct) and dly_pct >= 50.0:
        reasons.append(f"institutional delivery ({dly_pct:.1f}%, {dly_exp_ratio:.2f}x base)")
    if progressive_vcp or has_vdu:
        reasons.append("VCP contraction + volume dry-up")
    if ema_structure == "Bullish":
        reasons.append("stacked bullish MAs")
    if comp_momentum >= 0.75 and comp_adx >= 0.75:
        reasons.append("strong trend & momentum")
    if nifty_rs_60d > 2.0:
        reasons.append(f"outperforming NIFTY (+{nifty_rs_60d:.1f}%)")
    if sector_rs_60d > 2.0:
        reasons.append(f"sector leader (+{sector_rs_60d:.1f}%)")
    if is_distribution_trap:
        reasons.append("WARNING: high-volume distribution/rejection bar")
    elif false_bo:
        reasons.append("WARNING: recent false-breakout risk")
    elif is_overextended:
        reasons.append("WARNING: extended above 20 EMA / 10D rally")

    reason_str = "; ".join(reasons) if reasons else "developing technical base"
    explanation = (
        f"Technical setup score {score:.1f}/100 ({market_regime} regime). "
        f"{reason_str}. This is a setup-strength ranking, not a guaranteed price prediction."
    )

    return {
        "price": round(price, 2),
        "breakout_level": round(breakout_level, 2),
        "breakout_trigger": breakout_trigger,
        "target1": target1,
        "target2": target2,
        "target3": target3,
        "stop_reference": stop_reference,
        "distance_pct": round(distance_pct, 2),
        "rank_score": rank_score,
        "score": score,
        "rating": rating,
        "status": status,
        "rvol": round(rvol, 2),
        "rsi": round(rsi_v, 2),
        "macd": round(macd_v, 3),
        "adx": round(adx_v, 2),
        "atr_pct": round(atr_pct, 2),
        "atr_ratio": round(atr_ratio, 2),
        "squeeze": comp_squeeze,
        "ema_structure": ema_structure,
        "candlestick": candle_name,
        "resistance_touches": int(res_touches),
        "resistance_recency": int(res_recency),
        "relative_strength": round(ret_60d, 2),
        "nifty_relative_strength": round(nifty_rs_60d, 2),
        "sector_relative_strength": round(sector_rs_60d, 2),
        "market_regime": market_regime,
        "false_breakout": bool(false_bo),
        "false_breakout_age": false_bo_age,
        "risk_reward": risk_reward,
        "component_proximity": round(comp_proximity, 2),
        "component_resistance": round(comp_resistance, 2),
        "component_volume": round(comp_volume, 2),
        "component_trend": round(comp_trend, 2),
        "component_momentum": round(comp_momentum, 2),
        "component_adx": round(comp_adx, 2),
        "component_squeeze": round(comp_squeeze, 2),
        "component_relative_strength": round(comp_rs, 2),
        "component_candle": round(comp_candle, 2),
        "component_market_regime": round(comp_regime, 2),
        "weights": active_weights,
        "explanation": explanation,
        "delivery_pct": dly_pct if np.isfinite(dly_pct) else None,
        "deliverable_qty": int(round(dly_qty)) if np.isfinite(dly_qty) else None,
        "deliv_expansion_ratio": round(dly_exp_ratio, 2),
        "ud_vol_ratio": round(ud_vol_ratio, 2),
        "clv": round(clv, 2),
        "pct_below_52w": round(pct_below_52w, 2),
        "is_distribution_trap": bool(is_distribution_trap),
        "overhead_wall_trap": bool(overhead_wall_trap),
        "is_overextended": bool(is_overextended),
    }


def scan_single(symbol: str, max_distance: float = 10.0, period: str = "2y") -> dict[str, Any] | None:
    """Scans a single NSE ticker with full delivery, NIFTY RS, and sector context."""
    clean_sym = str(symbol).strip().upper().replace(".NS", "")
    hist = fetch_history(clean_sym, period=period)
    if hist is None:
        return None
    nifty_df = fetch_index_history("^NSEI", period=period)
    vix_df = fetch_index_history("^INDIAVIX", period="6mo")
    dly_map = get_delivery_lookup_dict()
    ctx = _evaluate_market_context(nifty_df, vix_df=vix_df)

    row = score_stock(
        hist,
        nifty_df=nifty_df,
        sector_df=None,
        delivery_info=dly_map.get(clean_sym),
        market_context=ctx,
    )
    if row is None:
        return None
    if float(row.get("distance_pct", 99.0)) > float(max_distance):
        return None

    uni = load_universe()
    m = uni.loc[uni["symbol"] == clean_sym]
    row["symbol"] = clean_sym
    row["company_name"] = str(m.iloc[0]["company_name"]) if not m.empty else clean_sym
    row["cap_category"] = str(m.iloc[0]["cap_category"]) if not m.empty else ""
    return row


def scan_universe(
    max_distance: float = 10.0,
    period: str = "2y",
    top_n: int = 500,
    weights: dict[str, float] | None = None,
) -> pd.DataFrame:
    """Downloads NIFTY 500 histories in fast parallel batches, computes Sector RS & Breadth, and scores setups."""
    if yf is None:
        return pd.DataFrame()
    uni = load_universe()
    if uni.empty:
        return pd.DataFrame()

    symbols = uni["symbol"].astype(str).str.strip().str.upper().tolist()
    meta_map = {
        str(r["symbol"]).strip().upper(): (
            str(r.get("company_name", r["symbol"])),
            str(r.get("cap_category", "")),
            str(r.get("industry", "General")),
        )
        for r in uni.to_dict(orient="records")
    }

    delivery_map = get_delivery_lookup_dict()
    nifty_df = fetch_index_history("^NSEI", period=period)
    vix_df = fetch_index_history("^INDIAVIX", period="6mo")

    histories: dict[str, pd.DataFrame] = {}
    chunk_size = 125
    for start_idx in range(0, len(symbols), chunk_size):
        chunk_syms = symbols[start_idx : start_idx + chunk_size]
        tickers = [s.replace("&", "%26") + ".NS" for s in chunk_syms]
        try:
            raw = yf.download(
                tickers,
                period=period,
                interval="1d",
                auto_adjust=True,
                progress=False,
                threads=True,
                group_by="ticker",
                multi_level_index=True,
            )
            if raw is None or raw.empty:
                continue
            for sym, tk in zip(chunk_syms, tickers):
                try:
                    if isinstance(raw.columns, pd.MultiIndex):
                        if tk in raw.columns.get_level_values(0):
                            sub = raw[tk]
                        elif tk in raw.columns.get_level_values(1):
                            sub = raw.xs(tk, axis=1, level=1)
                        else:
                            continue
                    else:
                        sub = raw
                    cleaned = _clean_ohlcv(sub)
                    if cleaned is not None:
                        histories[sym] = cleaned
                except Exception:
                    continue
        except Exception:
            continue

    if not histories:
        return pd.DataFrame()

    # Build In-Memory Equal-Weighted Sector Index Series & Universe Market Breadth (Zero Extra API Calls)
    sector_buckets: dict[str, list[pd.Series]] = {}
    above_50ema = 0
    above_200sma = 0
    breadth_total = 0

    for sym, h_df in histories.items():
        c_ser = h_df["Close"]
        if len(c_ser) >= 50:
            breadth_total += 1
            last_c = float(c_ser.iloc[-1])
            e50 = float(_ema(c_ser, 50).iloc[-1])
            s200 = float(c_ser.rolling(200, min_periods=50).mean().iloc[-1])
            if last_c > e50:
                above_50ema += 1
            if last_c > s200:
                above_200sma += 1

        ind_name = meta_map.get(sym, (sym, "", "General"))[2]
        norm_close = (c_ser / float(c_ser.iloc[0])) * 100.0
        sector_buckets.setdefault(ind_name, []).append(norm_close)

    sector_df_map: dict[str, pd.DataFrame] = {}
    for ind_name, ser_list in sector_buckets.items():
        if len(ser_list) >= 2:
            sec_mean = pd.concat(ser_list, axis=1).mean(axis=1).dropna()
            sector_df_map[ind_name] = pd.DataFrame({"Close": sec_mean})

    b50_pct = (above_50ema / breadth_total * 100.0) if breadth_total > 0 else 55.0
    b200_pct = (above_200sma / breadth_total * 100.0) if breadth_total > 0 else 55.0

    market_ctx = _evaluate_market_context(
        nifty_df=nifty_df,
        vix_df=vix_df,
        breadth_50ema_pct=b50_pct,
        breadth_200sma_pct=b200_pct,
    )

    rows: list[dict[str, Any]] = []
    for sym, h_df in histories.items():
        comp_name, cap_cat, ind_name = meta_map.get(sym, (sym, "", "General"))
        sec_df = sector_df_map.get(ind_name)
        dly_info = delivery_map.get(sym)

        scored = score_stock(
            h_df,
            nifty_df=nifty_df,
            sector_df=sec_df,
            weights=weights,
            delivery_info=dly_info,
            market_context=market_ctx,
        )
        if scored is None:
            continue
        dist = float(scored.get("distance_pct", 99.0))
        if dist > float(max_distance) or dist < -3.5:
            continue

        scored["symbol"] = sym
        scored["company_name"] = comp_name
        scored["cap_category"] = cap_cat
        scored["industry"] = ind_name
        rows.append(scored)

    if not rows:
        return pd.DataFrame()

    out_df = pd.DataFrame(rows)
    out_df = out_df.sort_values(
        ["rank_score", "score", "rating", "distance_pct"],
        ascending=[False, False, False, True],
        kind="stable",
    ).reset_index(drop=True)
    out_df["rank"] = np.arange(1, len(out_df) + 1)

    if top_n and int(top_n) > 0:
        out_df = out_df.head(int(top_n)).reset_index(drop=True)
    return out_df


def optimize_weights(completed_outcomes: pd.DataFrame) -> dict[str, float]:
    """Derives empirical component weights from matured 20-day outcomes (fallback to DEFAULT_WEIGHTS)."""
    if completed_outcomes is None or completed_outcomes.empty or "T1_Before_Stop" not in completed_outcomes.columns:
        return DEFAULT_WEIGHTS.copy()
    comp_map = {
        "proximity": "Component_Proximity",
        "resistance": "Component_Resistance",
        "volume": "Component_Volume",
        "trend": "Component_Trend",
        "momentum": "Component_Momentum",
        "adx": "Component_ADX",
        "squeeze": "Component_Squeeze",
        "relative_strength": "Component_Relative_Strength",
        "candle": "Component_Candle",
        "market_regime": "Component_Market_Regime",
    }
    target = pd.to_numeric(completed_outcomes["T1_Before_Stop"], errors="coerce")
    valid = target.notna()
    if int(valid.sum()) < 40:
        return DEFAULT_WEIGHTS.copy()

    raw_w: dict[str, float] = {}
    for k, col in comp_map.items():
        base_w = DEFAULT_WEIGHTS[k]
        if col in completed_outcomes.columns:
            s = pd.to_numeric(completed_outcomes[col], errors="coerce")
            corr = s[valid].corr(target[valid])
            if pd.notna(corr):
                raw_w[k] = max(2.0, base_w * (1.0 + float(np.clip(corr, -0.35, 0.50))))
            else:
                raw_w[k] = base_w
        else:
            raw_w[k] = base_w
    total = sum(raw_w.values())
    return {k: round((v / total) * 100.0, 2) for k, v in raw_w.items()}
