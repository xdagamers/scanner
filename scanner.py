import io
import math
import requests
import numpy as np
import pandas as pd
import yfinance as yf

# Official NSE NIFTY 500 Universe + Cap Classification Sources
NSE_URL = "https://nsearchives.nseindia.com/content/indices/ind_nifty500list.csv"
NIFTYINDICES_URL = "https://www.niftyindices.com/IndexConstituent/ind_nifty500list.csv"
LEGACY_NSE_URL = "https://nsearchives.nseindia.com/content/indices/ind_nifty200list.csv"
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120 Safari/537.36",
    "Accept": "text/csv,text/plain,*/*",
    "Accept-Language": "en-US,en;q=0.9",
    "Accept-Encoding": "gzip, deflate",
    "Referer": "https://www.nseindia.com/market-data/live-equity-market",
}

DEFAULT_WEIGHTS = {
    "proximity": 16,
    "resistance": 12,
    "volume": 16,
    "trend": 16,
    "momentum": 10,
    "adx": 7,
    "squeeze": 10,
    "relative_strength": 8,
    "candle": 2,
    "market_regime": 3,
}

# Institutional Liquidity Filter: Minimum ₹10 Crore 20-day median daily turnover
MIN_MEDIAN_TURNOVER_INR = 10_00_00_000


def _load_csv(url):
    """Download a CSV with an NSE session warm-up and browser-like headers."""
    with requests.Session() as session:
        session.headers.update(HEADERS)
        try:
            session.get(
                "https://www.nseindia.com/",
                timeout=15,
                allow_redirects=True,
            )
        except Exception:
            pass

        r = session.get(
            url,
            headers={"Referer": "https://www.nseindia.com/"},
            timeout=30,
            allow_redirects=True,
        )
        r.raise_for_status()
        content = r.content.decode("utf-8-sig", errors="replace")
        return pd.read_csv(io.StringIO(content))


def load_universe():
    """Load the official NIFTY 500 universe and classify Large/Mid/Small caps accurately."""
    errors = []

    n500_urls = [
        "https://nsearchives.nseindia.com/content/indices/ind_nifty500list.csv",
        "https://www.niftyindices.com/IndexConstituent/ind_nifty500list.csv",
    ]
    n100_urls = [
        "https://nsearchives.nseindia.com/content/indices/ind_nifty100list.csv",
        "https://www.niftyindices.com/IndexConstituent/ind_nifty100list.csv",
    ]
    nmid_urls = [
        "https://nsearchives.nseindia.com/content/indices/ind_niftymidcap150list.csv",
        "https://www.niftyindices.com/IndexConstituent/ind_niftymidcap150list.csv",
    ]

    df_500 = None
    for url in n500_urls:
        try:
            df_500 = _load_csv(url)
            if df_500 is not None and not df_500.empty:
                break
        except Exception as e:
            errors.append(str(e))

    if df_500 is None or df_500.empty:
        raise RuntimeError("Could not load official NIFTY 500 constituents: " + " | ".join(errors))

    symbol_col = next((c for c in df_500.columns if c.strip().lower() == "symbol"), None)
    if symbol_col is None:
        raise ValueError("No Symbol column in NIFTY 500 CSV")
    name_col = next((c for c in df_500.columns if c.strip().lower() in {"company name", "company_name"}), None)

    out = pd.DataFrame({
        "symbol": df_500[symbol_col].astype(str).str.strip(),
        "company_name": df_500[name_col].astype(str).str.strip() if name_col else df_500[symbol_col].astype(str).str.strip(),
    })
    out = out[out.symbol.ne("") & out.symbol.ne("nan")].drop_duplicates("symbol").reset_index(drop=True)

    large_caps = set()
    for url in n100_urls:
        try:
            df_100 = _load_csv(url)
            sc = next((c for c in df_100.columns if c.strip().lower() == "symbol"), None)
            if sc:
                large_caps = set(df_100[sc].astype(str).str.strip())
                break
        except Exception:
            continue

    mid_caps = set()
    for url in nmid_urls:
        try:
            df_mid = _load_csv(url)
            sc = next((c for c in df_mid.columns if c.strip().lower() == "symbol"), None)
            if sc:
                mid_caps = set(df_mid[sc].astype(str).str.strip())
                break
        except Exception:
            continue

    def classify_symbol(sym):
        if sym in large_caps:
            return "Large Cap"
        if sym in mid_caps:
            return "Mid Cap"
        return "Small Cap"

    out["cap_category"] = out["symbol"].apply(classify_symbol)

    if len(out) < 200:
        raise ValueError(f"Expected a broad market universe, got only {len(out)} symbols")
    return out


