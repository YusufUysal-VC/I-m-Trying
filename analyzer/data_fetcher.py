import yfinance as yf
import json
import os
from pathlib import Path

CACHE_DIR = Path(__file__).parent.parent / 'cache'
CACHE_DIR.mkdir(exist_ok=True)

TIMEFRAMES = {
    '1G': {'period': '1d', 'interval': '1m'},
    '1H': {'period': '5d', 'interval': '15m'},
    '1A': {'period': '1mo', 'interval': '1h'},
    '3A': {'period': '3mo', 'interval': '1d'},
    '1Y': {'period': '1y', 'interval': '1d'},
    '5Y': {'period': '5y', 'interval': '1wk'},
}


def fetch_data(symbol, tf='3A'):
    """Fetch OHLCV data for a symbol and timeframe."""
    tf_config = TIMEFRAMES.get(tf, TIMEFRAMES['3A'])
    ticker = yf.Ticker(symbol)
    df = ticker.history(period=tf_config['period'], interval=tf_config['interval'])
    return df


def safe_fetch(symbol, period, interval):
    """Fetch data with fallback to cache."""
    try:
        ticker = yf.Ticker(symbol)
        df = ticker.history(period=period, interval=interval)

        if df.empty or len(df) < 20:
            raise ValueError(f"Yetersiz veri: {symbol}")

        return df
    except Exception as e:
        cached = load_from_cache(symbol)
        if cached is not None:
            return cached
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
