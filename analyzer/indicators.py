import pandas as pd
import numpy as np


def _ema(series, length):
    """Calculate Exponential Moving Average."""
    return series.ewm(span=length, adjust=False).mean()


def _sma(series, length):
    """Calculate Simple Moving Average."""
    return series.rolling(window=length).mean()


def _rsi(series, length=14):
    """Calculate Relative Strength Index."""
    delta = series.diff()
    gain = delta.where(delta > 0, 0.0)
    loss = -delta.where(delta < 0, 0.0)
    avg_gain = gain.ewm(alpha=1/length, min_periods=length).mean()
    avg_loss = loss.ewm(alpha=1/length, min_periods=length).mean()
    rs = avg_gain / avg_loss
    return 100 - (100 / (1 + rs))


def _macd(series, fast=12, slow=26, signal=9):
    """Calculate MACD, Signal, and Histogram."""
    ema_fast = _ema(series, fast)
    ema_slow = _ema(series, slow)
    macd_line = ema_fast - ema_slow
    signal_line = _ema(macd_line, signal)
    histogram = macd_line - signal_line
    return macd_line, signal_line, histogram


def _bbands(series, length=20, std=2):
    """Calculate Bollinger Bands."""
    mid = _sma(series, length)
    rolling_std = series.rolling(window=length).std()
    upper = mid + (rolling_std * std)
    lower = mid - (rolling_std * std)
    return upper, mid, lower


def calculate_all(df):
    """Calculate all technical indicators on a DataFrame."""
    if df is None or df.empty or len(df) < 20:
        return df

    close = df['Close']

    # RSI (14)
    df['rsi'] = _rsi(close, 14)

    # MACD (12, 26, 9)
    try:
        macd_line, signal_line, histogram = _macd(close, 12, 26, 9)
        df['macd'] = macd_line
        df['macd_signal'] = signal_line
        df['macd_hist'] = histogram
    except Exception as e:
        print(f"[HATA] MACD hesaplama: {e}")

    # Bollinger Bands (20, 2)
    try:
        upper, mid, lower = _bbands(close, 20, 2)
        df['bb_upper'] = upper
        df['bb_mid'] = mid
        df['bb_lower'] = lower
    except Exception as e:
        print(f"[HATA] BBands hesaplama: {e}")

    # Moving Averages
    if len(df) >= 20:
        df['ema20'] = _ema(close, 20)
        df['sma20'] = _sma(close, 20)
    if len(df) >= 50:
        df['ema50'] = _ema(close, 50)
    if len(df) >= 200:
        df['ema200'] = _ema(close, 200)

    # Volume EMA
    if 'Volume' in df.columns and df['Volume'].sum() > 0:
        df['vol_ema20'] = _ema(df['Volume'].astype(float), 20)
    else:
        df['vol_ema20'] = 0

    return df