def yf_symbol(symbol):
    return symbol.replace("&", "%26") + ".NS"


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
    df = df[~df.index.duplicated(keep="last")].sort_index()
    return df if len(df) >= 220 else None


def fetch_history(symbol, period="2y"):
    try:
        df = yf.download(
            yf_symbol(symbol), period=period, interval="1d", auto_adjust=True,
            progress=False, threads=False, group_by="column"
        )
        return _normalize_yf(df)
    except Exception:
        return None


def fetch_histories_batch(symbols, period="2y"):
    """Batch download the universe to reduce API calls/rate-limit risk."""
    tickers = [yf_symbol(s) for s in symbols]
    try:
        data = yf.download(
            tickers, period=period, interval="1d", auto_adjust=True,
            progress=False, threads=True, group_by="ticker", multi_level_index=True,
        )
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
    if not histories:
        for symbol in symbols:
            df = fetch_history(symbol, period)
            if df is not None:
                histories[symbol] = df
    return histories


def ema(s, n):
    return s.ewm(span=n, adjust=False).mean()


def rsi(close, n=14):
    """Wilder's RSI with explicit behaviour for zero-loss and flat-price windows."""
    delta = close.diff()
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)
    avg_gain = gain.ewm(alpha=1 / n, adjust=False).mean()
    avg_loss = loss.ewm(alpha=1 / n, adjust=False).mean()
    rs = avg_gain / avg_loss.replace(0, np.nan)
    out = 100 - (100 / (1 + rs))
    only_gains = (avg_loss == 0) & (avg_gain > 0)
    no_movement = (avg_loss == 0) & (avg_gain == 0)
    out = out.mask(only_gains, 100.0).mask(no_movement, 50.0)
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


def obv_accumulation(df, window=20):
    """Check if On-Balance Volume (OBV) is trending above its 20-day EMA (institutional accumulation)."""
    if len(df) < window + 5:
        return True
    direction = np.sign(df.Close.diff()).fillna(0.0)
    obv = (direction * df.Volume.fillna(0.0)).cumsum()
    obv_ema = obv.ewm(span=window, adjust=False).mean()
    return bool(obv.iloc[-1] >= obv_ema.iloc[-1])


def pocket_pivot_check(df, lookback=10):
    """O'Neil / Kacher Pocket Pivot: Today is an up-day and today's volume exceeds
    the largest down-day volume over the prior `lookback` sessions.
    """
    if len(df) < lookback + 2:
        return False
    today = df.iloc[-1]
    prev_close = float(df.Close.iloc[-2])
    if float(today.Close) <= prev_close:
        return False
    prior = df.iloc[-lookback - 1:-1]
    prior_diffs = df.Close.diff().iloc[-lookback - 1:-1]
    down_vols = prior.Volume[prior_diffs < 0]
    if down_vols.empty:
        return True
    return bool(float(today.Volume) > float(down_vols.max()))


def candle_pattern(df):
    if len(df) < 3:
        return "None"
    a, b, c = df.iloc[-3], df.iloc[-2], df.iloc[-1]
    body = lambda x: abs(x.Close - x.Open)
    rng = lambda x: max(x.High - x.Low, 1e-9)
    clv_c = (c.Close - c.Low) / rng(c)
    if b.Close < b.Open < c.Close and c.Open <= b.Close and c.Close >= b.Open and clv_c >= 0.65:
        return "Bullish Engulfing"
    lower = min(c.Open, c.Close) - c.Low
    upper = c.High - max(c.Open, c.Close)
    if lower >= 2 * body(c) and upper <= body(c) * 1.0 and clv_c >= 0.60:
        return "Hammer"
    if c.Close > c.Open and body(c) / rng(c) > 0.75:
        return "Bullish Marubozu"
    if a.Close < a.Open and body(b) < body(a) * 0.5 and c.Close > c.Open and c.Close > (a.Open + a.Close) / 2:
        return "Morning Star"
    if b.Close < b.Open and c.Close > c.Open and c.Open < b.Low and c.Close > (b.Open + b.Close) / 2:
        return "Piercing Line"
    if all(x.Close > x.Open for x in (a, b, c)) and a.Close < b.Close < c.Close:
        return "Three White Soldiers"
    if c.High < b.High and c.Low > b.Low:
        return "Inside Bar"
    return "None"


