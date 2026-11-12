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
    "proximity": 18,
    "resistance": 12,
    "volume": 16,
    "trend": 14,
    "momentum": 10,
    "adx": 8,
    "squeeze": 8,
    "relative_strength": 9,
    "candle": 2,
    "market_regime": 3,
}

# Minimum 20-day median daily traded turnover in Rupees (₹5 Crore) to avoid illiquid operator traps
MIN_MEDIAN_TURNOVER_INR = 5_00_00_000


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
    """Load the official NIFTY 500 universe and classify caps accurately."""
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
    """RSI with explicit behaviour for zero-loss and flat-price windows."""
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

    e20_series, e50_series = ema(close, 20), ema(close, 50)
    e20, e50 = _safe_float(e20_series.iloc[-1]), _safe_float(e50_series.iloc[-1])
    e200_series = close.rolling(200).mean()
    e200 = _safe_float(e200_series.iloc[-1])

    prior_20d_avg_volume = volume.rolling(20, min_periods=15).mean().shift(1).iloc[-1]
    rvol = _safe_float(volume.iloc[-1] / prior_20d_avg_volume, 0) if _safe_float(prior_20d_avg_volume) > 0 else 0.0

    day_range = max(high_p - low_p, 1e-9)
    clv = (price - low_p) / day_range 
    prev_close = _safe_float(close.iloc[-2], price)
    is_bullish_bar = (price >= prev_close) and (clv >= 0.45)
    is_distribution_trap = (rvol >= 1.3) and ((price < open_p and clv < 0.40) or (price < prev_close))

    price_diff_20 = close.diff().tail(20)
    vol_20 = volume.tail(20).fillna(0.0)
    up_vol = float(vol_20[price_diff_20 > 0].sum())
    down_vol = float(vol_20[price_diff_20 < 0].sum())
    ud_vol_ratio = (up_vol / down_vol) if down_vol > 0 else (2.0 if up_vol > 0 else 1.0)

    if is_distribution_trap:
        volume_s = 0.05
    elif is_bullish_bar:
        base_v = 1.0 if rvol >= 2.2 else 0.85 if rvol >= 1.6 else 0.70 if rvol >= 1.3 else 0.50 if rvol >= 1.05 else 0.30
        acc_bonus = 0.15 if ud_vol_ratio >= 1.35 else (0.05 if ud_vol_ratio >= 1.1 else -0.15)
        volume_s = float(np.clip(base_v + acc_bonus, 0.05, 1.0))
    else:
        volume_s = 0.55 if ud_vol_ratio >= 1.4 else 0.35 if ud_vol_ratio >= 1.1 else 0.15

    high_252 = _safe_float(df.High.tail(252).max(), breakout)
    pct_below_52w = (high_252 - price) / high_252 * 100 if high_252 > 0 else 0.0

    proximity = 1.0 if -0.5 <= distance <= 0.5 else 0.92 if distance <= 1.2 else 0.82 if distance <= 2.2 else 0.70 if distance <= 3.2 else 0.55 if distance <= 5.0 else 0.30 if distance <= 8.0 else 0.05 if distance <= 10.0 else 0.0
    resistance = min(1.0, touches / 4.0)
    if recency <= 35:
        resistance = min(1.0, resistance + 0.10)
    if pct_below_52w <= 5.0:
        resistance = min(1.0, resistance + 0.15)
    elif pct_below_52w > 25.0:
        resistance = max(0.1, resistance - 0.25)

    e20_prev = _safe_float(e20_series.iloc[-6], e20)
    e50_prev = _safe_float(e50_series.iloc[-11], e50)
    trend = (
        (0.25 if price > e20 else 0.0)
        + (0.25 if e20 > e50 else 0.0)
        + (0.25 if e50 > e200 else 0.0)
        + (0.15 if e20 > e20_prev else 0.0)
        + (0.10 if e50 > e50_prev else 0.0)
    )
    extension_atr = (price - e20) / atr_v if atr_v > 0 else 0.0
    is_overextended = extension_atr > 3.5 or distance < -2.5

    momentum = 0.80 if 54 <= rsi_v <= 70 else 0.55 if (50 <= rsi_v < 54 or 70 < rsi_v <= 75) else 0.20
    if rsi_v > _safe_float(rsi_series.iloc[-3], rsi_v) and rsi_v <= 73:
        momentum = min(1.0, momentum + 0.10)
    if macd_v > signal_v and hist_v > hist_prev:
        momentum = min(1.0, momentum + 0.10)
    if clv < 0.35:
        momentum = max(0.10, momentum - 0.25)

    adx_prev = _safe_float(adx_series.iloc[-4], adx_v)
    adx_s = 0.15 if adx_v < 15 else 0.35 if adx_v < 20 else 0.60 if adx_v < 25 else 0.80 if adx_v < 35 else 0.90
    if plus_v > minus_v:
        adx_s = min(1.0, adx_s + 0.10)
    if adx_v > adx_prev and plus_v > minus_v:
        adx_s = min(1.0, adx_s + 0.05)

    atr50 = _safe_float(atr_series.rolling(50).mean().iloc[-1], atr_v)
    atr_ratio = atr_v / atr50 if atr50 else 1.0
    prior_10d_range_pct = (df.High.iloc[-11:-1].max() - df.Low.iloc[-11:-1].min()) / price * 100 if len(df) >= 12 and price > 0 else 10.0
    squeeze = 1.0 if atr_ratio <= 0.75 else 0.85 if atr_ratio <= 0.85 else 0.65 if atr_ratio <= 0.95 else 0.40 if atr_ratio <= 1.05 else 0.20
    if prior_10d_range_pct <= 6.0:
        squeeze = min(1.0, squeeze + 0.15)

    ret60 = _safe_float(close.iloc[-1] / close.iloc[-61] - 1) * 100 if len(close) > 61 else 0.0
    rs_20 = relative_strength_vs_index(df, nifty_df, 20)
    rs_60 = relative_strength_vs_index(df, nifty_df, 60)
    rs_120 = relative_strength_vs_index(df, nifty_df, 120)
    blended_rs = (0.40 * rs_20) + (0.35 * rs_60) + (0.25 * rs_120)
    sector_rs = relative_strength_vs_index(df, sector_df, 60) if sector_df is not None else 0.0

    rs_score = 0.0
    if blended_rs >= 10 and rs_20 > 0:
        rs_score = 0.95
    elif blended_rs >= 5 and rs_20 >= 0:
        rs_score = 0.78
    elif blended_rs >= 2:
        rs_score = 0.60
    elif blended_rs >= 0:
        rs_score = 0.35
    if sector_rs > 5:
        rs_score = min(1.0, rs_score + 0.15)

    candle = candle_pattern(df)
    candle_score = {
        "Bullish Engulfing": 1.0, "Bullish Marubozu": 1.0, "Morning Star": 1.0,
        "Three White Soldiers": 1.0, "Hammer": 0.8, "Piercing Line": 0.8,
        "Inside Bar": 0.2, "None": 0.0
    }.get(candle, 0.0)

    false_breakout, false_breakout_age = false_breakout_info(df, breakout_lvl=breakout)
    market_score, market_label = _market_regime(nifty_df)

    overhead_wall_trap = (pct_below_52w > 22.0) or (
        (high_252 - breakout) / breakout * 100 > 2.0 and (high_252 - breakout) / breakout * 100 <= 6.5 and touches < 3
    )

    breakout_trigger = breakout * 1.0025
    recent_low = _safe_float(df.Low.tail(10).min(), price)
    stop = min(recent_low, price - 1.5 * atr_v)
    if stop >= price:
        stop = price - 1.5 * atr_v
    target1 = breakout_trigger + 1.5 * atr_v
    target2 = breakout_trigger + 3.0 * atr_v
    risk = max(price - stop, 0.01)
    reward = max(target1 - price, 0)
    rr = reward / risk

    return {
        "price": price, "breakout_level": float(breakout), "breakout_trigger": float(breakout_trigger), "distance_pct": float(distance),
        "touches": touches, "recency": recency, "proximity": proximity, "resistance": resistance, "volume": volume_s,
        "trend": trend, "momentum": momentum, "adx": min(1.0, adx_s), "squeeze": squeeze, "relative_strength": rs_score, "candle": candle_score,
        "market_regime": market_score, "market_regime_label": market_label, "rsi_value": rsi_v, "macd_value": macd_v, "adx_value": adx_v, "rvol": rvol,
        "atr": atr_v, "atr_pct": atr_pct, "atr_ratio": atr_ratio,
        "ema_structure": ("Bullish" if price > e20 > e50 > e200 else "Mixed" if price > e200 else "Bearish"),
        "candlestick": candle, "relative_strength_60": ret60, "nifty_relative_strength": rs_60, "sector_relative_strength": sector_rs,
        "false_breakout": bool(false_breakout), "false_breakout_age": int(false_breakout_age), "stop_reference": float(stop),
        "target1": float(target1), "target2": float(target2), "risk_reward": float(rr),
        "is_distribution_trap": bool(is_distribution_trap), "is_overextended": bool(is_overextended),
        "overhead_wall_trap": bool(overhead_wall_trap), "ud_vol_ratio": float(ud_vol_ratio), "clv": float(clv),
        "pct_below_52w": float(pct_below_52w),
    }


