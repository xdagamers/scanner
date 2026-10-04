import io
import math
import requests
import numpy as np
import pandas as pd
import yfinance as yf

# NIFTY LargeMidcap 250 = NIFTY 100 + NIFTY Midcap 150.
# This is the official NSE "top 250" broad large+mid-cap universe.
NSE_URL = "https://nsearchives.nseindia.com/content/indices/ind_niftylargemidcap250list.csv"
LEGACY_NSE_URL = "https://nsearchives.nseindia.com/content/indices/ind_nifty200list.csv"
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120 Safari/537.36",
    "Accept": "text/csv,text/plain,*/*",
}

DEFAULT_WEIGHTS = {
    "proximity": 20,
    "resistance": 12,
    "volume": 14,
    "trend": 12,
    "momentum": 10,
    "adx": 8,
    "squeeze": 8,
    "relative_strength": 7,
    "candle": 4,
    "market_regime": 5,
}


def _load_csv(url):
    r = requests.get(url, headers=HEADERS, timeout=20)
    r.raise_for_status()
    return pd.read_csv(io.StringIO(r.text))


def load_universe():
    """Load the official NSE NIFTY LargeMidcap 250 universe."""
    errors = []
    for url in (NSE_URL,):
        try:
            df = _load_csv(url)
            symbol_col = next((c for c in df.columns if c.strip().lower() == "symbol"), None)
            if symbol_col is None:
                raise ValueError(f"No Symbol column in {url}")
            name_col = next((c for c in df.columns if c.strip().lower() in {"company name", "company_name"}), None)
            out = pd.DataFrame({
                "symbol": df[symbol_col].astype(str).str.strip(),
                "company_name": df[name_col].astype(str).str.strip() if name_col else df[symbol_col].astype(str).str.strip(),
            })
            out = out[out.symbol.ne("") & out.symbol.ne("nan")]
            out = out.drop_duplicates("symbol").reset_index(drop=True)
            if len(out) < 200:
                raise ValueError(f"Expected a large+midcap universe, got only {len(out)} symbols")
            return out
        except Exception as e:
            errors.append(str(e))
    raise RuntimeError("Could not load official NIFTY LargeMidcap 250 constituents: " + " | ".join(errors))


def yf_symbol(symbol):
    return symbol.replace("&", "%26") + ".NS"


def _normalize_yf(df):
    if df is None or df.empty:
        return None
    if isinstance(df.columns, pd.MultiIndex):
        # For a single ticker download, yfinance may still return a MultiIndex.
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
        df = yf.download(yf_symbol(symbol), period=period, interval="1d", auto_adjust=True,
                         progress=False, threads=False, group_by="column")
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
    # If a batch request failed completely, fall back to individual downloads.
    if not histories:
        for symbol in symbols:
            df = fetch_history(symbol, period)
            if df is not None:
                histories[symbol] = df
    return histories


def ema(s, n):
    return s.ewm(span=n, adjust=False).mean()


def rsi(close, n=14):
    delta = close.diff()
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)
    avg_gain = gain.ewm(alpha=1 / n, adjust=False).mean()
    avg_loss = loss.ewm(alpha=1 / n, adjust=False).mean()
    rs = avg_gain / avg_loss.replace(0, np.nan)
    return 100 - (100 / (1 + rs))


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
    """Find a nearby, meaningful resistance zone using prior bars only."""
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
        center = float(np.mean(cluster)); top = float(max(cluster)); touches = len(cluster)
        positions = []
        for level in cluster:
            p = np.where(np.isclose(h.values, level, rtol=1e-8, atol=1e-8))[0]
            if len(p): positions.append(len(hist) - int(p[-1]))
        recency = min(positions) if positions else lookback
        distance = (top - current) / current * 100
        if distance >= -2:
            # A small preference for strong zones, but proximity remains dominant.
            strength = touches * 4 + max(0, 4 - recency / 30)
            candidates.append((abs(distance), -strength, top, touches, recency))
    if not candidates:
        return float(h.max()), 1, lookback
    candidates.sort(key=lambda x: (x[0], x[1]))
    _, _, top, touches, recency = candidates[0]
    return top, touches, recency


def false_breakout_info(df, lookback=20, tolerance=0.0025):
    if len(df) < lookback + 5:
        return False, 0
    recent = df.tail(lookback + 4).copy()
    for i in range(3, len(recent)):
        resistance = float(recent.iloc[:i].High.max())
        bar = recent.iloc[i]
        if float(bar.High) > resistance * (1 + tolerance):
            for j in range(i + 1, min(i + 4, len(recent))):
                if float(recent.iloc[j].Close) < resistance:
                    return True, (len(recent) - 1) - i
    return False, 0


