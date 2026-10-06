"""
scanner.py - NSE breakout scanner: accumulation -> breakout -> new high.

What the score looks at (all thresholds live in CFG below):
  * Price structure : proximity to resistance, base length/depth, volatility
                      contraction, Bollinger squeeze, distance to the 52-week high
  * Accumulation    : volume dry-up in the base, up-vs-down volume, OBV and
                      Accumulation/Distribution at new highs
  * Confirmation    : close above resistance + buffer, volume vs 50-day average
  * Trend           : price vs rising 50/200 SMA, 50 > 200, 10/20 EMA clustering
  * Momentum        : RSI (base range, breakout zone, higher high, divergence),
                      MACD above signal and zero, ADX level and slope
  * Relative strength: vs NIFTY (return + RS line near highs) and vs own industry
  * Market regime   : NIFTY trend, applied as a score multiplier when bearish
  * Fundamentals    : quarterly profit/revenue growth YoY, margins, annual growth,
                      ROE, debt/equity, operating cash flow, PEG (blended into the
                      score or used as a hard filter, only for the shortlist)

Known limits (be honest with yourself when reading results):
  * Backtests use technical data only. Point-in-time fundamentals and sector data
    are not available from yfinance, so they are not part of the backtest.
  * The universe is today's index constituents (survivorship bias in backtests).
  * yfinance statement history for Indian stocks is often only 4-5 quarters, so
    some fundamental checks come back "n/a" instead of pass/fail.
  * Estimate revisions, earnings surprise and promoter pledging are not available
    from yfinance and are not scored.
"""
import io
import json
import os
import re
import time
from datetime import datetime
from zoneinfo import ZoneInfo

import numpy as np
import pandas as pd
import requests
import yfinance as yf

# --------------------------------------------------------------------------- #
# Universe
# --------------------------------------------------------------------------- #
# NIFTY 500 = NIFTY 100 (large) + NIFTY Midcap 150 (mid) + NIFTY Smallcap 250 (small).
NSE_URL = "https://nsearchives.nseindia.com/content/indices/ind_nifty500list.csv"
# Fallbacks if the NIFTY 500 download fails (these have NO small caps).
LARGEMIDCAP_URL = "https://nsearchives.nseindia.com/content/indices/ind_niftylargemidcap250list.csv"
LEGACY_NSE_URL = "https://nsearchives.nseindia.com/content/indices/ind_nifty200list.csv"
UNIVERSE_CACHE = "universe_cache.csv"
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120 Safari/537.36",
    "Accept": "text/csv,text/plain,*/*",
}

# --------------------------------------------------------------------------- #
# Configuration: every threshold used below is here.
# --------------------------------------------------------------------------- #
CFG = {
    # data
    "min_history_bars": 220,
    "drop_partial_bar": True,          # drop today's unfinished daily candle during market hours
    "retry_missing_max": 80,           # individual retries for symbols the batch download missed
    # scan filters
    "max_distance_pct": 10.0,          # max distance below resistance
    "min_distance_pct": -1.0,          # allow up to 1% above resistance (fresh breakouts)
    "max_dist_52w_pct": 15.0,          # skip stocks further than this below the 52-week high (0 = off)
    "trigger_buffer_pct": 0.25,        # close must be this far above resistance to be "confirmed"
    # RSI
    "rsi_base_window": 30,
    "rsi_base_floor": 40,
    "rsi_breakout_low": 55,
    "rsi_strong_high": 75,
    "rsi_extreme": 85,
    # base / structure
    "base_min_days": 20,
    "base_max_depth_pct": 25.0,
    "base_max_scan": 150,
    # volume
    "vol_avg_days": 50,
    "vol_breakout_min": 1.4,
    "vol_breakout_good": 1.5,
    "vol_breakout_strong": 2.0,
    "vol_dryup_days": 10,
    "updown_days": 30,
    # trend / momentum
    "ma_cluster_pct": 1.5,             # |EMA10 - EMA20| / price
    "adx_min": 20,
    "adx_trend": 25,
    # relative strength
    "rs_window": 60,
    "rs_line_window": 120,
    "rs_line_near_high_pct": 3.0,
    "sector_min_members": 4,
    # risk
    "stop_atr_mult": 1.5,
    "max_stop_pct": 8.0,
    "bearish_market_multiplier": 0.75,
    # fundamentals
    "fund_cache_dir": ".fund_cache",
    "fund_cache_days": 7,
    "fund_publish_lag_q_days": 45,     # results are public within ~45 days of quarter end
    "fund_publish_lag_a_days": 90,
    "fund_weight": 0.25,               # share of the final score from fundamentals
    "fund_top_n": 40,                  # only the technical shortlist gets fundamentals
    "fund_profit_strong": 25.0, "fund_profit_min": 20.0,
    "fund_rev_strong": 20.0, "fund_rev_min": 15.0,
    "fund_annual_growth_min": 20.0,
    "fund_roe_min": 15.0,
    "fund_max_debt_equity": 1.0,
    "fund_peg_max": 2.0,
    "fund_min_margin_for_growth": 0.01,  # below this net margin in the base quarter, growth % is flagged
    "fund_min_coverage": 0.40,           # share of fundamental weight that must be evaluable
}

DEFAULT_WEIGHTS = {
    "proximity": 16,
    "new_high": 8,
    "resistance": 8,
    "accumulation": 14,
    "volume": 10,
    "trend": 10,
    "momentum": 10,
    "adx": 4,
    "squeeze": 6,
    "relative_strength": 7,
    "candle": 3,
    "market_regime": 4,
}
assert sum(DEFAULT_WEIGHTS.values()) == 100, "DEFAULT_WEIGHTS must sum to 100"

LAST_RUN = {}  # diagnostics from the most recent download/scan


# --------------------------------------------------------------------------- #
# Universe loading
# --------------------------------------------------------------------------- #
def _load_csv(url):
    r = requests.get(url, headers=HEADERS, timeout=20)
    r.raise_for_status()
    return pd.read_csv(io.StringIO(r.text))


def _parse_universe(df, url, min_rows):
    cols = {c.strip().lower(): c for c in df.columns}
    if "symbol" not in cols:
        raise ValueError(f"No Symbol column in {url}")
    sym = df[cols["symbol"]].astype(str).str.strip()
    name_col = cols.get("company name") or cols.get("company_name")
    ind_col = cols.get("industry")
    out = pd.DataFrame({
        "symbol": sym,
        "company_name": df[name_col].astype(str).str.strip() if name_col else sym,
        "industry": df[ind_col].astype(str).str.strip() if ind_col else "",
    })
    out = out[out.symbol.ne("") & out.symbol.ne("nan")]
    out = out.drop_duplicates("symbol").reset_index(drop=True)
    if len(out) < min_rows:
        raise ValueError(f"Expected at least {min_rows} symbols from {url}, got {len(out)}")
    return out


def load_universe():
    """Official NIFTY 500 (large + mid + small caps). Falls back to LargeMidcap 250, then NIFTY 200,
    then the last cached copy. A fallback means small caps are missing, so a warning is printed."""
    errors = []
    for url, min_rows in ((NSE_URL, 400), (LARGEMIDCAP_URL, 200), (LEGACY_NSE_URL, 150)):
        try:
            out = _parse_universe(_load_csv(url), url, min_rows)
            if url != NSE_URL:
                print(f"WARNING: NIFTY 500 unavailable, using {url} (no small caps). Errors: " + " | ".join(errors))
            try:
                out.to_csv(UNIVERSE_CACHE, index=False)
            except Exception:
                pass
            return out
        except Exception as e:
            errors.append(f"{url}: {e}")
    if os.path.exists(UNIVERSE_CACHE):
        try:
            cached = pd.read_csv(UNIVERSE_CACHE)
            if len(cached) >= 150:  # note: may be a large/mid-only copy if NIFTY 500 never downloaded
                print("WARNING: using cached universe because NSE download failed: " + " | ".join(errors))
                return cached
        except Exception:
            pass
    raise RuntimeError("Could not load NSE constituents: " + " | ".join(errors))


