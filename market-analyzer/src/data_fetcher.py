"""
data_fetcher.py — yfinance wrapper with caching and error handling.
Fetches OHLCV data for stocks, crypto, forex, and commodities.
"""

import os
import time
import pickle
import logging
import hashlib
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional

import pandas as pd
import yfinance as yf

logger = logging.getLogger(__name__)

# Cache directory relative to project root
CACHE_DIR = Path(__file__).parent.parent / "cache"
CACHE_DIR.mkdir(exist_ok=True)

# Timeframe configurations: (period, interval, label)
TIMEFRAMES = {
    "Günlük":   {"period": "3mo",  "interval": "1d",  "cache_hours": 1},
    "Haftalık": {"period": "1y",   "interval": "1wk", "cache_hours": 24},
    "Aylık":    {"period": "5y",   "interval": "1mo", "cache_hours": 24},
    "3 Aylık":  {"period": "max",  "interval": "3mo", "cache_hours": 24},
    "Yıllık":   {"period": "max",  "interval": "3mo", "cache_hours": 24},
    "5 Yıllık": {"period": "max",  "interval": "1mo", "cache_hours": 24},
}


def _cache_key(symbol: str, period: str, interval: str) -> str:
    raw = f"{symbol}_{period}_{interval}_{datetime.now().strftime('%Y%m%d')}"
    return hashlib.md5(raw.encode()).hexdigest()


def _cache_path(symbol: str, period: str, interval: str) -> Path:
    key = _cache_key(symbol, period, interval)
    safe_symbol = symbol.replace("/", "_").replace("=", "_").replace("-", "_")
    return CACHE_DIR / f"{safe_symbol}_{period}_{interval}_{key}.pkl"


def _is_cache_valid(path: Path, max_age_hours: int) -> bool:
    if not path.exists():
        return False
    age = datetime.now() - datetime.fromtimestamp(path.stat().st_mtime)
    return age < timedelta(hours=max_age_hours)


def _load_from_cache(path: Path) -> Optional[pd.DataFrame]:
    try:
        with open(path, "rb") as f:
            return pickle.load(f)
    except Exception as e:
        logger.warning(f"Cache load failed for {path}: {e}")
        return None


def _save_to_cache(df: pd.DataFrame, path: Path) -> None:
    try:
        with open(path, "wb") as f:
            pickle.dump(df, f)
    except Exception as e:
        logger.warning(f"Cache save failed for {path}: {e}")


def fetch_ohlcv(symbol: str, period: str, interval: str, cache_hours: int = 24) -> Optional[pd.DataFrame]:
    """
    Fetch OHLCV data for a symbol. Uses cache if available and fresh.
    Returns DataFrame with columns: Open, High, Low, Close, Volume
    Returns None if data unavailable.
    """
    cache_path = _cache_path(symbol, period, interval)

    if _is_cache_valid(cache_path, cache_hours):
        df = _load_from_cache(cache_path)
        if df is not None and not df.empty:
            logger.debug(f"Cache hit: {symbol} {period}/{interval}")
            return df

    logger.info(f"Fetching {symbol} ({period}/{interval}) from yfinance...")
    try:
        ticker = yf.Ticker(symbol)
        df = ticker.history(period=period, interval=interval, auto_adjust=True)

        if df is None or df.empty:
            logger.warning(f"No data returned for {symbol} ({period}/{interval})")
            return None

        # Normalize column names
        df.index = pd.to_datetime(df.index)
        df = df[["Open", "High", "Low", "Close", "Volume"]].copy()
        df.dropna(subset=["Close"], inplace=True)

        if len(df) < 5:
            logger.warning(f"Insufficient data for {symbol} ({period}/{interval}): {len(df)} rows")
            return None

        _save_to_cache(df, cache_path)
        time.sleep(0.5)  # Rate limiting
        return df

    except Exception as e:
        logger.error(f"Error fetching {symbol} ({period}/{interval}): {e}")
        return None


def fetch_all_timeframes(symbol: str) -> dict[str, Optional[pd.DataFrame]]:
    """
    Fetch OHLCV data for all configured timeframes.
    Returns dict: timeframe_label -> DataFrame or None
    """
    results = {}
    for tf_label, tf_config in TIMEFRAMES.items():
        df = fetch_ohlcv(
            symbol=symbol,
            period=tf_config["period"],
            interval=tf_config["interval"],
            cache_hours=tf_config["cache_hours"],
        )
        results[tf_label] = df
        if df is None:
            logger.warning(f"No data for {symbol} on {tf_label} timeframe")
    return results


def get_current_price(symbol: str) -> Optional[float]:
    """Get the most recent closing price for a symbol."""
    df = fetch_ohlcv(symbol, period="5d", interval="1d", cache_hours=1)
    if df is not None and not df.empty:
        return float(df["Close"].iloc[-1])
    return None


def get_price_change_pct(symbol: str) -> Optional[float]:
    """Get 1-day percentage price change."""
    df = fetch_ohlcv(symbol, period="5d", interval="1d", cache_hours=1)
    if df is not None and len(df) >= 2:
        prev_close = float(df["Close"].iloc[-2])
        curr_close = float(df["Close"].iloc[-1])
        if prev_close > 0:
            return round((curr_close - prev_close) / prev_close * 100, 2)
    return None


def load_watchlist(watchlist_path: str = None) -> dict:
    """Load watchlist from JSON config file."""
    import json
    if watchlist_path is None:
        watchlist_path = Path(__file__).parent.parent / "config" / "watchlist.json"
    with open(watchlist_path, "r", encoding="utf-8") as f:
        return json.load(f)
