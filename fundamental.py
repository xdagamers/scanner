import warnings
import yfinance as yf
import pandas as pd
import numpy as np
import concurrent.futures

# Suppress harmless internal yfinance/pandas deprecation warnings
warnings.simplefilter(action='ignore', category=FutureWarning)
warnings.filterwarnings("ignore", message=".*inplace.*")

def _calculate_yoy_growth(series):
    """Calculates Year-over-Year growth comparing to 4 quarters ago."""
    if series is None or len(series) < 5:
        return np.nan
    current = series.iloc[0]
    year_ago = series.iloc[4]
    if pd.isna(current) or pd.isna(year_ago) or year_ago == 0:
        return np.nan
    return float(((current - year_ago) / abs(year_ago)) * 100)

def fetch_single_fundamental(symbol):
    """Fetches Tier 1 fundamental metrics for a single NSE symbol."""
    ticker_str = f"{symbol}.NS"
    ticker = yf.Ticker(ticker_str)
    
    data = {
        "symbol": symbol,
        "q_rev_growth_yoy_pct": np.nan,
        "q_profit_growth_yoy_pct": np.nan,
        "operating_margin_pct": np.nan,
        "debt_to_equity": np.nan,
        "avg_traded_value_30d": np.nan,
        "fundamental_quality": "OK"
    }
    
    try:
        q_financials = ticker.quarterly_financials
        q_balance = ticker.quarterly_balance_sheet
        info = ticker.info

        if not q_financials.empty:
            if 'Total Revenue' in q_financials.index:
                data["q_rev_growth_yoy_pct"] = _calculate_yoy_growth(q_financials.loc['Total Revenue'].dropna())
            
            if 'Net Income' in q_financials.index:
                data["q_profit_growth_yoy_pct"] = _calculate_yoy_growth(q_financials.loc['Net Income'].dropna())
                
            if 'Operating Income' in q_financials.index and 'Total Revenue' in q_financials.index:
                op_income = q_financials.loc['Operating Income'].dropna()
                total_rev = q_financials.loc['Total Revenue'].dropna()
                if not op_income.empty and not total_rev.empty and total_rev.iloc[0] != 0:
                    data["operating_margin_pct"] = float((op_income.iloc[0] / total_rev.iloc[0]) * 100)

        if not q_balance.empty:
            if 'Total Debt' in q_balance.index and 'Stockholders Equity' in q_balance.index:
                total_debt = q_balance.loc['Total Debt'].dropna()
                equity = q_balance.loc['Stockholders Equity'].dropna()
                if not total_debt.empty and not equity.empty and equity.iloc[0] != 0:
                    data["debt_to_equity"] = float(total_debt.iloc[0] / equity.iloc[0])

        hist = ticker.history(period="2mo")
        if not hist.empty and len(hist) >= 30:
            last_30 = hist.tail(30)
            data["avg_traded_value_30d"] = float((last_30['Volume'] * last_30['Close']).mean())
        else:
            data["fundamental_quality"] = "MISSING_PRICE_HISTORY"

        if pd.isna(data["debt_to_equity"]) and "debtToEquity" in info:
            val = info.get("debtToEquity")
            if val is not None:
                data["debt_to_equity"] = float(val / 100)

    except Exception as e:
        data["fundamental_quality"] = "MISSING_DATA"

    return data

def fetch_fundamentals_batch(symbols, max_workers=10):
    """
    Fetches fundamental data concurrently for a list of symbols.
    Returns a pandas DataFrame.
    """
    results = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = {executor.submit(fetch_single_fundamental, sym): sym for sym in symbols}
        for future in concurrent.futures.as_completed(futures):
            try:
                results.append(future.result())
            except Exception:
                sym = futures[future]
                results.append({"symbol": sym, "fundamental_quality": "FETCH_FAILED"})
                
    df = pd.DataFrame(results)
    return df
