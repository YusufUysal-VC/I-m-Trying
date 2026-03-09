#!/usr/bin/env python3
"""
demo_data.py — Synthetic data generator for testing the report pipeline
without internet access. Generates realistic OHLCV data for all timeframes.
"""

import numpy as np
import pandas as pd
from datetime import datetime, timedelta


def generate_ohlcv(
    start_price: float,
    n_bars: int,
    volatility: float = 0.02,
    trend: float = 0.001,
    seed: int = 42,
) -> pd.DataFrame:
    """Generate realistic synthetic OHLCV data."""
    rng = np.random.default_rng(seed)
    prices = [start_price]
    for _ in range(n_bars - 1):
        change = rng.normal(trend, volatility)
        prices.append(prices[-1] * (1 + change))

    prices = np.array(prices)
    opens = prices.copy()
    closes = prices * (1 + rng.normal(0, volatility * 0.3, n_bars))
    highs = np.maximum(opens, closes) * (1 + abs(rng.normal(0, volatility * 0.5, n_bars)))
    lows = np.minimum(opens, closes) * (1 - abs(rng.normal(0, volatility * 0.5, n_bars)))
    volumes = rng.lognormal(mean=np.log(1_000_000), sigma=0.5, size=n_bars).astype(int)

    # Date index
    end = datetime.now()
    dates = pd.date_range(end=end, periods=n_bars, freq="D")

    return pd.DataFrame(
        {"Open": opens, "High": highs, "Low": lows, "Close": closes, "Volume": volumes},
        index=dates,
    )


# Demo symbols with realistic starting prices
DEMO_PRICES = {
    "THYAO.IS": 55.0,
    "ASELS.IS": 78.5,
    "EREGL.IS": 28.3,
    "GARAN.IS": 102.0,
    "SISE.IS": 22.8,
    "AAPL": 225.0,
    "NVDA": 875.0,
    "MSFT": 415.0,
    "TSLA": 195.0,
    "AMZN": 198.0,
    "BTC-USD": 82400.0,
    "ETH-USD": 3200.0,
    "SOL-USD": 168.0,
    "BNB-USD": 610.0,
    "USDTRY=X": 36.5,
    "EURUSD=X": 1.084,
    "GBPUSD=X": 1.265,
    "EURTRY=X": 39.6,
    "GC=F": 2918.0,
    "SI=F": 32.5,
    "CL=F": 78.5,
    "NG=F": 3.85,
}

# Timeframe bar counts for demo
TF_BARS = {
    "Günlük": 90,
    "Haftalık": 52,
    "Aylık": 60,
    "3 Aylık": 40,
    "Yıllık": 30,
    "5 Yıllık": 60,
}

# Trend profiles per category
TF_TRENDS = {
    "Günlük": {"trend": 0.0015, "vol": 0.018},
    "Haftalık": {"trend": 0.002, "vol": 0.025},
    "Aylık": {"trend": 0.003, "vol": 0.035},
    "3 Aylık": {"trend": 0.003, "vol": 0.035},
    "Yıllık": {"trend": 0.003, "vol": 0.035},
    "5 Yıllık": {"trend": 0.004, "vol": 0.045},
}


def get_demo_data(symbol: str, period: str, interval: str) -> pd.DataFrame:
    """Return synthetic OHLCV data for a symbol and timeframe."""
    start_price = DEMO_PRICES.get(symbol, 100.0)

    # Map interval to timeframe label
    interval_to_tf = {
        "1d": "Günlük",
        "1wk": "Haftalık",
        "1mo": "Aylık",
        "3mo": "3 Aylık",
    }
    tf = interval_to_tf.get(interval, "Günlük")
    cfg = TF_TRENDS.get(tf, {"trend": 0.001, "vol": 0.02})
    n_bars = TF_BARS.get(tf, 60)

    seed = hash(symbol + interval) % (2**31)

    # Resample to weekly/monthly by creating fewer bars
    if interval == "1wk":
        freq_str = "W-FRI"
    elif interval in ("1mo", "3mo"):
        freq_str = "MS"
    else:
        freq_str = "B"  # business days

    # Generate dates first, then build OHLCV with exact same length
    dates = pd.date_range(end=datetime.now(), periods=n_bars, freq=freq_str)
    n_actual = len(dates)

    df = generate_ohlcv(
        start_price=start_price,
        n_bars=n_actual,
        volatility=cfg["vol"],
        trend=cfg["trend"],
        seed=seed,
    )
    df.index = dates
    return df