def yf_symbol(symbol):
    # yfinance expects the raw ticker, e.g. "M&M.NS". Do not percent-encode "&".
    return symbol.strip() + ".NS"


# --------------------------------------------------------------------------- #
# Price data
# --------------------------------------------------------------------------- #
def _drop_partial_bar(df):
    """Drop today's candle while the NSE session is still running (or just ended)."""
    if not CFG["drop_partial_bar"] or df is None or df.empty:
        return df
    now = datetime.now(ZoneInfo("Asia/Kolkata"))
    session_live = now.weekday() < 5 and (now.hour * 60 + now.minute) < (15 * 60 + 45)
    if session_live and pd.Timestamp(df.index[-1]).date() == now.date():
        return df.iloc[:-1]
    return df


def _normalize_yf(df):
    if df is None or df.empty:
        return None
    if isinstance(df.columns, pd.MultiIndex):
        if len(df.columns.get_level_values(0).unique()) == 1:
            df.columns = df.columns.get_level_values(-1)
        else:
            df.columns = df.columns.get_level_values(0)
    needed = ["Open", "High", "Low", "Close", "Volume"]
    if not all(c in df.columns for c in needed):
        return None
    df = df[needed].copy().dropna()
    # tz-naive, date-only index so stock / index / sector series align exactly
    df.index = pd.DatetimeIndex(df.index).tz_localize(None).normalize()
    df = df[~df.index.duplicated(keep="last")].sort_index()
    df = _drop_partial_bar(df)
    return df if len(df) >= CFG["min_history_bars"] else None


def fetch_history(symbol, period="2y"):
    try:
        df = yf.download(yf_symbol(symbol), period=period, interval="1d", auto_adjust=True,
                         progress=False, threads=False, group_by="column")
        return _normalize_yf(df)
    except Exception:
        return None


def fetch_histories_batch(symbols, period="2y"):
    """Batch download, then retry whatever is missing one by one. Failures are recorded in LAST_RUN."""
    tickers = [yf_symbol(s) for s in symbols]
    try:
        data = yf.download(tickers, period=period, interval="1d", auto_adjust=True,
                           progress=False, threads=True, group_by="ticker", multi_level_index=True)
    except Exception:
        data = None
    histories = {}
    if data is not None and not data.empty:
        for symbol, ticker in zip(symbols, tickers):
            try:
                if isinstance(data.columns, pd.MultiIndex):
                    first = data.columns.get_level_values(0)
                    second = data.columns.get_level_values(1)
                    if ticker in first:
                        df = data[ticker]
                    elif ticker in second:
                        df = data.xs(ticker, axis=1, level=1)
                    else:
                        continue
                else:
                    df = data
                df = _normalize_yf(df)
                if df is not None:
                    histories[symbol] = df
            except Exception:
                continue
    missing = [s for s in symbols if s not in histories]
    for symbol in missing[: CFG["retry_missing_max"]]:
        df = fetch_history(symbol, period)
        if df is not None:
            histories[symbol] = df
    LAST_RUN["requested"] = len(symbols)
    LAST_RUN["downloaded"] = len(histories)
    LAST_RUN["failed_symbols"] = [s for s in symbols if s not in histories]
    return histories


def fetch_index_history(symbol="^NSEI", period="2y"):
    try:
        return _normalize_yf(yf.download(symbol, period=period, interval="1d", auto_adjust=True,
                                         progress=False, threads=False))
    except Exception:
        return None


# --------------------------------------------------------------------------- #
# Indicators
# --------------------------------------------------------------------------- #
def ema(s, n):
    return s.ewm(span=n, adjust=False).mean()


def rsi(close, n=14):
    """Wilder RSI. Zero average loss gives 100 (not NaN)."""
    delta = close.diff()
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)
    avg_gain = gain.ewm(alpha=1 / n, adjust=False).mean()
    avg_loss = loss.ewm(alpha=1 / n, adjust=False).mean()
    rs = avg_gain / avg_loss.replace(0, np.nan)
    out = 100 - (100 / (1 + rs))
    out = out.where(~((avg_loss == 0) & (avg_gain > 0)), 100.0)
    out = out.where(~((avg_loss == 0) & (avg_gain == 0)), 50.0)
    return out


def macd(close):
    fast, slow = ema(close, 12), ema(close, 26)
    line = fast - slow
    signal = line.ewm(span=9, adjust=False).mean()
    return line, signal, line - signal


def atr(df, n=14):
    prev = df.Close.shift(1)
    tr = pd.concat([df.High - df.Low, (df.High - prev).abs(), (df.Low - prev).abs()], axis=1).max(axis=1)
    return tr.ewm(alpha=1 / n, adjust=False).mean()


def adx(df, n=14):
    up, down = df.High.diff(), -df.Low.diff()
    plus_dm = pd.Series(np.where((up > down) & (up > 0), up, 0.0), index=df.index)
    minus_dm = pd.Series(np.where((down > up) & (down > 0), down, 0.0), index=df.index)
    tr = pd.concat([df.High - df.Low, (df.High - df.Close.shift()).abs(), (df.Low - df.Close.shift()).abs()], axis=1).max(axis=1)
    atr_v = tr.ewm(alpha=1 / n, adjust=False).mean()
    plus_di = 100 * plus_dm.ewm(alpha=1 / n, adjust=False).mean() / atr_v.replace(0, np.nan)
    minus_di = 100 * minus_dm.ewm(alpha=1 / n, adjust=False).mean() / atr_v.replace(0, np.nan)
    dx = 100 * (plus_di - minus_di).abs() / (plus_di + minus_di).replace(0, np.nan)
    return dx.ewm(alpha=1 / n, adjust=False).mean(), plus_di, minus_di


def obv(df):
    direction = np.sign(df.Close.diff().fillna(0))
    return (direction * df.Volume).cumsum()


def ad_line(df):
    rng = (df.High - df.Low).replace(0, np.nan)
    mfm = ((df.Close - df.Low) - (df.High - df.Close)) / rng
    return (mfm.fillna(0) * df.Volume).cumsum()


def bb_width(close, n=20, k=2):
    ma = close.rolling(n).mean()
    return (2 * k * close.rolling(n).std()) / ma


def _safe_float(x, default=0.0):
    try:
        v = float(x)
        return v if np.isfinite(v) else default
    except Exception:
        return default


def _pct_rank(series, value):
    s = series.dropna()
    return 0.5 if s.empty else float((s <= value).mean())


# --------------------------------------------------------------------------- #
# Pattern / structure helpers
# --------------------------------------------------------------------------- #
def candle_pattern(df):
    if len(df) < 3:
        return "None"
    a, b, c = df.iloc[-3], df.iloc[-2], df.iloc[-1]
    body = lambda x: abs(x.Close - x.Open)
    rng = lambda x: max(x.High - x.Low, 1e-9)
    if b.Close < b.Open < c.Close and c.Open <= b.Close and c.Close >= b.Open:
        return "Bullish Engulfing"
    lower = min(c.Open, c.Close) - c.Low
    upper = c.High - max(c.Open, c.Close)
    if lower >= 2 * body(c) and upper <= body(c) * 1.2:
        return "Hammer"
    if c.Close > c.Open and body(c) / rng(c) > 0.75:
        return "Bullish Marubozu"
    if a.Close < a.Open and body(b) < body(a) * .5 and c.Close > c.Open and c.Close > (a.Open + a.Close) / 2:
        return "Morning Star"
    if b.Close < b.Open and c.Close > c.Open and c.Open < b.Low and c.Close > (b.Open + b.Close) / 2:
        return "Piercing Line"
    if all(x.Close > x.Open for x in (a, b, c)) and a.Close < b.Close < c.Close:
        return "Three White Soldiers"
    if c.High < b.High and c.Low > b.Low:
        return "Inside Bar"
    return "None"


