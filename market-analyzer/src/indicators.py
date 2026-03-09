"""
indicators.py — Technical indicator computation using pandas-ta.
Computes RSI, MACD, Bollinger Bands, EMAs, and Support/Resistance levels.
"""

import logging
from dataclasses import dataclass, field
from typing import Optional

import numpy as np
import pandas as pd

try:
    import pandas_ta as ta
except ImportError:
    ta = None
    logging.warning("pandas-ta not installed. Install with: pip install pandas-ta")

logger = logging.getLogger(__name__)


@dataclass
class IndicatorResult:
    """Holds all computed indicator values for a single timeframe."""
    symbol: str
    timeframe: str
    df: pd.DataFrame  # OHLCV + indicators

    # Current values (last row)
    current_price: float = 0.0
    rsi: Optional[float] = None
    macd_line: Optional[float] = None
    macd_signal: Optional[float] = None
    macd_histogram: Optional[float] = None
    bb_upper: Optional[float] = None
    bb_middle: Optional[float] = None
    bb_lower: Optional[float] = None
    bb_pct: Optional[float] = None       # 0-100: position within bands
    bb_squeeze: bool = False
    ema_20: Optional[float] = None
    ema_50: Optional[float] = None
    ema_200: Optional[float] = None

    # Signal flags
    rsi_signal: str = "neutral"          # "oversold" | "neutral" | "overbought"
    rsi_divergence: str = "none"         # "bullish" | "bearish" | "none"
    macd_signal_type: str = "neutral"    # "bullish_cross" | "bearish_cross" | "neutral"
    golden_cross: bool = False
    death_cross: bool = False
    ema_alignment: str = "neutral"       # "bullish" | "bearish" | "neutral"

    # Support & Resistance
    support_levels: list = field(default_factory=list)
    resistance_levels: list = field(default_factory=list)


def compute_all_indicators(symbol: str, timeframe: str, df: pd.DataFrame) -> IndicatorResult:
    """
    Compute all technical indicators for a given OHLCV dataframe.
    Returns an IndicatorResult with all values populated.
    """
    result = IndicatorResult(symbol=symbol, timeframe=timeframe, df=df.copy())

    if df is None or len(df) < 10:
        logger.warning(f"Insufficient data for {symbol} {timeframe}: {len(df) if df is not None else 0} rows")
        return result

    df = df.copy()
    result.current_price = float(df["Close"].iloc[-1])

    _compute_rsi(df, result)
    _compute_macd(df, result)
    _compute_bollinger_bands(df, result)
    _compute_emas(df, result)
    _compute_support_resistance(df, result)
    _detect_cross_signals(df, result)

    result.df = df
    return result


def _compute_rsi(df: pd.DataFrame, result: IndicatorResult) -> None:
    """Compute RSI(14) and determine signal zones."""
    try:
        if ta is not None:
            rsi_series = df.ta.rsi(length=14)
        else:
            rsi_series = _manual_rsi(df["Close"], 14)

        if rsi_series is not None and not rsi_series.dropna().empty:
            df["RSI"] = rsi_series
            result.rsi = float(rsi_series.iloc[-1]) if not pd.isna(rsi_series.iloc[-1]) else None

            if result.rsi is not None:
                if result.rsi > 70:
                    result.rsi_signal = "overbought"
                elif result.rsi < 30:
                    result.rsi_signal = "oversold"
                else:
                    result.rsi_signal = "neutral"

            # RSI divergence detection (simple)
            result.rsi_divergence = _detect_rsi_divergence(df)
    except Exception as e:
        logger.error(f"RSI computation failed: {e}")


def _manual_rsi(close: pd.Series, period: int = 14) -> pd.Series:
    """Fallback manual RSI calculation."""
    delta = close.diff()
    gain = delta.where(delta > 0, 0.0)
    loss = -delta.where(delta < 0, 0.0)
    avg_gain = gain.ewm(com=period - 1, min_periods=period).mean()
    avg_loss = loss.ewm(com=period - 1, min_periods=period).mean()
    rs = avg_gain / avg_loss.replace(0, np.nan)
    return 100 - (100 / (1 + rs))


def _detect_rsi_divergence(df: pd.DataFrame) -> str:
    """
    Detect simple RSI divergence using last 20 bars.
    Bullish: price making lower lows while RSI makes higher lows.
    Bearish: price making higher highs while RSI makes lower highs.
    """
    if "RSI" not in df.columns or len(df) < 20:
        return "none"

    last_n = df.tail(20).dropna(subset=["RSI"])
    if len(last_n) < 10:
        return "none"

    prices = last_n["Close"].values
    rsi_vals = last_n["RSI"].values

    # Find swing lows
    mid = len(prices) // 2
    price_low_early = min(prices[:mid])
    price_low_late = min(prices[mid:])
    rsi_low_early = min(rsi_vals[:mid])
    rsi_low_late = min(rsi_vals[mid:])

    # Find swing highs
    price_high_early = max(prices[:mid])
    price_high_late = max(prices[mid:])
    rsi_high_early = max(rsi_vals[:mid])
    rsi_high_late = max(rsi_vals[mid:])

    if price_low_late < price_low_early and rsi_low_late > rsi_low_early:
        return "bullish"
    if price_high_late > price_high_early and rsi_high_late < rsi_high_early:
        return "bearish"
    return "none"