def resistance_level(df, lookback=180):
    """Find a structural resistance ceiling using 5-bar fractal swing highs + 150D/252D highs.
    Prevents locking onto minor bounces trapped underneath major overhead supply.
    """
    hist = df.iloc[:-1].tail(lookback).copy()
    current = float(df.Close.iloc[-1])
    if len(hist) < 40:
        return np.nan, 0, 999
    h = hist.High.astype(float)

    swing5 = (h > h.shift(1)) & (h > h.shift(2)) & (h >= h.shift(-1)) & (h >= h.shift(-2))
    highs = h[swing5].dropna()
    if len(highs) < 2:
        swing3 = (h > h.shift(1)) & (h >= h.shift(-1))
        highs = h[swing3].dropna()
    if highs.empty:
        return float(h.max()), 1, lookback

    tolerance = 0.015
    clusters = []
    for level in sorted(highs.tolist()):
        for cluster in clusters:
            center = np.mean(cluster)
            if abs(level - center) / center <= tolerance:
                cluster.append(level)
                break
        else:
            clusters.append([level])

    major_high_150 = float(h.max())
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
        distance = (top - current) / top * 100

        if -1.5 <= distance <= 12.0:
            overhead_gap_pct = (major_high_150 - top) / top * 100 if top > 0 else 0
            overhead_penalty = 8.0 if (1.8 <= overhead_gap_pct <= 7.0 and touches < 3) else 0.0
            strength = (touches * 5.0) + max(0.0, 5.0 - recency / 25.0) - overhead_penalty
            rank_metric = abs(distance) - (0.35 * min(touches, 5)) + overhead_penalty
            candidates.append((rank_metric, -strength, top, touches, recency))

    if not candidates:
        return major_high_150, 1, lookback
    candidates.sort(key=lambda x: (x[0], x[1]))
    _, _, top, touches, recency = candidates[0]
    return top, touches, recency


def false_breakout_info(df, breakout_lvl=None, lookback=20, tolerance=0.0025):
    """Detect if price pierced the structural breakout level in the last 20 sessions and failed back below it."""
    if len(df) < lookback + 5:
        return False, 0
    recent = df.tail(lookback + 4).copy()

    if breakout_lvl is not None and np.isfinite(breakout_lvl) and breakout_lvl > 0:
        for i in range(len(recent) - 1):
            bar = recent.iloc[i]
            if float(bar.High) > breakout_lvl * (1 + tolerance) and float(bar.Close) < breakout_lvl * 0.995:
                return True, (len(recent) - 1) - i
            if float(bar.Close) > breakout_lvl * (1 + tolerance):
                for j in range(i + 1, min(i + 5, len(recent))):
                    if float(recent.iloc[j].Close) < breakout_lvl * 0.992:
                        return True, (len(recent) - 1) - i

    for i in range(5, len(recent) - 1):
        resistance = float(recent.iloc[:i].High.max())
        bar = recent.iloc[i]
        if float(bar.High) > resistance * (1 + tolerance):
            for j in range(i + 1, min(i + 4, len(recent))):
                if float(recent.iloc[j].Close) < resistance * 0.995:
                    return True, (len(recent) - 1) - i
    return False, 0


def fetch_index_history(symbol="^NSEI", period="2y"):
    try:
        return _normalize_yf(yf.download(symbol, period=period, interval="1d", auto_adjust=True, progress=False, threads=False))
    except Exception:
        return None


def relative_strength_vs_index(stock_df, index_df, window=60):
    """Calculate excess return over a common set of stock/index dates."""
    if index_df is None or stock_df is None or stock_df.empty or index_df.empty:
        return 0.0
    try:
        aligned = pd.concat(
            [stock_df["Close"].rename("stock"), index_df["Close"].rename("index")],
            axis=1,
            join="inner",
        ).dropna().sort_index()
        if len(aligned) <= window:
            return 0.0
        stock_return = float(aligned["stock"].iloc[-1] / aligned["stock"].iloc[-window - 1] - 1)
        index_return = float(aligned["index"].iloc[-1] / aligned["index"].iloc[-window - 1] - 1)
        return (stock_return - index_return) * 100
    except Exception:
        return 0.0