def resistance_level(df, lookback=150):
    """Nearest meaningful resistance zone at/above price, using prior bars only."""
    hist = df.iloc[:-1].tail(lookback).copy()
    current = float(df.Close.iloc[-1])
    if len(hist) < 30:
        return np.nan, 0, 999
    h = hist.High.astype(float)
    swing = (h > h.shift(1)) & (h >= h.shift(-1))
    highs = h[swing].dropna()
    if highs.empty:
        return float(h.max()), 1, lookback
    tolerance = 0.0125
    clusters = []
    for level in sorted(highs.tolist()):
        for cluster in clusters:
            center = np.mean(cluster)
            if abs(level - center) / center <= tolerance:
                cluster.append(level)
                break
        else:
            clusters.append([level])
    candidates = []
    for cluster in clusters:
        top = float(max(cluster))
        touches = len(cluster)
        positions = []
        for level in cluster:
            p = np.where(np.isclose(h.values, level, rtol=1e-8, atol=1e-8))[0]
            if len(p):
                positions.append(len(hist) - int(p[-1]))
        recency = min(positions) if positions else lookback
        distance = (top - current) / current * 100
        if distance >= -2:
            strength = touches * 4 + max(0, 4 - recency / 30)
            candidates.append((abs(distance), -strength, top, touches, recency))
    if not candidates:
        return float(h.max()), 1, lookback
    candidates.sort(key=lambda x: (x[0], x[1]))
    _, _, top, touches, recency = candidates[0]
    return top, touches, recency


def detect_base(df, max_depth_pct=None, max_scan=None):
    """Longest window of prior bars (ending yesterday) whose high-low range stays within max depth.
    Returns (length_days, depth_pct, base_low, base_high)."""
    max_depth_pct = CFG["base_max_depth_pct"] if max_depth_pct is None else max_depth_pct
    max_scan = CFG["base_max_scan"] if max_scan is None else max_scan
    prior = df.iloc[:-1]
    hi, lo = prior.High.values, prior.Low.values
    run_hi, run_lo, length, depth = -np.inf, np.inf, 0, np.nan
    for k in range(1, min(max_scan, len(prior)) + 1):
        new_hi, new_lo = max(run_hi, hi[-k]), min(run_lo, lo[-k])
        d = (new_hi - new_lo) / new_hi * 100
        if d > max_depth_pct:
            break
        run_hi, run_lo, length, depth = new_hi, new_lo, k, d
    if length == 0:
        return 0, np.nan, np.nan, np.nan
    return length, float(depth), float(run_lo), float(run_hi)


def contraction_score(df):
    """Each ~10-day window's range should be smaller than the one before it."""
    prior = df.iloc[:-1]
    if len(prior) < 30:
        return 0.25

    def rng(a):
        hi, lo = a.High.max(), a.Low.min()
        return (hi - lo) / hi * 100

    r_new, r_mid, r_old = rng(prior.iloc[-10:]), rng(prior.iloc[-20:-10]), rng(prior.iloc[-30:-20])
    if r_new < r_mid < r_old:
        return 1.0
    if r_new < r_old:
        return 0.65
    return 0.25


def false_breakout_info(df, lookback=40, window=15, tolerance=0.0025):
    """A recent pierce above the prior `lookback`-bar high that closed back under it within 3 bars
    and has not been reclaimed. Returns (flag, age_in_bars)."""
    if len(df) < lookback + window + 5:
        return False, 0
    n = len(df)
    last_close = float(df.Close.iloc[-1])
    for i in range(n - window, n - 1):
        resistance = float(df.High.iloc[i - lookback:i].max())
        if float(df.High.iloc[i]) > resistance * (1 + tolerance):
            for j in range(i + 1, min(i + 4, n)):
                if float(df.Close.iloc[j]) < resistance:
                    if last_close < resistance * (1 + tolerance):
                        return True, (n - 1) - i
                    break
    return False, 0


def relative_strength_vs_index(stock_df, index_df, window=60):
    if index_df is None or len(stock_df) <= window or len(index_df) <= window:
        return 0.0
    a = float(stock_df.Close.iloc[-1] / stock_df.Close.iloc[-window - 1] - 1)
    b = float(index_df.Close.iloc[-1] / index_df.Close.iloc[-window - 1] - 1)
    return (a - b) * 100


def rs_line_info(stock_df, index_df):
    """(is the RS line near its high?, is it rising over ~1 month?)"""
    w = CFG["rs_line_window"]
    if index_df is None:
        return False, False
    common = stock_df.index.intersection(index_df.index)
    if len(common) < w + 25:
        return False, False
    rs = stock_df.Close.loc[common] / index_df.Close.loc[common]
    near = bool(rs.iloc[-1] >= rs.tail(w).max() * (1 - CFG["rs_line_near_high_pct"] / 100))
    return near, bool(rs.iloc[-1] > rs.iloc[-21])


def build_sector_frames(histories, industry_map):
    """Equal-weighted industry index per stock, excluding the stock itself (leave-one-out)."""
    by_ind = {}
    for sym in histories:
        ind = industry_map.get(sym)
        if ind and str(ind) not in ("", "nan"):
            by_ind.setdefault(ind, []).append(sym)
    frames = {}
    for ind, syms in by_ind.items():
        if len(syms) < CFG["sector_min_members"]:
            continue
        cl = pd.concat({s: histories[s].Close.tail(130) for s in syms}, axis=1).ffill().dropna(how="any")
        if len(cl) < 70:
            continue
        norm = cl / cl.iloc[0]
        total, n = norm.sum(axis=1), len(syms)
        for s in syms:
            frames[s] = pd.DataFrame({"Close": (total - norm[s]) / (n - 1)})
    return frames


def _market_regime(index_df):
    if index_df is None or len(index_df) < CFG["min_history_bars"]:
        return 0.5, "Unknown"
    close = index_df.Close
    e20 = ema(close, 20).iloc[-1]
    s50, s200 = close.rolling(50).mean().iloc[-1], close.rolling(200).mean().iloc[-1]
    rsi_v = float(rsi(close).iloc[-1])
    if close.iloc[-1] > e20 > s50 > s200 and rsi_v >= 50:
        return 1.0, "Bullish"
    if close.iloc[-1] < s50 and s50 < s200:
        return 0.2, "Bearish"
    return 0.55, "Neutral"


# --------------------------------------------------------------------------- #
# Component scoring (technical)
# --------------------------------------------------------------------------- #
def _rsi_analysis(close, r):
    """Score RSI the way a breakout trader reads it: held a base range, entering 55-75,
    making a higher high, no bearish divergence. >70 is NOT penalised."""
    cur = _safe_float(r.iloc[-1], 50)
    win = r.iloc[-1 - CFG["rsi_base_window"]:-1].dropna()
    base_floor_ok = bool(len(win) > 10 and win.min() >= CFG["rsi_base_floor"])

    recent = r.iloc[-6:].dropna()
    crossed_60 = bool(len(recent) >= 2 and ((recent.shift(1) < 60) & (recent >= 60)).any())

    prior_peak = r.iloc[-60:-5].max()
    higher_high = bool(np.isfinite(prior_peak) and r.iloc[-5:].max() >= prior_peak)

    diverge = False
    prior_close = close.iloc[-60:-5]
    if len(prior_close) >= 20:
        peak_idx = prior_close.idxmax()
        near_high = close.iloc[-1] >= prior_close.max() * 0.995
        diverge = bool(near_high and cur < _safe_float(r.loc[peak_idx], cur) - 2)

    if cur < 45:
        s = 0.15
    elif cur < CFG["rsi_breakout_low"]:
        s = 0.50
    elif cur <= CFG["rsi_strong_high"]:
        s = 0.85
    elif cur <= CFG["rsi_extreme"]:
        s = 0.65
    else:
        s = 0.45
    if base_floor_ok:
        s += 0.05
    if crossed_60:
        s += 0.07
    if higher_high:
        s += 0.08
    if diverge:
        s -= 0.30
    return float(np.clip(s, 0, 1)), cur, base_floor_ok, crossed_60, higher_high, diverge