def _compute_macd(df: pd.DataFrame, result: IndicatorResult) -> None:
    """Compute MACD(12,26,9)."""
    try:
        if ta is not None:
            macd_df = df.ta.macd(fast=12, slow=26, signal=9)
        else:
            macd_df = _manual_macd(df["Close"])

        if macd_df is not None and not macd_df.empty:
            # pandas-ta returns columns: MACD_12_26_9, MACDh_12_26_9, MACDs_12_26_9
            macd_col = [c for c in macd_df.columns if c.startswith("MACD_")]
            hist_col = [c for c in macd_df.columns if c.startswith("MACDh_")]
            sig_col = [c for c in macd_df.columns if c.startswith("MACDs_")]

            if macd_col:
                df["MACD"] = macd_df[macd_col[0]]
                result.macd_line = _safe_float(macd_df[macd_col[0]].iloc[-1])
            if hist_col:
                df["MACD_hist"] = macd_df[hist_col[0]]
                result.macd_histogram = _safe_float(macd_df[hist_col[0]].iloc[-1])
            if sig_col:
                df["MACD_signal"] = macd_df[sig_col[0]]
                result.macd_signal = _safe_float(macd_df[sig_col[0]].iloc[-1])

            # Detect crossover
            if len(df) >= 2 and "MACD" in df.columns and "MACD_signal" in df.columns:
                prev_macd = _safe_float(df["MACD"].iloc[-2])
                curr_macd = result.macd_line
                prev_sig = _safe_float(df["MACD_signal"].iloc[-2])
                curr_sig = result.macd_signal

                if all(v is not None for v in [prev_macd, curr_macd, prev_sig, curr_sig]):
                    if prev_macd < prev_sig and curr_macd > curr_sig:
                        result.macd_signal_type = "bullish_cross"
                    elif prev_macd > prev_sig and curr_macd < curr_sig:
                        result.macd_signal_type = "bearish_cross"
                    elif curr_macd > curr_sig:
                        result.macd_signal_type = "bullish"
                    else:
                        result.macd_signal_type = "bearish"
    except Exception as e:
        logger.error(f"MACD computation failed: {e}")


def _manual_macd(close: pd.Series) -> pd.DataFrame:
    """Fallback manual MACD calculation."""
    ema12 = close.ewm(span=12, adjust=False).mean()
    ema26 = close.ewm(span=26, adjust=False).mean()
    macd = ema12 - ema26
    signal = macd.ewm(span=9, adjust=False).mean()
    hist = macd - signal
    return pd.DataFrame({
        "MACD_12_26_9": macd,
        "MACDs_12_26_9": signal,
        "MACDh_12_26_9": hist,
    })


def _compute_bollinger_bands(df: pd.DataFrame, result: IndicatorResult) -> None:
    """Compute Bollinger Bands (20, 2) and detect squeeze."""
    try:
        if ta is not None:
            bb_df = df.ta.bbands(length=20, std=2)
        else:
            bb_df = _manual_bbands(df["Close"])

        if bb_df is not None and not bb_df.empty:
            upper_col = [c for c in bb_df.columns if c.startswith("BBU_")]
            mid_col = [c for c in bb_df.columns if c.startswith("BBM_")]
            lower_col = [c for c in bb_df.columns if c.startswith("BBL_")]

            if upper_col and mid_col and lower_col:
                df["BB_upper"] = bb_df[upper_col[0]]
                df["BB_middle"] = bb_df[mid_col[0]]
                df["BB_lower"] = bb_df[lower_col[0]]

                result.bb_upper = _safe_float(bb_df[upper_col[0]].iloc[-1])
                result.bb_middle = _safe_float(bb_df[mid_col[0]].iloc[-1])
                result.bb_lower = _safe_float(bb_df[lower_col[0]].iloc[-1])

                if result.bb_upper and result.bb_lower and result.bb_upper != result.bb_lower:
                    price = result.current_price
                    band_range = result.bb_upper - result.bb_lower
                    result.bb_pct = round((price - result.bb_lower) / band_range * 100, 1)

                # Squeeze: current band width vs historical average
                band_width = bb_df[upper_col[0]] - bb_df[lower_col[0]]
                avg_bw = band_width.rolling(50).mean()
                if not avg_bw.empty and not pd.isna(avg_bw.iloc[-1]) and avg_bw.iloc[-1] > 0:
                    curr_bw = band_width.iloc[-1]
                    if curr_bw < avg_bw.iloc[-1] * 0.7:
                        result.bb_squeeze = True
    except Exception as e:
        logger.error(f"Bollinger Bands computation failed: {e}")