def ibd_weighted_rs_excess(stock_df, index_df):
    """William O'Neil / IBD Weighted Relative Strength Excess Return:
    40% * 3M (63D) + 20% * 6M (126D) + 20% * 9M (189D) + 20% * 12M (252D).
    """
    r63 = relative_strength_vs_index(stock_df, index_df, 63)
    r126 = relative_strength_vs_index(stock_df, index_df, 126)
    r189 = relative_strength_vs_index(stock_df, index_df, min(189, len(stock_df) - 5))
    r252 = relative_strength_vs_index(stock_df, index_df, min(250, len(stock_df) - 5))
    return (0.40 * r63) + (0.20 * r126) + (0.20 * r189) + (0.20 * r252)


def _market_regime(index_df):
    if index_df is None or len(index_df) < 220:
        return 0.5, "Unknown"
    close = index_df.Close
    e20, e50, e200 = ema(close, 20).iloc[-1], ema(close, 50).iloc[-1], close.rolling(200).mean().iloc[-1]
    rsi_v = float(rsi(close).iloc[-1])
    if close.iloc[-1] > e20 > e50 > e200 and rsi_v >= 50:
        return 1.0, "Bullish"
    if close.iloc[-1] < e50 and e50 < e200:
        return 0.2, "Bearish"
    return 0.55, "Neutral"


def _safe_float(x, default=0.0):
    try:
        return float(x) if np.isfinite(float(x)) else default
    except Exception:
        return default