def _flow_score(s):
    """OBV / A-D: new 60-day high is best, above a rising 20-day average is decent."""
    last = float(s.iloc[-1])
    if last >= float(s.iloc[-61:-1].max()):
        return 1.0, True
    sma = s.rolling(20).mean()
    if last > sma.iloc[-1] and sma.iloc[-1] > sma.iloc[-6]:
        return 0.6, False
    if last > sma.iloc[-1]:
        return 0.4, False
    return 0.15, False


def component_scores(df, nifty_df=None, sector_df=None):
    if df is None or len(df) < CFG["min_history_bars"]:
        return None
    close, volume = df.Close, df.Volume.replace(0, np.nan)
    price = _safe_float(close.iloc[-1])
    breakout, touches, recency = resistance_level(df)
    if not np.isfinite(breakout) or breakout <= 0 or price <= 0:
        return None
    distance = (breakout - price) / breakout * 100
    breakout_trigger = breakout * (1 + CFG["trigger_buffer_pct"] / 100)

    atr_series = atr(df)
    atr_v = _safe_float(atr_series.iloc[-1])
    atr_pct = atr_v / price * 100 if price else 0
    candle = candle_pattern(df)

    # ---- 52-week high ------------------------------------------------------
    high52 = float(df.High.iloc[:-1].tail(252).max())
    dist52 = (high52 - price) / high52 * 100
    new_high = bool(price > high52)
    nh = (1.0 if dist52 <= 0 else .90 if dist52 <= 2 else .75 if dist52 <= 5 else
          .50 if dist52 <= 10 else .25 if dist52 <= 15 else .05)

    # ---- proximity / resistance -------------------------------------------
    proximity = (1.0 if distance <= 0.5 else .92 if distance <= 1 else .82 if distance <= 2 else
                 .70 if distance <= 3 else .55 if distance <= 5 else .30 if distance <= 8 else
                 .05 if distance <= 10 else 0)
    resistance = min(1.0, touches / 4)
    if recency <= 35:
        resistance = min(1.0, resistance + .10)

    # ---- volume ------------------------------------------------------------
    vol_base = volume.shift(1).rolling(CFG["vol_avg_days"]).mean()   # prior 50 bars, excludes today
    rvol = _safe_float(volume.iloc[-1] / vol_base.iloc[-1], 0)
    up_day = bool(close.iloc[-1] > close.iloc[-2])
    if distance <= 0:   # price is above the level: judge the breakout volume
        volume_s = (1.0 if rvol >= CFG["vol_breakout_strong"] else .85 if rvol >= CFG["vol_breakout_good"] else
                    .70 if rvol >= CFG["vol_breakout_min"] else .40 if rvol >= 1.15 else .10)
    else:               # still building: quiet days are fine, a heavy up day is a bonus, a heavy down day is not
        volume_s = (.85 if (rvol >= CFG["vol_breakout_min"] and up_day) else
                    .30 if rvol >= CFG["vol_breakout_min"] else .50)

    # ---- accumulation ------------------------------------------------------
    base_len, base_depth, base_low, base_high = detect_base(df)
    if base_len >= CFG["base_min_days"]:
        base_s = min(1.0, .5 + (base_len - CFG["base_min_days"]) / 60)
        if base_depth > 15:
            base_s *= .85
    else:
        base_s = base_len / CFG["base_min_days"] * 0.4 if base_len else 0.0

    n_dry = CFG["vol_dryup_days"]
    dry_ratio = _safe_float(volume.iloc[-1 - n_dry:-1].mean() / vol_base.iloc[-1], 1.0)
    dry_s = 1.0 if dry_ratio <= .70 else .80 if dry_ratio <= .85 else .60 if dry_ratio <= 1.0 else .35 if dry_ratio <= 1.2 else .20

    chg = close.diff().tail(CFG["updown_days"])
    vv = df.Volume.tail(CFG["updown_days"])
    up_vol, dn_vol = vv[chg > 0].sum(), vv[chg < 0].sum()
    updown = float(up_vol / dn_vol) if dn_vol > 0 else 3.0
    updown_s = 1.0 if updown >= 1.5 else .80 if updown >= 1.2 else .55 if updown >= 1.0 else .20

    obv_s, obv_high = _flow_score(obv(df))
    ad_s, ad_high = _flow_score(ad_line(df))
    flow_s = (obv_s + ad_s) / 2

    accumulation = .30 * base_s + .20 * dry_s + .25 * updown_s + .25 * flow_s

    # ---- trend (SMA50/SMA200 used consistently) ---------------------------
    e10, e20 = _safe_float(ema(close, 10).iloc[-1]), _safe_float(ema(close, 20).iloc[-1])
    s50_ser, s200_ser = close.rolling(50).mean(), close.rolling(200).mean()
    s50, s200 = _safe_float(s50_ser.iloc[-1]), _safe_float(s200_ser.iloc[-1])
    clustered = abs(e10 - e20) / price * 100 <= CFG["ma_cluster_pct"]
    trend = ((.20 if price > s50 else 0) + (.15 if price > s200 else 0) + (.20 if s50 > s200 else 0) +
             (.15 if s50 > _safe_float(s50_ser.iloc[-11]) else 0) +
             (.15 if s200 > _safe_float(s200_ser.iloc[-21]) else 0) +
             (.10 if clustered else 0) + (.05 if price > e20 else 0))
    ema_structure = "Bullish" if (price > s50 > s200 and price > e20) else "Mixed" if price > s200 else "Bearish"

    # ---- momentum: RSI + MACD ---------------------------------------------
    rsi_series = rsi(close)
    rsi_s, rsi_v, rsi_base_ok, rsi_cross60, rsi_hh, rsi_div = _rsi_analysis(close, rsi_series)
    macd_line, signal, hist = macd(close)
    macd_v, signal_v = _safe_float(macd_line.iloc[-1]), _safe_float(signal.iloc[-1])
    hist_v, hist_prev = _safe_float(hist.iloc[-1]), _safe_float(hist.iloc[-2])
    if macd_v > signal_v and macd_v > 0:
        macd_s = 1.0 if hist_v > hist_prev else .85
    elif macd_v > signal_v:
        macd_s = .60
    elif macd_v > 0:
        macd_s = .35
    else:
        macd_s = .10
    momentum = .6 * rsi_s + .4 * macd_s

    # ---- ADX: level, slope; low ADX is normal while coiling in a base -----
    adx_series, plus_di, minus_di = adx(df)
    adx_v = _safe_float(adx_series.iloc[-1])
    adx_prev = _safe_float(adx_series.iloc[-6], adx_v)
    plus_v, minus_v = _safe_float(plus_di.iloc[-1]), _safe_float(minus_di.iloc[-1])
    if adx_v >= CFG["adx_trend"]:
        adx_s = .80
    elif adx_v >= CFG["adx_min"]:
        adx_s = .60
    else:
        adx_s = .45 if base_len >= CFG["base_min_days"] else .25
    if adx_v > adx_prev:
        adx_s += .15
    if plus_v > minus_v:
        adx_s += .10
    adx_s = min(1.0, adx_s)

    # ---- squeeze: ATR ratio + range contraction + Bollinger squeeze/expansion
    atr50 = _safe_float(atr_series.rolling(50).mean().iloc[-1], atr_v)
    atr_ratio = atr_v / atr50 if atr50 else 1
    atr_s = 1.0 if atr_ratio <= .75 else .85 if atr_ratio <= .85 else .65 if atr_ratio <= .95 else .40 if atr_ratio <= 1.05 else .20
    bw = bb_width(close)
    bw_hist = bw.tail(120)
    bw_now = _safe_float(bw.iloc[-1])
    squeezed_recently = _pct_rank(bw_hist, _safe_float(bw.tail(20).min())) <= .25
    bb_expanding = bool(bw_now > _safe_float(bw.iloc[-6]) * 1.10)
    if squeezed_recently and bb_expanding:
        bb_s = 1.0
    elif squeezed_recently:
        bb_s = .80
    elif _pct_rank(bw_hist, bw_now) <= .35:
        bb_s = .60
    else:
        bb_s = .20
    squeeze = .40 * atr_s + .30 * contraction_score(df) + .30 * bb_s

    # ---- relative strength -------------------------------------------------
    ret60 = _safe_float(close.iloc[-1] / close.iloc[-61] - 1) * 100 if len(close) > 61 else 0
    nifty_rs = relative_strength_vs_index(df, nifty_df, CFG["rs_window"])
    sector_rs = relative_strength_vs_index(df, sector_df, CFG["rs_window"]) if sector_df is not None else 0
    rs_near_high, rs_rising = rs_line_info(df, nifty_df)
    rs_score = (.75 if nifty_rs >= 10 else .60 if nifty_rs >= 5 else .45 if nifty_rs >= 2 else
                .30 if nifty_rs >= 0 else .10)
    if rs_near_high:
        rs_score += .15
    if rs_rising:
        rs_score += .05
    if sector_rs > 5:
        rs_score += .10
    rs_score = min(1.0, rs_score)

    candle_score = {"Bullish Engulfing": 1, "Bullish Marubozu": 1, "Morning Star": 1, "Three White Soldiers": 1,
                    "Hammer": .8, "Piercing Line": .8, "Inside Bar": .6, "None": 0}.get(candle, 0)

    false_breakout, false_breakout_age = false_breakout_info(df)
    market_score, market_label = _market_regime(nifty_df)

    # ---- risk: below the 10-day low / 1.5 ATR, and below the breakout level once above it; capped ----
    stop = min(_safe_float(df.Low.tail(10).min(), price), price - CFG["stop_atr_mult"] * atr_v)
    if price >= breakout:
        stop = min(stop, breakout - 0.5 * atr_v)
    floor = price * (1 - CFG["max_stop_pct"] / 100)
    stop_capped = bool(stop < floor)
    stop = max(stop, floor)
    stop_pct = (price - stop) / price * 100
    ref = max(price, breakout_trigger)          # targets measured from where the move actually starts
    target1 = ref + 1.5 * atr_v
    target2 = ref + 3.0 * atr_v
    risk = max(price - stop, 0.01)
    rr = max(target1 - price, 0) / risk

    return {
        "price": price, "breakout_level": float(breakout), "breakout_trigger": float(breakout_trigger),
        "distance_pct": float(distance), "touches": touches, "recency": recency,
        # component scores (0..1)
        "proximity": proximity, "new_high": nh, "resistance": resistance, "accumulation": accumulation,
        "volume": volume_s, "trend": trend, "momentum": momentum, "adx": adx_s, "squeeze": squeeze,
        "relative_strength": rs_score, "candle": candle_score, "market_regime": market_score,
        # diagnostics
        "market_regime_label": market_label, "rsi_value": rsi_v, "macd_value": macd_v, "adx_value": adx_v, "rvol": rvol,
        "atr": atr_v, "atr_pct": atr_pct, "atr_ratio": atr_ratio, "ema_structure": ema_structure, "candlestick": candle,
        "return_60d": ret60, "nifty_relative_strength": nifty_rs, "sector_relative_strength": sector_rs,
        "rs_line_near_high": rs_near_high,
        "dist_52w_pct": float(dist52), "high_52w": high52, "is_new_52w_high": new_high,
        "base_days": int(base_len), "base_depth_pct": None if not np.isfinite(base_depth) else float(base_depth),
        "volume_dryup_ratio": float(dry_ratio), "up_down_volume": float(updown),
        "obv_new_high": bool(obv_high), "ad_new_high": bool(ad_high),
        "rsi_base_held": rsi_base_ok, "rsi_crossed_60": rsi_cross60, "rsi_higher_high": rsi_hh, "rsi_divergence": rsi_div,
        "bb_squeeze": bool(squeezed_recently), "bb_expanding": bb_expanding,
        "false_breakout": bool(false_breakout), "false_breakout_age": int(false_breakout_age),
        "stop_reference": float(stop), "stop_pct": float(stop_pct), "stop_capped": stop_capped,
        "target1": float(target1), "target2": float(target2), "risk_reward": float(rr),
    }