def fetch_index_history(symbol="^NSEI", period="2y"):
    try:
        return _normalize_yf(yf.download(symbol, period=period, interval="1d", auto_adjust=True, progress=False, threads=False))
    except Exception:
        return None


def relative_strength_vs_index(stock_df, index_df, window=60):
    if index_df is None or len(stock_df) <= window or len(index_df) <= window:
        return 0.0
    a = float(stock_df.Close.iloc[-1] / stock_df.Close.iloc[-window - 1] - 1)
    b = float(index_df.Close.iloc[-1] / index_df.Close.iloc[-window - 1] - 1)
    return (a - b) * 100


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
    breakout, touches, recency = resistance_level(df)
    if not np.isfinite(breakout) or breakout <= 0 or price <= 0:
        return None
    distance = (breakout - price) / breakout * 100
    atr_v = _safe_float(atr(df).iloc[-1])
    atr_pct = atr_v / price * 100 if price else 0
    rsi_series = rsi(close); rsi_v = _safe_float(rsi_series.iloc[-1], 50)
    macd_line, signal, hist = macd(close)
    macd_v, signal_v, hist_v, hist_prev = map(_safe_float, [macd_line.iloc[-1], signal.iloc[-1], hist.iloc[-1], hist.iloc[-2]])
    adx_series, plus_di, minus_di = adx(df)
    adx_v, plus_v, minus_v = map(_safe_float, [adx_series.iloc[-1], plus_di.iloc[-1], minus_di.iloc[-1]])
    e20, e50 = _safe_float(ema(close, 20).iloc[-1]), _safe_float(ema(close, 50).iloc[-1])
    e200 = _safe_float(close.rolling(200).mean().iloc[-1])
    rvol = _safe_float(volume.iloc[-1] / volume.rolling(20).mean().iloc[-1], 0)
    candle = candle_pattern(df)
    ret60 = _safe_float(close.iloc[-1] / close.iloc[-61] - 1) * 100 if len(close) > 61 else 0
    nifty_rs = relative_strength_vs_index(df, nifty_df, 60)
    sector_rs = relative_strength_vs_index(df, sector_df, 60) if sector_df is not None else 0
    false_breakout, false_breakout_age = false_breakout_info(df)
    market_score, market_label = _market_regime(nifty_df)

    # Proximity is intentionally strong because the user's primary objective is near-breakout ranking.
    proximity = 1.0 if distance <= 0.5 else .92 if distance <= 1 else .82 if distance <= 2 else .70 if distance <= 3 else .55 if distance <= 5 else .30 if distance <= 8 else .05 if distance <= 10 else 0
    resistance = min(1.0, touches / 4)
    if recency <= 35: resistance = min(1.0, resistance + .10)

    volume_s = 1.0 if rvol >= 2.5 else .85 if rvol >= 1.8 else .70 if rvol >= 1.4 else .50 if rvol >= 1.15 else .30 if rvol >= .9 else .10

    # Trend: price above 20/50/200 with positive slope of 20 EMA.
    e20_prev = _safe_float(ema(close, 20).iloc[-6])
    trend = (0.30 if price > e20 else 0) + (0.30 if e20 > e50 else 0) + (0.25 if e50 > e200 else 0) + (0.15 if e20 > e20_prev else 0)

    # Momentum: RSI in a constructive zone + MACD direction.
    momentum = .75 if 52 <= rsi_v <= 68 else .55 if 48 <= rsi_v < 52 or 68 < rsi_v <= 72 else .25
    if rsi_v > _safe_float(rsi_series.iloc[-3], rsi_v): momentum = min(1, momentum + .15)
    if macd_v > signal_v and hist_v > hist_prev: momentum = min(1, momentum + .10)

    adx_s = .15 if adx_v < 15 else .35 if adx_v < 20 else .55 if adx_v < 25 else .75 if adx_v < 35 else .90
    if plus_v > minus_v: adx_s = min(1, adx_s + .10)

    # Volatility contraction: lower recent ATR than its 50-day average is a useful pre-breakout condition.
    atr_series = atr(df)
    atr50 = _safe_float(atr_series.rolling(50).mean().iloc[-1], atr_v)
    atr_ratio = atr_v / atr50 if atr50 else 1
    squeeze = 1.0 if atr_ratio <= .75 else .85 if atr_ratio <= .85 else .65 if atr_ratio <= .95 else .40 if atr_ratio <= 1.05 else .20

    rs_score = 0.0
    if nifty_rs >= 10: rs_score = .9
    elif nifty_rs >= 5: rs_score = .7
    elif nifty_rs >= 2: rs_score = .55
    elif nifty_rs >= 0: rs_score = .35
    if sector_rs > 5: rs_score = min(1, rs_score + .2)

    candle_score = {"Bullish Engulfing":1,"Bullish Marubozu":1,"Morning Star":1,"Three White Soldiers":1,"Hammer":.8,"Piercing Line":.8,"Inside Bar":.6,"None":0}.get(candle, 0)

    # A 0.25% trigger buffer avoids treating tiny intraday pierces as confirmed breakouts.
    breakout_trigger = breakout * 1.0025
    recent_low = _safe_float(df.Low.tail(10).min(), price)
    stop = min(recent_low, price - 1.5 * atr_v)
    if stop >= price: stop = price - 1.5 * atr_v
    target1 = breakout_trigger + 1.5 * atr_v
    target2 = breakout_trigger + 3.0 * atr_v
    risk = max(price - stop, 0.01)
    reward = max(target1 - price, 0)
    rr = reward / risk

    return {
        "price":price,"breakout_level":float(breakout),"breakout_trigger":float(breakout_trigger),"distance_pct":float(distance),
        "touches":touches,"recency":recency,"proximity":proximity,"resistance":resistance,"volume":volume_s,
        "trend":trend,"momentum":momentum,"adx":min(1,adx_s),"squeeze":squeeze,"relative_strength":rs_score,"candle":candle_score,
        "market_regime":market_score,"market_regime_label":market_label,"rsi_value":rsi_v,"macd_value":macd_v,"adx_value":adx_v,"rvol":rvol,
        "atr":atr_v,"atr_pct":atr_pct,"atr_ratio":atr_ratio,"ema_structure":("Bullish" if price > e20 > e50 > e200 else "Mixed" if price > e200 else "Bearish"),
        "candlestick":candle,"relative_strength_60":ret60,"nifty_relative_strength":nifty_rs,"sector_relative_strength":sector_rs,
        "false_breakout":bool(false_breakout),"false_breakout_age":int(false_breakout_age),"stop_reference":float(stop),
        "target1":float(target1),"target2":float(target2),"risk_reward":float(rr),
    }


