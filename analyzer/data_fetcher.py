import yfinance as yf
import json
import os
import pandas as pd
from pathlib import Path

CACHE_DIR = Path(__file__).parent.parent / 'cache'
OHLCV_CACHE_DIR = CACHE_DIR / 'ohlcv'
CACHE_DIR.mkdir(exist_ok=True)
OHLCV_CACHE_DIR.mkdir(exist_ok=True)

TIMEFRAMES = {
    '1G': {'period': '1d', 'interval': '1m'},
    '1H': {'period': '5d', 'interval': '15m'},
    '1A': {'period': '1mo', 'interval': '1h'},
    '3A': {'period': '3mo', 'interval': '1d'},
    '1Y': {'period': '1y', 'interval': '1d'},
    '5Y': {'period': '5y', 'interval': '1wk'},
}

# Alternative ticker formats to try when primary fails
TICKER_ALTERNATIVES = {
    # If symbol fails, try these suffixes/formats
    'suffixes': ['', '-USD', '.IS'],
}


def _try_fetch(symbol, period, interval):
    """Try fetching a single ticker."""
    ticker = yf.Ticker(symbol)
    df = ticker.history(period=period, interval=interval)
    if df is not None and not df.empty and len(df) >= 5:
        return df
    return None


def fetch_data(symbol, tf='3A'):
    """Fetch OHLCV data for a symbol and timeframe."""
    tf_config = TIMEFRAMES.get(tf, TIMEFRAMES['3A'])
    return safe_fetch(symbol, tf_config['period'], tf_config['interval'])


def safe_fetch(symbol, period, interval):
    """Fetch data with alternative ticker formats and OHLCV cache fallback."""
    # Try primary symbol first
    try:
        df = _try_fetch(symbol, period, interval)
        if df is not None and len(df) >= 5:
            _save_ohlcv_cache(symbol, period, interval, df)
            return df
    except Exception:
        pass

    # Try alternative formats if primary fails
    base = symbol.replace('-USD', '').replace('.IS', '')
    for suffix in TICKER_ALTERNATIVES['suffixes']:
        alt = base + suffix
        if alt == symbol:
            continue
        try:
            df = _try_fetch(alt, period, interval)
            if df is not None and len(df) >= 5:
                _save_ohlcv_cache(symbol, period, interval, df)
                return df
        except Exception:
            continue

    # Fallback: try with lower min_periods threshold (some ETNs have less data)
    try:
        ticker = yf.Ticker(symbol)
        df = ticker.history(period=period, interval=interval)
        if df is not None and not df.empty and len(df) >= 2:
            _save_ohlcv_cache(symbol, period, interval, df)
            return df
    except Exception:
        pass

    # Last resort: load OHLCV cache (returns DataFrame, not dict)
    cached_df = _load_ohlcv_cache(symbol, period, interval)
    if cached_df is not None:
        return cached_df

    return None


def _save_ohlcv_cache(symbol, period, interval, df):
    """Save OHLCV DataFrame to parquet/csv cache."""
    safe_name = symbol.replace('=', '_').replace('/', '_')
    cache_file = OHLCV_CACHE_DIR / f"{safe_name}_{period}_{interval}.csv"
    try:
        df.to_csv(cache_file)
    except Exception:
        pass


def _load_ohlcv_cache(symbol, period, interval):
    """Load cached OHLCV DataFrame."""
    safe_name = symbol.replace('=', '_').replace('/', '_')
    cache_file = OHLCV_CACHE_DIR / f"{safe_name}_{period}_{interval}.csv"
    if cache_file.exists():
        try:
            df = pd.read_csv(cache_file, index_col=0, parse_dates=True)
            if not df.empty:
                return df
        except Exception:
            pass
    return None


def save_to_cache(symbol, data):
    """Save analysis result to cache as JSON."""
    cache_file = CACHE_DIR / f"{symbol.replace('=', '_').replace('/', '_')}.json"
    with open(cache_file, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, default=str)


def load_from_cache(symbol):
    """Load cached analysis result."""
    cache_file = CACHE_DIR / f"{symbol.replace('=', '_').replace('/', '_')}.json"
    if cache_file.exists():
        with open(cache_file, 'r', encoding='utf-8') as f:
            return json.load(f)
    return None