def _manual_bbands(close: pd.Series, length: int = 20, std: float = 2) -> pd.DataFrame:
    """Fallback manual Bollinger Bands."""
    mid = close.rolling(length).mean()
    std_dev = close.rolling(length).std()
    upper = mid + std * std_dev
    lower = mid - std * std_dev
    return pd.DataFrame({
        f"BBU_{length}_{std}.0": upper,
        f"BBM_{length}_{std}.0": mid,
        f"BBL_{length}_{std}.0": lower,
    })


def _compute_emas(df: pd.DataFrame, result: IndicatorResult) -> None:
    """Compute EMA 20, 50, 200."""
    try:
        for period in [20, 50, 200]:
            if len(df) >= period // 2:
                if ta is not None:
                    ema = df.ta.ema(length=period)
                else:
                    ema = df["Close"].ewm(span=period, adjust=False).mean()

                col_name = f"EMA_{period}"
                df[col_name] = ema
                val = _safe_float(ema.iloc[-1])
                if period == 20:
                    result.ema_20 = val
                elif period == 50:
                    result.ema_50 = val
                elif period == 200:
                    result.ema_200 = val

        # EMA alignment
        e20, e50, e200 = result.ema_20, result.ema_50, result.ema_200
        if e20 and e50 and e200:
            if e20 > e50 > e200:
                result.ema_alignment = "bullish"
            elif e20 < e50 < e200:
                result.ema_alignment = "bearish"
            else:
                result.ema_alignment = "neutral"
    except Exception as e:
        logger.error(f"EMA computation failed: {e}")


def _detect_cross_signals(df: pd.DataFrame, result: IndicatorResult) -> None:
    """Detect Golden Cross and Death Cross (EMA50 vs EMA200)."""
    try:
        if "EMA_50" not in df.columns or "EMA_200" not in df.columns:
            return
        if len(df) < 2:
            return

        prev_e50 = _safe_float(df["EMA_50"].iloc[-2])
        curr_e50 = result.ema_50
        prev_e200 = _safe_float(df["EMA_200"].iloc[-2])
        curr_e200 = result.ema_200

        if all(v is not None for v in [prev_e50, curr_e50, prev_e200, curr_e200]):
            if prev_e50 < prev_e200 and curr_e50 > curr_e200:
                result.golden_cross = True
            elif prev_e50 > prev_e200 and curr_e50 < curr_e200:
                result.death_cross = True
    except Exception as e:
        logger.error(f"Cross signal detection failed: {e}")


def _compute_support_resistance(df: pd.DataFrame, result: IndicatorResult) -> None:
    """
    Detect support and resistance levels using pivot point method.
    Uses rolling window of 10 candles left + 10 right.
    Clusters nearby levels within 0.5% and scores by touch count.
    """
    try:
        if len(df) < 25:
            return

        window = 10
        highs = df["High"].values
        lows = df["Low"].values
        closes = df["Close"].values

        pivot_highs = []
        pivot_lows = []

        for i in range(window, len(df) - window):
            # Pivot high: local maximum
            if highs[i] == max(highs[i - window: i + window + 1]):
                pivot_highs.append(highs[i])
            # Pivot low: local minimum
            if lows[i] == min(lows[i - window: i + window + 1]):
                pivot_lows.append(lows[i])

        current_price = closes[-1]

        # Cluster and score
        support_levels = _cluster_levels(pivot_lows, current_price, is_support=True)
        resistance_levels = _cluster_levels(pivot_highs, current_price, is_support=False)

        # Sort and take top 3 each
        result.support_levels = sorted(support_levels, key=lambda x: x["price"], reverse=True)[:3]
        result.resistance_levels = sorted(resistance_levels, key=lambda x: x["price"])[:3]
    except Exception as e:
        logger.error(f"Support/Resistance computation failed: {e}")


def _cluster_levels(levels: list, current_price: float, is_support: bool) -> list:
    """Cluster nearby price levels (within 0.5%) and score them."""
    if not levels:
        return []

    sorted_levels = sorted(levels)
    clusters = []
    current_cluster = [sorted_levels[0]]

    for level in sorted_levels[1:]:
        if level <= current_cluster[-1] * 1.005:
            current_cluster.append(level)
        else:
            clusters.append(current_cluster)
            current_cluster = [level]
    clusters.append(current_cluster)

    result = []
    for cluster in clusters:
        avg_price = sum(cluster) / len(cluster)
        touch_count = len(cluster)
        if touch_count >= 3:
            strength = "Güçlü"
        elif touch_count == 2:
            strength = "Orta"
        else:
            strength = "Zayıf"

        # Filter: supports below current price, resistances above
        if is_support and avg_price < current_price * 1.02:
            result.append({"price": round(avg_price, 4), "strength": strength, "touches": touch_count})
        elif not is_support and avg_price > current_price * 0.98:
            result.append({"price": round(avg_price, 4), "strength": strength, "touches": touch_count})

    return result


def _safe_float(val) -> Optional[float]:
    """Convert to float, return None if NaN/invalid."""
    try:
        f = float(val)
        return None if (np.isnan(f) or np.isinf(f)) else f
    except (TypeError, ValueError):
        return None