def score_from_components(c, weights=None):
    weights = weights or DEFAULT_WEIGHTS
    raw = sum(c[k] * weights[k] for k in weights)
    # Strong penalty for a recent failed breakout, because the setup may still be in supply.
    if c["false_breakout"]: raw -= 10
    return float(np.clip(raw, 0, 100))


def _rating(score):
    # Explicit mapping: 90-100 = 10, 80-89.99 = 9, etc.
    return max(1, min(10, int(score // 10) + 1))


def score_stock(df, nifty_df=None, sector_df=None, weights=None):
    c = component_scores(df, nifty_df=nifty_df, sector_df=sector_df)
    if c is None: return None
    score = score_from_components(c, weights)
    rating = _rating(score)
    d = c["distance_pct"]
    status = "BREAKOUT CONFIRMED" if d < 0 else "VERY NEAR" if d <= 1 else "NEAR BREAKOUT" if d <= 3 else "DEVELOPING" if d <= 5 else "WATCH" if d <= 10 else "WEAK"
    reasons = []
    if d <= 3: reasons.append("close to resistance")
    if c["touches"] >= 3: reasons.append(f"{c['touches']} resistance touches")
    if c["rvol"] >= 1.4: reasons.append("volume confirmation")
    if c["ema_structure"] == "Bullish": reasons.append("bullish MA structure")
    if c["adx_value"] >= 20 and c["momentum"] >= .6: reasons.append("positive momentum/trend strength")
    if c["squeeze"] >= .65: reasons.append("volatility contraction")
    if c["nifty_relative_strength"] > 2: reasons.append("outperforming NIFTY")
    if c["false_breakout"]: reasons.append("recent false-breakout risk")
    explanation = f"Technical setup score {score:.1f}/100. " + ("; ".join(reasons) if reasons else "limited confirmation") + ". This is a setup-strength ranking, not a guaranteed price prediction."
    return {
        "price":c["price"],"breakout_level":c["breakout_level"],"breakout_trigger":c["breakout_trigger"],"distance_pct":c["distance_pct"],
        "score":score,"rating":rating,"status":status,"rsi":c["rsi_value"],"macd":c["macd_value"],"adx":c["adx_value"],"rvol":c["rvol"],
        "atr_pct":c["atr_pct"],"ema_structure":c["ema_structure"],"candlestick":c["candlestick"],"relative_strength":c["relative_strength_60"],
        "nifty_relative_strength":c["nifty_relative_strength"],"sector_relative_strength":c["sector_relative_strength"],"market_regime":c["market_regime_label"],
        "false_breakout":c["false_breakout"],"false_breakout_age":c["false_breakout_age"],"resistance_touches":c["touches"],"risk_reward":c["risk_reward"],
        "stop_reference":c["stop_reference"],"target1":c["target1"],"target2":c["target2"],"squeeze":c["squeeze"],"explanation":explanation,
    }


def _ranking_score(row):
    # Ranking prioritizes closeness, but prevents a weak stock from winning solely because it is 0.5% away.
    proximity = max(0, min(1, 1 - max(row["distance_pct"], 0) / 10))
    setup = row["score"] / 100
    volume = min(1, max(0, row["rvol"] / 2))
    return 100 * (0.45 * proximity + 0.40 * setup + 0.10 * volume + 0.05 * (1 if row["status"] == "BREAKOUT CONFIRMED" else 0))


def scan_universe(max_distance=10.0, period="2y", top_n=20):
    universe = load_universe()
    nifty = fetch_index_history("^NSEI", period=period)
    histories = fetch_histories_batch(universe.symbol.tolist(), period=period)
    rows = []
    for symbol, df in histories.items():
        row = score_stock(df, nifty_df=nifty)
        if row is None: continue
        if row["distance_pct"] < -1 or row["distance_pct"] > max_distance: continue
        row["symbol"] = symbol
        match = universe.loc[universe.symbol == symbol, "company_name"]
        row["company_name"] = match.iloc[0] if not match.empty else symbol
        row["rank_score"] = _ranking_score(row)
        rows.append(row)
    if not rows: return pd.DataFrame()
    result = pd.DataFrame(rows)
    # Top 20 are ranked by technical setup + proximity, not distance alone.
    result = result.sort_values(["rank_score", "score", "distance_pct"], ascending=[False, False, True]).reset_index(drop=True)
    result.insert(0, "rank", np.arange(1, len(result) + 1))
    return result.head(top_n)


def scan_single(symbol, max_distance=10.0, period="2y"):
    df = fetch_history(symbol, period)
    if df is None: return None
    nifty = fetch_index_history("^NSEI", period=period)
    row = score_stock(df, nifty_df=nifty)
    if row is None or row["distance_pct"] > max_distance: return None
    row["symbol"] = symbol
    row["rank_score"] = _ranking_score(row)
    return row


def backtest_symbol(symbol, period="5y", min_rating=7, hold_days=10):
    df = fetch_history(symbol, period)
    nifty = fetch_index_history("^NSEI", period=period)
    if df is None: return {"summary":{},"trades":pd.DataFrame()}
    trades=[]
    for i in range(220, len(df)-hold_days-1):
        hist=df.iloc[:i+1]
        row=score_stock(hist, nifty_df=nifty)
        if row is None or row["distance_pct"] < -1 or row["distance_pct"] > 10 or row["rating"] < min_rating: continue
        future=df.iloc[i+1:i+1+hold_days]; entry=float(hist.Close.iloc[-1]); level=float(row["breakout_level"])
        trades.append({"date":hist.index[-1],"breakout_hit":bool(future.High.max()>=level),"final_return_pct":(float(future.Close.iloc[-1])/entry-1)*100,"max_return_pct":(float(future.High.max())/entry-1)*100,"min_return_pct":(float(future.Low.min())/entry-1)*100,"rating":row["rating"]})
    t=pd.DataFrame(trades)
    if t.empty: return {"summary":{},"trades":t}
    return {"summary":{"signals":len(t),"breakout_hit_rate_pct":t.breakout_hit.mean()*100,"avg_final_return_pct":t.final_return_pct.mean(),"median_final_return_pct":t.final_return_pct.median(),"avg_max_return_pct":t.max_return_pct.mean(),"stop_5pct_rate_pct":(t.min_return_pct<=-5).mean()*100},"trades":t}


def optimize_weights(*args, **kwargs):
    # Kept as a compatibility hook. Weight tuning should be performed with the new walk-forward validator,
    # not optimized directly on the same observations used to select the final model.
    return pd.DataFrame(), DEFAULT_WEIGHTS