def component_scores(df, nifty_df=None, sector_df=None):
    if len(df) < 220:
        return None
    close, volume = df.Close, df.Volume.replace(0, np.nan)
    price = _safe_float(close.iloc[-1])
    open_p = _safe_float(df.Open.iloc[-1], price)
    high_p = _safe_float(df.High.iloc[-1], price)
    low_p = _safe_float(df.Low.iloc[-1], price)

    # 1. Institutional Liquidity Filter (₹10 Cr median 20D turnover)
    recent_turnover = (close.tail(20) * volume.tail(20)).median()
    if not np.isfinite(recent_turnover) or recent_turnover < MIN_MEDIAN_TURNOVER_INR:
        return None

    breakout, touches, recency = resistance_level(df)
    if not np.isfinite(breakout) or breakout <= 0 or price <= 0:
        return None

    distance = (breakout - price) / breakout * 100
    atr_series = atr(df)
    atr_v = _safe_float(atr_series.iloc[-1])
    atr_pct = atr_v / price * 100 if price else 0

    rsi_series = rsi(close)
    rsi_v = _safe_float(rsi_series.iloc[-1], 50)
    macd_line, signal, hist = macd(close)
    macd_v, signal_v, hist_v, hist_prev = map(_safe_float, [macd_line.iloc[-1], signal.iloc[-1], hist.iloc[-1], hist.iloc[-2]])
    adx_series, plus_di, minus_di = adx(df)
    adx_v, plus_v, minus_v = map(_safe_float, [adx_series.iloc[-1], plus_di.iloc[-1], minus_di.iloc[-1]])

    # Moving Averages for Minervini Stage 2 Trend Template (20 EMA, 50 EMA/SMA, 150 SMA, 200 SMA)
    e20_series, e50_series = ema(close, 20), ema(close, 50)
    e20, e50 = _safe_float(e20_series.iloc[-1]), _safe_float(e50_series.iloc[-1])
    sma50 = _safe_float(close.rolling(50).mean().iloc[-1], e50)
    sma150 = _safe_float(close.rolling(150).mean().iloc[-1], e50)
    sma200_series = close.rolling(200).mean()
    e200 = _safe_float(sma200_series.iloc[-1])
    sma200_22d_ago = _safe_float(sma200_series.iloc[-22], e200) if len(sma200_series) >= 22 else e200

    # 52-Week High / Low Structure (Minervini Rules 6 & 7)
    high_252 = _safe_float(df.High.tail(252).max(), breakout)
    low_252 = _safe_float(df.Low.tail(252).min(), price * 0.7)
    pct_below_52w_high = (high_252 - price) / high_252 * 100 if high_252 > 0 else 0.0
    pct_above_52w_low = (price - low_252) / low_252 * 100 if low_252 > 0 else 0.0

    # 2. Direction-Aware Volume, Pocket Pivots, VDU & OBV Accumulation
    prior_20d_avg_volume = volume.rolling(20, min_periods=15).mean().shift(1).iloc[-1]
    rvol = _safe_float(volume.iloc[-1] / prior_20d_avg_volume, 0) if _safe_float(prior_20d_avg_volume) > 0 else 0.0

    day_range = max(high_p - low_p, 1e-9)
    clv = (price - low_p) / day_range  # Close Location Value (upper 30% close >= 0.70)
    prev_close = _safe_float(close.iloc[-2], price)
    is_bullish_bar = (price >= prev_close) and (clv >= 0.50)
    is_distribution_trap = (rvol >= 1.3) and ((price < open_p and clv < 0.40) or (price < prev_close))

    # 20-Day Up/Down Volume Ratio + OBV Slope + Pocket Pivot + Prior 5-Day Volume Dry-Up (VDU)
    price_diff_20 = close.diff().tail(20)
    vol_20 = volume.tail(20).fillna(0.0)
    up_vol = float(vol_20[price_diff_20 > 0].sum())
    down_vol = float(vol_20[price_diff_20 < 0].sum())
    ud_vol_ratio = (up_vol / down_vol) if down_vol > 0 else (2.0 if up_vol > 0 else 1.0)
    obv_bullish = obv_accumulation(df, 20)
    has_pocket_pivot = pocket_pivot_check(df, 10)
    prior_5d_vdu = bool(volume.iloc[-6:-1].min() <= 0.65 * _safe_float(prior_20d_avg_volume, 1.0)) if len(volume) >= 7 else False

    if is_distribution_trap:
        volume_s = 0.05
    elif is_bullish_bar:
        base_v = 1.0 if rvol >= 2.2 else 0.85 if rvol >= 1.5 else 0.72 if rvol >= 1.25 else 0.55 if rvol >= 1.0 else 0.35
        acc_bonus = (0.12 if ud_vol_ratio >= 1.30 else 0.0) + (0.08 if obv_bullish else -0.10) + (0.08 if has_pocket_pivot else 0.0)
        volume_s = float(np.clip(base_v + acc_bonus, 0.05, 1.0))
    else:
        # Pre-breakout quiet consolidation day: reward Volume Dry-Up (VDU) + strong 20D accumulation
        vdu_bonus = 0.20 if (prior_5d_vdu and distance > 0 and clv >= 0.40) else 0.0
        volume_s = float(np.clip((0.50 if ud_vol_ratio >= 1.30 else 0.30) + vdu_bonus + (0.10 if obv_bullish else -0.10), 0.10, 0.85))

    # 3. Proximity & Resistance Quality
    proximity = 1.0 if -0.5 <= distance <= 0.5 else 0.94 if distance <= 1.2 else 0.85 if distance <= 2.2 else 0.72 if distance <= 3.2 else 0.55 if distance <= 5.0 else 0.30 if distance <= 8.0 else 0.05 if distance <= 10.0 else 0.0
    resistance = min(1.0, touches / 4.0)
    if recency <= 35:
        resistance = min(1.0, resistance + 0.10)
    if pct_below_52w_high <= 10.0:
        resistance = min(1.0, resistance + 0.15)
    elif pct_below_52w_high > 25.0:
        resistance = max(0.05, resistance - 0.30)

    # 4. Minervini 8-Point Stage 2 Trend Template Score
    e20_prev = _safe_float(e20_series.iloc[-6], e20)
    sma200_rising_1m = e200 > sma200_22d_ago
    minervini_stage2 = (
        price > sma50 > sma150 > e200
        and sma200_rising_1m
        and pct_above_52w_low >= 30.0
        and pct_below_52w_high <= 25.0
    )
    trend = (
        (0.20 if price > e20 else 0.0)
        + (0.20 if e20 > e50 else 0.0)
        + (0.20 if sma50 > sma150 > e200 else (0.10 if e50 > e200 else 0.0))
        + (0.15 if sma200_rising_1m else 0.0)
        + (0.15 if (pct_above_52w_low >= 30.0 and pct_below_52w_high <= 25.0) else 0.0)
        + (0.10 if e20 > e20_prev else 0.0)
    )
    extension_atr = (price - e20) / atr_v if atr_v > 0 else 0.0