def score_from_components(c, weights=None):
    weights = weights or DEFAULT_WEIGHTS
    raw = sum(c[k] * weights[k] for k in weights)
    # Institutional Anti-Trap Penalties
    if c.get("false_breakout"):
        raw -= 15.0  
    if c.get("is_distribution_trap"):
        raw -= 12.0  
    if c.get("is_overextended"):
        raw -= 10.0  
    if c.get("overhead_wall_trap"):
        raw -= 8.0   
    if c.get("ema_structure") == "Bearish":
        raw -= 12.0  
    return float(np.clip(raw, 0, 100))


def _rating(score):
    return max(1, min(10, int(score // 10) + 1))


def score_stock(df, nifty_df=None, sector_df=None, weights=None):
    c = component_scores(df, nifty_df=nifty_df, sector_df=sector_df)
    if c is None:
        return None
    score = score_from_components(c, weights)
    rating = _rating(score)
    d = c["distance_pct"]
    trigger_confirmed = (float(c["price"]) >= float(c["breakout_trigger"])) and (c.get("clv", 0.5) >= 0.50)
    status = (
        "BREAKOUT CONFIRMED" if trigger_confirmed
        else "TESTING RESISTANCE" if d < 0
        else "VERY NEAR" if d <= 1
        else "NEAR BREAKOUT" if d <= 3
        else "DEVELOPING" if d <= 5
        else "WATCH" if d <= 10
        else "WEAK"
    )
    reasons = []
    if d <= 3:
        reasons.append("close to resistance")
    if c["touches"] >= 3:
        reasons.append(f"{c['touches']} resistance touches")
    if c["rvol"] >= 1.4 and not c.get("is_distribution_trap"):
        reasons.append("price-confirmed volume expansion")
    if c.get("ud_vol_ratio", 1.0) >= 1.3:
        reasons.append(f"20D accumulation ({c['ud_vol_ratio']:.2f}x U/D vol)")
    if c["ema_structure"] == "Bullish":
        reasons.append("stacked bullish MAs")
    if c["adx_value"] >= 20 and c["momentum"] >= 0.6:
        reasons.append("strong trend & momentum")
    if c["squeeze"] >= 0.65:
        reasons.append("VCP volatility contraction")
    if c["nifty_relative_strength"] > 2:
        reasons.append("outperforming NIFTY")
    if c["false_breakout"]:
        reasons.append("WARNING: recent false-breakout risk")
    if c.get("is_distribution_trap"):
        reasons.append("WARNING: high-volume rejection bar")

    explanation = (
        f"Technical setup score {score:.1f}/100. "
        + ("; ".join(reasons) if reasons else "limited confirmation")
        + ". This is a setup-strength ranking, not a guaranteed price prediction."
    )
    return {
        "price": c["price"], "breakout_level": c["breakout_level"], "breakout_trigger": c["breakout_trigger"], "distance_pct": c["distance_pct"],
        "score": score, "score_components_raw": float(sum(c[k] * (weights or DEFAULT_WEIGHTS)[k] for k in (weights or DEFAULT_WEIGHTS))),
        "rating": rating, "status": status, "rsi": c["rsi_value"], "macd": c["macd_value"], "adx": c["adx_value"], "rvol": c["rvol"],
        "atr_pct": c["atr_pct"], "atr_ratio": c["atr_ratio"], "ema_structure": c["ema_structure"], "candlestick": c["candlestick"],
        "relative_strength": c["relative_strength_60"], "nifty_relative_strength": c["nifty_relative_strength"],
        "sector_relative_strength": c["sector_relative_strength"], "market_regime": c["market_regime_label"],
        "false_breakout": c["false_breakout"], "false_breakout_age": c["false_breakout_age"],
        "resistance_touches": c["touches"], "resistance_recency": c["recency"],
        "risk_reward": c["risk_reward"], "stop_reference": c["stop_reference"], "target1": c["target1"], "target2": c["target2"],
        "target3": float(c["target2"] + (c["target2"] - c["target1"])),
        "squeeze": c["squeeze"], "component_proximity": c["proximity"], "component_resistance": c["resistance"], "component_volume": c["volume"],
        "component_trend": c["trend"], "component_momentum": c["momentum"], "component_adx": c["adx"], "component_squeeze": c["squeeze"],
        "component_relative_strength": c["relative_strength"], "component_candle": c["candle"], "component_market_regime": c["market_regime"],
        "weights": dict(weights or DEFAULT_WEIGHTS), "explanation": explanation,
        "ud_vol_ratio": float(c.get("ud_vol_ratio", 1.0)),
        "clv": float(c.get("clv", 0.5)),
        "pct_below_52w": float(c.get("pct_below_52w", 0.0)),
        "is_distribution_trap": bool(c.get("is_distribution_trap", False)),
        "overhead_wall_trap": bool(c.get("overhead_wall_trap", False)),
        "is_overextended": bool(c.get("is_overextended", False)),
    }


def _ranking_score(row):
    d = float(row["distance_pct"])
    if -0.5 <= d <= 2.0:
        proximity = 1.0
    elif d < -0.5:
        proximity = max(0.0, 1.0 - abs(d + 0.5) / 4.0)
    else:
        proximity = max(0.0, 1.0 - (d - 2.0) / 8.0)

    setup = float(row["score"]) / 100.0
    vol_component = float(row.get("component_volume", 0.5))
    confirmed_bonus = 1.0 if row["status"] == "BREAKOUT CONFIRMED" else 0.0
    return 100.0 * (0.55 * setup + 0.25 * proximity + 0.15 * vol_component + 0.05 * confirmed_bonus)


def scan_universe(max_distance=10.0, period="2y", top_n=20):
    universe = load_universe()
    nifty = fetch_index_history("^NSEI", period=period)
    histories = fetch_histories_batch(universe.symbol.tolist(), period=period)
    rows = []
    for symbol, df in histories.items():
        row = score_stock(df, nifty_df=nifty)
        if row is None:
            continue
        if row["distance_pct"] < -1.5 or row["distance_pct"] > max_distance:
            continue
        row["symbol"] = symbol
        match = universe.loc[universe.symbol == symbol, "company_name"]
        cap_match = universe.loc[universe.symbol == symbol, "cap_category"] if "cap_category" in universe.columns else pd.Series(dtype=object)
        row["company_name"] = match.iloc[0] if not match.empty else symbol
        row["cap_category"] = cap_match.iloc[0] if not cap_match.empty else ""
        row["rank_score"] = _ranking_score(row)
        rows.append(row)
    if not rows:
        return pd.DataFrame()
    result = pd.DataFrame(rows)
    result = result.sort_values(["rank_score", "score", "distance_pct"], ascending=[False, False, True]).reset_index(drop=True)
    result.insert(0, "rank", np.arange(1, len(result) + 1))
    return result.head(top_n)


def scan_single(symbol, max_distance=10.0, period="2y"):
    df = fetch_history(symbol, period)
    if df is None:
        return None
    nifty = fetch_index_history("^NSEI", period=period)
    row = score_stock(df, nifty_df=nifty)
    if row is None or row["distance_pct"] < -1.5 or row["distance_pct"] > max_distance:
        return None
    row["symbol"] = symbol
    row["rank_score"] = _ranking_score(row)
    return row


def backtest_symbol(symbol, period="5y", min_rating=7, hold_days=10):
    df = fetch_history(symbol, period)
    nifty = fetch_index_history("^NSEI", period=period)
    if df is None:
        return {"summary": {}, "trades": pd.DataFrame()}
    trades = []
    for i in range(220, len(df) - hold_days):
        hist = df.iloc[:i + 1]
        signal_date = hist.index[-1]
        if nifty is not None and not nifty.empty:
            nifty_asof = nifty.loc[nifty.index <= signal_date]
        else:
            nifty_asof = nifty
        row = score_stock(hist, nifty_df=nifty_asof)
        if row is None or row["distance_pct"] < -1.5 or row["distance_pct"] > 10 or row["rating"] < min_rating:
            continue
        future = df.iloc[i + 1:i + 1 + hold_days]
        if future.empty:
            continue
        entry = float(future.Open.iloc[0])
        if not np.isfinite(entry) or entry <= 0:
            continue
        final_close = float(future.Close.iloc[-1])
        max_high = float(future.High.max())
        min_low = float(future.Low.min())
        trigger = float(row.get("breakout_trigger", row["breakout_level"]))
        level = float(row["breakout_level"])
        trades.append({
            "date": signal_date,
            "entry_date": future.index[0],
            "entry_price": entry,
            "breakout_hit": bool(max_high >= trigger),
            "breakout_level": level,
            "breakout_trigger": trigger,
            "final_return_pct": (final_close / entry - 1) * 100,
            "max_return_pct": (max_high / entry - 1) * 100,
            "min_return_pct": (min_low / entry - 1) * 100,
            "rating": row["rating"],
        })
    t = pd.DataFrame(trades)
    if t.empty:
        return {"summary": {}, "trades": t}
    return {"summary": {
        "signals": len(t),
        "breakout_hit_rate_pct": t.breakout_hit.mean() * 100,
        "avg_final_return_pct": t.final_return_pct.mean(),
        "median_final_return_pct": t.final_return_pct.median(),
        "avg_max_return_pct": t.max_return_pct.mean(),
        "stop_5pct_rate_pct": (t.min_return_pct <= -5).mean() * 100,
    }, "trades": t}


def optimize_weights(*args, **kwargs):
    return pd.DataFrame(), DEFAULT_WEIGHTS