def score_from_components(c, weights=None):
    w = weights or DEFAULT_WEIGHTS
    total_w = sum(w.values()) or 1
    raw = sum(c.get(k, 0) * w[k] for k in w) / total_w * 100
    if c["false_breakout"]:
        raw -= 10
    if c["market_regime_label"] == "Bearish":
        raw *= CFG["bearish_market_multiplier"]
    return float(np.clip(raw, 0, 100))


def _rating(score):
    # 90-100 = 10, 80-89.99 = 9, ...
    return max(1, min(10, int(score // 10) + 1))


def _status(d):
    tp = CFG["trigger_buffer_pct"]
    return ("BREAKOUT CONFIRMED" if d <= -tp else "AT BREAKOUT LEVEL" if d <= 0 else "VERY NEAR" if d <= 1 else
            "NEAR BREAKOUT" if d <= 3 else "DEVELOPING" if d <= 5 else "WATCH" if d <= 10 else "WEAK")


def _explain(c, score):
    r = []
    if c["distance_pct"] <= 3: r.append("close to resistance")
    if c["is_new_52w_high"]: r.append("new 52-week high")
    elif c["dist_52w_pct"] <= 5: r.append(f"{c['dist_52w_pct']:.1f}% from 52-week high")
    if c["base_days"] >= CFG["base_min_days"]: r.append(f"{c['base_days']}-day base")
    if c["volume_dryup_ratio"] <= .85: r.append("volume dry-up in base")
    if c["up_down_volume"] >= 1.2: r.append("up-volume > down-volume")
    if c["obv_new_high"] or c["ad_new_high"]: r.append("OBV/A-D at new high")
    if c["touches"] >= 3: r.append(f"{c['touches']} resistance touches")
    if c["rvol"] >= CFG["vol_breakout_min"]: r.append(f"volume {c['rvol']:.1f}x 50-day avg")
    if c["ema_structure"] == "Bullish": r.append("bullish MA structure")
    if c["adx_value"] >= CFG["adx_min"] and c["momentum"] >= .6: r.append("positive momentum/trend strength")
    if c["rsi_higher_high"]: r.append("RSI higher high")
    if c["squeeze"] >= .65: r.append("volatility contraction")
    if c["nifty_relative_strength"] > 2: r.append("outperforming NIFTY")
    if c["rs_line_near_high"]: r.append("RS line near high")
    if c["rsi_divergence"]: r.append("WARNING: bearish RSI divergence")
    if c["false_breakout"]: r.append("recent false-breakout risk")
    return (f"Technical setup score {score:.1f}/100. " + ("; ".join(r) if r else "limited confirmation") +
            ". This is a setup-strength ranking, not a guaranteed price prediction.")


def score_stock(df, nifty_df=None, sector_df=None, weights=None):
    c = component_scores(df, nifty_df=nifty_df, sector_df=sector_df)
    if c is None:
        return None
    score = score_from_components(c, weights)
    d = c["distance_pct"]
    return {
        "price": c["price"], "breakout_level": c["breakout_level"], "breakout_trigger": c["breakout_trigger"],
        "distance_pct": d, "score": score, "tech_score": score, "rating": _rating(score), "status": _status(d),
        "rsi": c["rsi_value"], "macd": c["macd_value"], "adx": c["adx_value"], "rvol": c["rvol"],
        "atr_pct": c["atr_pct"], "ema_structure": c["ema_structure"], "candlestick": c["candlestick"],
        "return_60d": c["return_60d"], "relative_strength": c["nifty_relative_strength"],
        "nifty_relative_strength": c["nifty_relative_strength"], "sector_relative_strength": c["sector_relative_strength"],
        "market_regime": c["market_regime_label"],
        "false_breakout": c["false_breakout"], "false_breakout_age": c["false_breakout_age"],
        "resistance_touches": c["touches"], "risk_reward": c["risk_reward"],
        "stop_reference": c["stop_reference"], "stop_pct": c["stop_pct"], "stop_capped": c["stop_capped"],
        "target1": c["target1"], "target2": c["target2"], "squeeze": c["squeeze"],
        "dist_52w_pct": c["dist_52w_pct"], "is_new_52w_high": c["is_new_52w_high"],
        "base_days": c["base_days"], "base_depth_pct": c["base_depth_pct"],
        "volume_dryup_ratio": c["volume_dryup_ratio"], "up_down_volume": c["up_down_volume"],
        "obv_new_high": c["obv_new_high"], "ad_new_high": c["ad_new_high"],
        "rsi_higher_high": c["rsi_higher_high"], "rsi_divergence": c["rsi_divergence"],
        "volume_confirmed": bool(d <= 0 and c["rvol"] >= CFG["vol_breakout_good"]),
        "explanation": _explain(c, score),
    }


def _ranking_score(row):
    """Closeness matters, but a weak stock cannot win just by being 0.5% from the level."""
    proximity = max(0, min(1, 1 - max(row["distance_pct"], 0) / 10))
    setup = row["score"] / 100
    volume = min(1, max(0, row["rvol"] / 2))
    return 100 * (0.45 * proximity + 0.40 * setup + 0.10 * volume + 0.05 * (1 if row["status"] == "BREAKOUT CONFIRMED" else 0))


# --------------------------------------------------------------------------- #
# Fundamentals (shortlist only, cached on disk)
# --------------------------------------------------------------------------- #
_NAMES = {
    "ni": ["Net Income", "Net Income Common Stockholders", "Net Income From Continuing Operation Net Minority Interest"],
    "rev": ["Total Revenue", "Operating Revenue"],
    "op": ["Operating Income", "Total Operating Income As Reported"],
    "eps": ["Diluted EPS", "Basic EPS"],
    "ocf": ["Operating Cash Flow", "Cash Flow From Continuing Operating Activities"],
    "debt": ["Total Debt"],
    "equity": ["Stockholders Equity", "Common Stock Equity", "Total Equity Gross Minority Interest"],
}


def _stmt(t, *attrs):
    for a in attrs:
        try:
            d = getattr(t, a)
            if d is not None and not d.empty:
                return d
        except Exception:
            continue
    return None


def _series_from(df, names):
    if df is None:
        return None
    lower = {str(i).strip().lower(): i for i in df.index}
    for n in names:
        key = lower.get(n.lower())
        if key is None:
            continue
        row = df.loc[key]
        if isinstance(row, pd.DataFrame):
            row = row.iloc[0]
        s = pd.to_numeric(row, errors="coerce").dropna()
        if s.empty:
            continue
        s.index = pd.DatetimeIndex(pd.to_datetime(s.index)).tz_localize(None)
        return s.sort_index(ascending=False)
    return None


def _to_pairs(s):
    return None if s is None else [[d.strftime("%Y-%m-%d"), float(v)] for d, v in s.items()]


def _from_pairs(p):
    if not p:
        return None
    s = pd.Series([v for _, v in p], index=pd.to_datetime([d for d, _ in p]))
    return s.sort_index(ascending=False)


def fetch_fundamentals_raw(symbol, use_cache=True):
    safe = re.sub(r"[^A-Za-z0-9_-]", "_", symbol)
    path = os.path.join(CFG["fund_cache_dir"], f"{safe}.json")
    if use_cache and os.path.exists(path) and time.time() - os.path.getmtime(path) < CFG["fund_cache_days"] * 86400:
        try:
            with open(path) as f:
                return json.load(f)
        except Exception:
            pass
    raw = {}
    try:
        t = yf.Ticker(yf_symbol(symbol))
        q_inc = _stmt(t, "quarterly_income_stmt", "quarterly_financials")
        a_inc = _stmt(t, "income_stmt", "financials")
        q_cf = _stmt(t, "quarterly_cashflow", "quarterly_cash_flow")
        q_bs = _stmt(t, "quarterly_balance_sheet")
        raw["q_ni"] = _to_pairs(_series_from(q_inc, _NAMES["ni"]))
        raw["q_rev"] = _to_pairs(_series_from(q_inc, _NAMES["rev"]))
        raw["q_op"] = _to_pairs(_series_from(q_inc, _NAMES["op"]))
        raw["q_ocf"] = _to_pairs(_series_from(q_cf, _NAMES["ocf"]))
        raw["a_ni"] = _to_pairs(_series_from(a_inc, _NAMES["ni"]))
        raw["a_eps"] = _to_pairs(_series_from(a_inc, _NAMES["eps"]))
        debt, eq = _series_from(q_bs, _NAMES["debt"]), _series_from(q_bs, _NAMES["equity"])
        raw["debt"] = None if debt is None else float(debt.iloc[0])
        raw["equity"] = None if eq is None else float(eq.iloc[0])
        try:
            info = t.info or {}
        except Exception:
            info = {}
        raw["info"] = {k: info.get(k) for k in (
            "returnOnEquity", "earningsQuarterlyGrowth", "revenueGrowth", "trailingPegRatio", "pegRatio",
            "sector", "trailingPE", "heldPercentInstitutions", "heldPercentInsiders")}
    except Exception:
        return {}
    if raw.get("q_ni") or raw.get("q_rev"):
        try:
            os.makedirs(CFG["fund_cache_dir"], exist_ok=True)
            with open(path, "w") as f:
                json.dump(raw, f)
        except Exception:
            pass
    return raw


def _yoy_pct(s, shift=0):
    """Same-quarter-last-year growth for the quarter at position `shift` (0 = latest).
    Returns (pct, state): ok | turnaround | nm | na. Never falls back to QoQ."""
    if s is None or len(s) < shift + 5:
        return np.nan, "na"
    if abs((s.index[shift] - s.index[shift + 4]).days - 365) > 45:
        return np.nan, "na"
    cur, prev = float(s.iloc[shift]), float(s.iloc[shift + 4])
    if prev <= 0:
        return np.nan, ("turnaround" if cur > 0 else "nm")
    return (cur / prev - 1) * 100, "ok"


_FUND_W = {"q_profit": 25, "q_rev": 15, "accel": 8, "margin": 12, "annual": 10, "roe": 8, "de": 7, "ocf": 8, "peg": 7}


def compute_fundamentals(raw, as_of=None):
    """Turn raw statements into checks. Only periods published by `as_of` are used (no look-ahead)."""
    as_of = pd.Timestamp(as_of).normalize() if as_of is not None else pd.Timestamp.today().normalize()
    if not raw:
        return {"fund_status": "INSUFFICIENT", "fund_score": np.nan, "fund_core_pass": False,
                "fund_coverage": 0.0, "fund_notes": "no fundamental data"}

    def pub(key, lag):
        s = _from_pairs(raw.get(key))
        if s is None:
            return None
        s = s[(s.index + pd.Timedelta(days=lag)) <= as_of]
        return s if len(s) else None

    lq, la = CFG["fund_publish_lag_q_days"], CFG["fund_publish_lag_a_days"]
    q_ni, q_rev, q_op, q_ocf = pub("q_ni", lq), pub("q_rev", lq), pub("q_op", lq), pub("q_ocf", lq)
    a_ni, a_eps = pub("a_ni", la), pub("a_eps", la)
    info = raw.get("info") or {}
    notes, vals = [], {}          # vals[check] = 0..1 or None (n/a)

    # --- quarterly profit growth YoY --------------------------------------
    p_pct, p_state = _yoy_pct(q_ni)
    if p_state == "na" and info.get("earningsQuarterlyGrowth") is not None:
        p_pct, p_state = float(info["earningsQuarterlyGrowth"]) * 100, "ok"
        notes.append("profit growth from yfinance info")
    if p_state == "ok":
        v = 1.0 if p_pct >= CFG["fund_profit_strong"] else .8 if p_pct >= CFG["fund_profit_min"] else .4 if p_pct >= 10 else 0.0
        if q_ni is not None and q_rev is not None and len(q_ni) >= 5 and len(q_rev) >= 5:
            base_rev = q_rev.iloc[4]
            if base_rev > 0 and q_ni.iloc[4] < CFG["fund_min_margin_for_growth"] * base_rev:
                v = min(v, .6)
                notes.append("profit growth is off a very small base")
        vals["q_profit"] = v
    elif p_state == "turnaround":
        vals["q_profit"] = .5
        notes.append("turnaround: profit positive vs loss a year ago (growth % not meaningful)")
    elif p_state == "nm":
        vals["q_profit"] = 0.0
        notes.append("loss-making")
    else:
        vals["q_profit"] = None
        notes.append("quarterly profit YoY unavailable")

    # --- quarterly revenue growth YoY -------------------------------------
    r_pct, r_state = _yoy_pct(q_rev)
    if r_state == "na" and info.get("revenueGrowth") is not None:
        r_pct, r_state = float(info["revenueGrowth"]) * 100, "ok"
        notes.append("revenue growth from yfinance info")
    if r_state == "ok":
        vals["q_rev"] = 1.0 if r_pct >= CFG["fund_rev_strong"] else .8 if r_pct >= CFG["fund_rev_min"] else .4 if r_pct >= 8 else 0.0
    else:
        vals["q_rev"] = None
        notes.append("quarterly revenue YoY unavailable")

    # --- earnings acceleration -------------------------------------------
    prev_pct, prev_state = _yoy_pct(q_ni, shift=1)
    if p_state == "ok" and prev_state == "ok" and q_ni is not None and len(q_ni) >= 6:
        vals["accel"] = 1.0 if p_pct > prev_pct else 0.0
    else:
        vals["accel"] = None

    # --- operating margin trend ------------------------------------------
    margin_ok, two_q = None, False
    if q_op is not None and q_rev is not None:
        opm = (q_op / q_rev).dropna().sort_index(ascending=False)
        if len(opm) >= 2:
            ref = opm.iloc[4] if (len(opm) >= 5 and abs((opm.index[0] - opm.index[4]).days - 365) <= 45) else opm.iloc[1]
            margin_ok = bool(opm.iloc[0] >= ref - 0.005)
            two_q = bool(len(opm) >= 3 and opm.iloc[0] >= opm.iloc[1] >= opm.iloc[2])
    vals["margin"] = None if margin_ok is None else (1.0 if (margin_ok and two_q) else .7 if margin_ok else 0.0)

    # --- annual growth consistency (EPS, else net income) -----------------
    ann = a_eps if a_eps is not None and len(a_eps) >= 3 else a_ni
    annual_min = np.nan
    if ann is not None and len(ann) >= 3:
        g = []
        for i in range(min(3, len(ann) - 1)):
            prev = float(ann.iloc[i + 1])
            g.append((float(ann.iloc[i]) / prev - 1) * 100 if prev > 0 else -100.0)
        annual_min = min(g)
        vals["annual"] = sum(x >= CFG["fund_annual_growth_min"] for x in g) / len(g)
    else:
        vals["annual"] = None

    # --- ROE ---------------------------------------------------------------
    roe = info.get("returnOnEquity")
    roe = float(roe) * 100 if roe is not None else np.nan
    if not np.isfinite(roe) and q_ni is not None and len(q_ni) >= 4 and raw.get("equity"):
        roe = float(q_ni.iloc[:4].sum()) / float(raw["equity"]) * 100
    vals["roe"] = None if not np.isfinite(roe) else (1.0 if roe >= CFG["fund_roe_min"] else 0.0)

    # --- debt / equity (not meaningful for banks and NBFCs) --------------
    financial = "financial" in str(info.get("sector") or "").lower()
    de = np.nan
    if raw.get("debt") is not None and raw.get("equity"):
        de = float(raw["debt"]) / float(raw["equity"])
    if financial:
        vals["de"] = None
        notes.append("financial company: debt/equity and margins not scored")
        vals["margin"] = None
        margin_ok = None
    else:
        vals["de"] = None if not np.isfinite(de) else (1.0 if de <= CFG["fund_max_debt_equity"] else 0.0)

    # --- operating cash flow vs profit ------------------------------------
    ocf_ok = None
    if q_ocf is not None and len(q_ocf) >= 4:
        ocf_ttm = float(q_ocf.iloc[:4].sum())
        ni_ttm = float(q_ni.iloc[:4].sum()) if q_ni is not None and len(q_ni) >= 4 else np.nan
        ocf_ok = bool(ocf_ttm > 0 and (not np.isfinite(ni_ttm) or ni_ttm <= 0 or ocf_ttm >= 0.5 * ni_ttm))
    vals["ocf"] = None if ocf_ok is None else (1.0 if ocf_ok else 0.0)

    # --- valuation sanity (PEG) -------------------------------------------
    peg = info.get("trailingPegRatio") or info.get("pegRatio")
    peg = float(peg) if peg is not None else np.nan
    vals["peg"] = None if not np.isfinite(peg) else (1.0 if 0 < peg <= CFG["fund_peg_max"] else 0.0)

    ev = {k: v for k, v in vals.items() if v is not None}
    coverage = sum(_FUND_W[k] for k in ev) / sum(_FUND_W.values())
    score = sum(_FUND_W[k] * v for k, v in ev.items()) / sum(_FUND_W[k] for k in ev) * 100 if ev else np.nan

    core_pass = bool(
        vals["q_profit"] is not None and vals["q_rev"] is not None
        and vals["q_profit"] >= .8 and vals["q_rev"] >= .8
        and margin_ok is not False and ocf_ok is not False and vals["de"] != 0.0
    )
    if coverage < CFG["fund_min_coverage"] or not ev:
        status = "INSUFFICIENT"
    elif core_pass and score >= 70:
        status = "STRONG"
    elif score >= 50:
        status = "OK"
    else:
        status = "WEAK"

    def f(x):
        return None if not np.isfinite(x) else round(float(x), 2)

    return {
        "fund_status": status, "fund_score": f(score), "fund_core_pass": core_pass, "fund_coverage": round(coverage, 2),
        "q_profit_yoy": f(p_pct), "q_revenue_yoy": f(r_pct), "profit_accelerating": vals["accel"] == 1.0 if vals["accel"] is not None else None,
        "margin_expanding": margin_ok, "annual_growth_min": f(annual_min), "roe": f(roe), "debt_equity": f(de),
        "ocf_ok": ocf_ok, "peg": f(peg),
        "inst_holding_pct": f(float(info["heldPercentInstitutions"]) * 100) if info.get("heldPercentInstitutions") is not None else None,
        "insider_holding_pct": f(float(info["heldPercentInsiders"]) * 100) if info.get("heldPercentInsiders") is not None else None,
        "fund_notes": "; ".join(notes),
    }


def fetch_fundamentals(symbol, as_of=None, use_cache=True):
    return compute_fundamentals(fetch_fundamentals_raw(symbol, use_cache=use_cache), as_of=as_of)


def apply_fundamentals(row, fund):
    """Merge fundamentals into a scan row; blend into the score unless data is insufficient."""
    row.update(fund)
    if fund.get("fund_status") != "INSUFFICIENT" and fund.get("fund_score") is not None:
        wf = CFG["fund_weight"]
        row["score"] = (1 - wf) * row["tech_score"] + wf * fund["fund_score"]
        row["rating"] = _rating(row["score"])
    row["rank_score"] = _ranking_score(row)
    tag = f" Fundamentals {fund.get('fund_status')}"
    if fund.get("q_profit_yoy") is not None:
        tag += f" (profit YoY {fund['q_profit_yoy']:.0f}%"
        tag += f", revenue YoY {fund['q_revenue_yoy']:.0f}%)" if fund.get("q_revenue_yoy") is not None else ")"
    row["explanation"] = row["explanation"] + tag + "."
    return row


# --------------------------------------------------------------------------- #
# Scans
# --------------------------------------------------------------------------- #
def scan_universe(max_distance=None, period="2y", top_n=20, use_fundamentals=True, fund_mode="score",
                  fund_top_n=None, as_of=None):
    """fund_mode: 'score' blends fundamentals into the score, 'hard' also drops stocks that fail the
    core fundamental checks or lack data. Diagnostics are attached to result.attrs['report']."""
    max_distance = CFG["max_distance_pct"] if max_distance is None else max_distance
    universe = load_universe()
    industry_map = dict(zip(universe.symbol, universe.industry)) if "industry" in universe else {}
    names = dict(zip(universe.symbol, universe.company_name))
    nifty = fetch_index_history("^NSEI", period=period)
    histories = fetch_histories_batch(universe.symbol.tolist(), period=period)
    sector_frames = build_sector_frames(histories, industry_map)

    rows, errors = [], []
    for symbol, df in histories.items():
        try:
            row = score_stock(df, nifty_df=nifty, sector_df=sector_frames.get(symbol))
        except Exception as e:
            errors.append(f"{symbol}: {e}")
            continue
        if row is None:
            continue
        d = row["distance_pct"]
        if d < CFG["min_distance_pct"] or d > max_distance:
            continue
        if CFG["max_dist_52w_pct"] and row["dist_52w_pct"] > CFG["max_dist_52w_pct"]:
            continue
        row["symbol"] = symbol
        row["company_name"] = names.get(symbol, symbol)
        row["industry"] = industry_map.get(symbol, "")
        row["rank_score"] = _ranking_score(row)
        rows.append(row)

    report = {"universe": len(universe), "downloaded": len(histories), "failed_downloads": LAST_RUN.get("failed_symbols", []),
              "scoring_errors": errors, "candidates": len(rows), "fundamentals_checked": 0,
              "market_regime": rows[0]["market_regime"] if rows else _market_regime(nifty)[1]}
    if not rows:
        out = pd.DataFrame()
        out.attrs["report"] = report
        return out

    rows.sort(key=lambda r: (-r["rank_score"], -r["score"], r["distance_pct"]))
    if use_fundamentals:
        n = fund_top_n or CFG["fund_top_n"]
        shortlist = rows[:max(n, top_n)]
        for row in shortlist:
            try:
                fund = fetch_fundamentals(row["symbol"], as_of=as_of)
            except Exception as e:
                fund = {"fund_status": "INSUFFICIENT", "fund_score": None, "fund_core_pass": False, "fund_notes": str(e)}
            apply_fundamentals(row, fund)
        report["fundamentals_checked"] = len(shortlist)
        rows = shortlist
        if fund_mode == "hard":
            rows = [r for r in rows if r.get("fund_core_pass")]
    result = pd.DataFrame(rows)
    if result.empty:
        result.attrs["report"] = report
        return result
    result = result.sort_values(["rank_score", "score", "distance_pct"], ascending=[False, False, True]).reset_index(drop=True)
    result.insert(0, "rank", np.arange(1, len(result) + 1))
    result = result.head(top_n)
    result.attrs["report"] = report
    return result


def scan_single(symbol, max_distance=None, period="2y", use_fundamentals=False, as_of=None):
    max_distance = CFG["max_distance_pct"] if max_distance is None else max_distance
    df = fetch_history(symbol, period)
    if df is None:
        return None
    nifty = fetch_index_history("^NSEI", period=period)
    row = score_stock(df, nifty_df=nifty)
    if row is None or row["distance_pct"] > max_distance:
        return None
    row["symbol"] = symbol
    row["rank_score"] = _ranking_score(row)
    if use_fundamentals:
        apply_fundamentals(row, fetch_fundamentals(symbol, as_of=as_of))
    return row


def backtest_symbol(symbol, period="5y", min_rating=7, hold_days=10, cooldown=None,
                    round_trip_cost_pct=0.25, stop_pct=5.0, window=500):
    """Technical-only backtest with no look-ahead:
      * index data is cut to the signal date,
      * entry is the NEXT day's open, costs are deducted,
      * signals are spaced by `cooldown` days (default = hold_days) so one setup is not counted many times,
      * results are compared with the average return of ALL days (baseline).
    Fundamentals and sector data are not included (no point-in-time source)."""
    df = fetch_history(symbol, period)
    nifty = fetch_index_history("^NSEI", period=period)
    if df is None:
        return {"summary": {}, "trades": pd.DataFrame()}
    cooldown = hold_days if cooldown is None else cooldown
    trades, next_ok = [], 0
    for i in range(CFG["min_history_bars"], len(df) - hold_days - 1):
        if i < next_ok:
            continue
        hist = df.iloc[max(0, i - window + 1): i + 1]
        nifty_i = nifty.loc[: hist.index[-1]] if nifty is not None else None
        row = score_stock(hist, nifty_df=nifty_i)
        if row is None or row["distance_pct"] < CFG["min_distance_pct"] or row["distance_pct"] > CFG["max_distance_pct"] \
                or row["rating"] < min_rating:
            continue
        future = df.iloc[i + 1: i + 1 + hold_days]
        entry = float(future.Open.iloc[0])
        level = float(row["breakout_level"])
        final = (float(future.Close.iloc[-1]) / entry - 1) * 100 - round_trip_cost_pct
        min_ret = (float(future.Low.min()) / entry - 1) * 100
        stopped = min_ret <= -stop_pct
        trades.append({
            "date": hist.index[-1], "breakout_hit": bool(future.High.max() >= level),
            "final_return_pct": final, "stop_adjusted_return_pct": (-stop_pct - round_trip_cost_pct) if stopped else final,
            "max_return_pct": (float(future.High.max()) / entry - 1) * 100, "min_return_pct": min_ret,
            "rating": row["rating"],
        })
        next_ok = i + cooldown
    t = pd.DataFrame(trades)
    if t.empty:
        return {"summary": {}, "trades": t}
    fwd = (df.Close.shift(-hold_days) / df.Open.shift(-1) - 1) * 100 - round_trip_cost_pct
    baseline = float(fwd.iloc[CFG["min_history_bars"]: len(df) - hold_days - 1].mean())
    return {"summary": {
        "signals": len(t),
        "breakout_hit_rate_pct": t.breakout_hit.mean() * 100,
        "avg_final_return_pct": t.final_return_pct.mean(),
        "median_final_return_pct": t.final_return_pct.median(),
        "avg_stop_adjusted_return_pct": t.stop_adjusted_return_pct.mean(),
        "avg_max_return_pct": t.max_return_pct.mean(),
        "stop_5pct_rate_pct": (t.min_return_pct <= -5).mean() * 100,
        "baseline_avg_return_pct": baseline,
        "edge_vs_baseline_pct": t.final_return_pct.mean() - baseline,
    }, "trades": t}


def optimize_weights(*args, **kwargs):
    # Compatibility hook. Tune weights with walk-forward validation, never on the same data used to pick the model.
    return pd.DataFrame(), DEFAULT_WEIGHTS


if __name__ == "__main__":
    res = scan_universe()
    rep = res.attrs.get("report", {})
    print(f"Universe {rep.get('universe')}, downloaded {rep.get('downloaded')}, "
          f"failed {len(rep.get('failed_downloads', []))}, candidates {rep.get('candidates')}, "
          f"market {rep.get('market_regime')}")
    if res.empty:
        print("No candidates.")
    else:
        cols = [c for c in ["rank", "symbol", "status", "score", "rating", "distance_pct", "dist_52w_pct", "base_days",
                            "rvol", "rsi", "fund_status", "q_profit_yoy", "q_revenue_yoy"] if c in res.columns]
        print(res[cols].round(2).to_string(index=False))
