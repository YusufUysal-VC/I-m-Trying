"""
yfinance wrapper with caching and error handling.
Fetches OHLCV data for stocks, crypto, forex, and commodities.
"""

import json
import logging
import os
import pickle
import time
from datetime import datetime, timedelta
from pathlib import Path

import pandas as pd
import yfinance as yf

logger = logging.getLogger(__name__)

BASE_DIR = Path(__file__).resolve().parent.parent
CACHE_DIR = BASE_DIR / "cache"
CONFIG_DIR = BASE_DIR / "config"

TIMEFRAMES = {
    "Günlük": {"period": "3mo", "interval": "1d"},
    "Haftalık": {"period": "1y", "interval": "1wk"},
    "Aylık": {"period": "5y", "interval": "1mo"},
    "3 Aylık": {"period": "max", "interval": "3mo"},
    "Yıllık": {"period": "max", "interval": "3mo"},
    "5 Yıllık": {"period": "max", "interval": "1mo"},
}


def load_watchlist(path: str | None = None) -> dict:
    """Load watchlist from JSON config file."""
    config_path = Path(path) if path else CONFIG_DIR / "watchlist.json"
    with open(config_path, "r", encoding="utf-8") as f:
        return json.load(f)


def _cache_key(symbol: str, timeframe: str) -> str:
    """Generate a cache key for a symbol+timeframe combination."""
    safe_symbol = symbol.replace("=", "_").replace("/", "_")
    safe_tf = timeframe.replace(" ", "_")
    today = datetime.now().strftime("%Y%m%d")
    return f"{safe_symbol}_{safe_tf}_{today}"


def _get_cache_path(symbol: str, timeframe: str) -> Path:
    """Get the file path for cached data."""
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    return CACHE_DIR / f"{_cache_key(symbol, timeframe)}.pkl"


def _is_cache_valid(cache_path: Path, interval: str) -> bool:
    """Check if cached data is still valid based on interval type."""
    if not cache_path.exists():
        return False
    mtime = datetime.fromtimestamp(cache_path.stat().st_mtime)
    age = datetime.now() - mtime
    if interval in ("1m", "5m", "15m", "30m", "1h"):
        return age < timedelta(hours=1)
    return age < timedelta(hours=24)


def fetch_ohlcv(symbol: str, timeframe: str) -> pd.DataFrame | None:
    """
    Fetch OHLCV data for a single symbol and timeframe.
    Uses cache if available and valid.

    Returns DataFrame with columns: Open, High, Low, Close, Volume
    Returns None if data cannot be fetched.
    """
    tf_config = TIMEFRAMES.get(timeframe)
    if not tf_config:
        logger.error(f"Unknown timeframe: {timeframe}")
        return None

    period = tf_config["period"]
    interval = tf_config["interval"]

    cache_path = _get_cache_path(symbol, timeframe)
    if _is_cache_valid(cache_path, interval):
        logger.info(f"Cache hit: {symbol} [{timeframe}]")
        try:
            with open(cache_path, "rb") as f:
                return pickle.load(f)
        except Exception:
            logger.warning(f"Cache read failed for {symbol}, fetching fresh data")

    logger.info(f"Fetching: {symbol} [{timeframe}] period={period} interval={interval}")
    try:
        ticker = yf.Ticker(symbol)
        df = ticker.history(period=period, interval=interval)

        if df is None or df.empty:
            logger.warning(f"No data returned for {symbol} [{timeframe}]")
            return None

        # Keep only OHLCV columns
        cols = ["Open", "High", "Low", "Close", "Volume"]
        available_cols = [c for c in cols if c in df.columns]
        df = df[available_cols].copy()

        # Drop rows with all NaN
        df.dropna(how="all", inplace=True)

        if df.empty:
            logger.warning(f"Empty data after cleanup for {symbol} [{timeframe}]")
            return None

        # Save to cache
        try:
            with open(cache_path, "wb") as f:
                pickle.dump(df, f)
        except Exception as e:
            logger.warning(f"Cache write failed for {symbol}: {e}")

        return df

    except Exception as e:
        logger.error(f"Failed to fetch {symbol} [{timeframe}]: {e}")
        return None


def fetch_all_timeframes(symbol: str) -> dict[str, pd.DataFrame | None]:
    """Fetch data for all timeframes for a single symbol."""
    results = {}
    for tf_name in TIMEFRAMES:
        results[tf_name] = fetch_ohlcv(symbol, tf_name)
        time.sleep(0.5)  # Rate limiting
    return results


def fetch_category(category_name: str, symbols: list[str]) -> dict[str, dict]:
    """
    Fetch data for all symbols in a category across all timeframes.
    Returns: {symbol: {timeframe: DataFrame}}
    """
    logger.info(f"Fetching category: {category_name} ({len(symbols)} symbols)")
    results = {}
    for symbol in symbols:
        results[symbol] = fetch_all_timeframes(symbol)
    return results


def get_current_price(symbol: str) -> dict | None:
    """Get current price info for a symbol."""
    try:
        ticker = yf.Ticker(symbol)
        info = ticker.fast_info
        return {
            "price": getattr(info, "last_price", None),
            "previous_close": getattr(info, "previous_close", None),
            "currency": getattr(info, "currency", "USD"),
        }
    except Exception as e:
        logger.warning(f"Could not get current price for {symbol}: {e}")
        return None
