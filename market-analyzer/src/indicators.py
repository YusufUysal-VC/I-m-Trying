"""
Technical indicators: RSI, MACD, Bollinger Bands, EMA, Support/Resistance detection.
Uses pandas-ta for indicator computation.
"""

import logging
from dataclasses import dataclass, field

import numpy as np
import pandas as pd
import pandas_ta as ta

logger = logging.getLogger(__name__)


@dataclass
class SupportResistanceLevel:
    price: float
    level_type: str  # "support" or "resistance"
    strength: str  # "Strong", "Moderate", "Weak"
    touch_count: int = 1


@dataclass
class IndicatorResult:
    """All computed indicators for a single symbol+timeframe."""
    # RSI
    rsi: float | None = None
    rsi_series: pd.Series | None = None
    rsi_zone: str = "Nötr"  # "Aşırı Alım", "Nötr", "Aşırı Satım"
    rsi_divergence: str | None = None  # "bullish", "bearish", None

    # MACD
    macd_line: float | None = None
    macd_signal: float | None = None
    macd_histogram: float | None = None
    macd_series: pd.DataFrame | None = None
    macd_crossover: str | None = None  # "bullish_cross", "bearish_cross", None

    # Bollinger Bands
    bb_upper: float | None = None
    bb_middle: float | None = None
    bb_lower: float | None = None
    bb_percent: float | None = None  # 0-100
    bb_squeeze: bool = False
    bb_series: pd.DataFrame | None = None

    # EMAs
    ema20: float | None = None
    ema50: float | None = None
    ema200: float | None = None
    ema20_series: pd.Series | None = None
    ema50_series: pd.Series | None = None
    ema200_series: pd.Series | None = None
    golden_cross: bool = False
    death_cross: bool = False
    price_vs_ema200: str = "unknown"  # "above" or "below"

    # Support & Resistance
    support_levels: list = field(default_factory=list)
    resistance_levels: list = field(default_factory=list)

    # Price info
    current_price: float | None = None
    price_change_pct: float | None = None
    high_52w: float | None = None
    low_52w: float | None = None


def compute_rsi(df: pd.DataFrame, length: int = 14) -> tuple[pd.Series | None, float | None]:
    """Compute RSI using pandas-ta."""
    try:
        rsi = df.ta.rsi(length=length)
        if rsi is not None and not rsi.dropna().empty:
            return rsi, rsi.dropna().iloc[-1]
    except Exception as e:
        logger.warning(f"RSI computation failed: {e}")
    return None, None


def compute_macd(df: pd.DataFrame, fast: int = 12, slow: int = 26, signal: int = 9) -> tuple[pd.DataFrame | None, dict]:
    """Compute MACD using pandas-ta."""
    try:
        macd_df = df.ta.macd(fast=fast, slow=slow, signal=signal)
        if macd_df is not None and not macd_df.dropna().empty:
            last = macd_df.dropna().iloc[-1]
            cols = macd_df.columns.tolist()
            values = {
                "macd_line": last.iloc[0],
                "signal_line": last.iloc[1],
                "histogram": last.iloc[2],
            }
            # Check for crossover (compare last 2 rows)
            if len(macd_df.dropna()) >= 2:
                prev = macd_df.dropna().iloc[-2]
                prev_diff = prev.iloc[0] - prev.iloc[1]
                curr_diff = last.iloc[0] - last.iloc[1]
                if prev_diff < 0 and curr_diff >= 0:
                    values["crossover"] = "bullish_cross"
                elif prev_diff > 0 and curr_diff <= 0:
                    values["crossover"] = "bearish_cross"
                else:
                    values["crossover"] = None
            else:
                values["crossover"] = None
            return macd_df, values
    except Exception as e:
        logger.warning(f"MACD computation failed: {e}")
    return None, {}


def compute_bollinger_bands(df: pd.DataFrame, length: int = 20, std: float = 2.0) -> tuple[pd.DataFrame | None, dict]:
    """Compute Bollinger Bands using pandas-ta."""
    try:
        bb = df.ta.bbands(length=length, std=std)
        if bb is not None and not bb.dropna().empty:
            last = bb.dropna().iloc[-1]
            cols = bb.columns.tolist()
            # Columns: BBL, BBM, BBU, BBB, BBP
            lower = last.iloc[0]
            mid = last.iloc[1]
            upper = last.iloc[2]

            price = df["Close"].dropna().iloc[-1]
            bb_range = upper - lower
            bb_percent = ((price - lower) / bb_range * 100) if bb_range > 0 else 50

            # Squeeze detection: compare current bandwidth to 20-period avg
            if len(bb.dropna()) >= 20:
                bw_col = bb.columns[3]  # BBB column
                bw_series = bb[bw_col].dropna()
                current_bw = bw_series.iloc[-1]
                avg_bw = bw_series.tail(20).mean()
                squeeze = current_bw < avg_bw * 0.75
            else:
                squeeze = False

            return bb, {
                "upper": upper,
                "middle": mid,
                "lower": lower,
                "percent": bb_percent,
                "squeeze": squeeze,
            }
    except Exception as e:
        logger.warning(f"Bollinger Bands computation failed: {e}")
    return None, {}


def compute_emas(df: pd.DataFrame) -> dict:
    """Compute EMA 20, 50, 200."""
    result = {}
    for length in (20, 50, 200):
        try:
            ema = df.ta.ema(length=length)
            if ema is not None and not ema.dropna().empty:
                result[f"ema{length}"] = ema.dropna().iloc[-1]
                result[f"ema{length}_series"] = ema
            else:
                result[f"ema{length}"] = None
                result[f"ema{length}_series"] = None
        except Exception as e:
            logger.warning(f"EMA{length} computation failed: {e}")
            result[f"ema{length}"] = None
            result[f"ema{length}_series"] = None
    return result


def detect_support_resistance(df: pd.DataFrame, window: int = 10, cluster_pct: float = 0.005) -> tuple[list, list]:
    """
    Detect support and resistance levels using local minima/maxima.
    Uses rolling window of `window` candles left + right to find pivot highs/lows.
    Clusters nearby levels within `cluster_pct` (0.5%).
    """
    if df is None or len(df) < window * 2 + 1:
        return [], []

    highs = df["High"].values
    lows = df["Low"].values
    pivot_highs = []
    pivot_lows = []

    for i in range(window, len(df) - window):
        # Pivot high
        if highs[i] == max(highs[i - window: i + window + 1]):
            pivot_highs.append(highs[i])
        # Pivot low
        if lows[i] == min(lows[i - window: i + window + 1]):
            pivot_lows.append(lows[i])

    def cluster_levels(levels: list[float], pct: float) -> list[SupportResistanceLevel]:
        """Cluster nearby levels and count touches."""
        if not levels:
            return []
        levels = sorted(levels)
        clusters = []
        current_cluster = [levels[0]]

        for i in range(1, len(levels)):
            if abs(levels[i] - current_cluster[-1]) / current_cluster[-1] <= pct:
                current_cluster.append(levels[i])
            else:
                clusters.append(current_cluster)
                current_cluster = [levels[i]]
        clusters.append(current_cluster)

        result = []
        for cluster in clusters:
            avg_price = sum(cluster) / len(cluster)
            touch_count = len(cluster)
            if touch_count >= 3:
                strength = "Strong"
            elif touch_count >= 2:
                strength = "Moderate"
            else:
                strength = "Weak"
            result.append(SupportResistanceLevel(
                price=round(avg_price, 4),
                level_type="",
                strength=strength,
                touch_count=touch_count,
            ))
        return result

    support_levels = cluster_levels(pivot_lows, cluster_pct)
    for s in support_levels:
        s.level_type = "support"

    resistance_levels = cluster_levels(pivot_highs, cluster_pct)
    for r in resistance_levels:
        r.level_type = "resistance"

    # Keep only top 3 most significant (by touch count, then proximity to current price)
    current_price = df["Close"].iloc[-1]
    support_levels.sort(key=lambda x: (-x.touch_count, abs(x.price - current_price)))
    resistance_levels.sort(key=lambda x: (-x.touch_count, abs(x.price - current_price)))

    # Filter: supports below price, resistances above price
    support_levels = [s for s in support_levels if s.price < current_price][:3]
    resistance_levels = [r for r in resistance_levels if r.price > current_price][:3]

    return support_levels, resistance_levels


def detect_rsi_divergence(df: pd.DataFrame, rsi_series: pd.Series, lookback: int = 14) -> str | None:
    """Detect bullish or bearish RSI divergence."""
    if rsi_series is None or len(df) < lookback * 2 or len(rsi_series.dropna()) < lookback * 2:
        return None

    try:
        close = df["Close"].dropna().tail(lookback * 2)
        rsi = rsi_series.dropna().tail(lookback * 2)

        if len(close) < lookback or len(rsi) < lookback:
            return None

        # Simple divergence: compare first and second half
        mid = len(close) // 2
        price_first_low = close.iloc[:mid].min()
        price_second_low = close.iloc[mid:].min()
        rsi_first_low = rsi.iloc[:mid].min()
        rsi_second_low = rsi.iloc[mid:].min()

        price_first_high = close.iloc[:mid].max()
        price_second_high = close.iloc[mid:].max()
        rsi_first_high = rsi.iloc[:mid].max()
        rsi_second_high = rsi.iloc[mid:].max()

        # Bullish divergence: price makes lower low, RSI makes higher low
        if price_second_low < price_first_low and rsi_second_low > rsi_first_low:
            return "bullish"
        # Bearish divergence: price makes higher high, RSI makes lower high
        if price_second_high > price_first_high and rsi_second_high < rsi_first_high:
            return "bearish"
    except Exception:
        pass

    return None


def compute_all_indicators(df: pd.DataFrame) -> IndicatorResult | None:
    """Compute all indicators for a single DataFrame (one symbol, one timeframe)."""
    if df is None or df.empty or len(df) < 5:
        return None

    result = IndicatorResult()

    # Current price info
    result.current_price = df["Close"].iloc[-1]
    if len(df) >= 2:
        prev_close = df["Close"].iloc[-2]
        if prev_close != 0:
            result.price_change_pct = ((result.current_price - prev_close) / prev_close) * 100

    # 52-week high/low (use available data)
    result.high_52w = df["High"].max()
    result.low_52w = df["Low"].min()

    # RSI
    rsi_series, rsi_value = compute_rsi(df)
    result.rsi_series = rsi_series
    result.rsi = rsi_value
    if rsi_value is not None:
        if rsi_value > 70:
            result.rsi_zone = "Aşırı Alım"
        elif rsi_value < 30:
            result.rsi_zone = "Aşırı Satım"
        else:
            result.rsi_zone = "Nötr"
        result.rsi_divergence = detect_rsi_divergence(df, rsi_series)

    # MACD
    macd_df, macd_vals = compute_macd(df)
    result.macd_series = macd_df
    if macd_vals:
        result.macd_line = macd_vals.get("macd_line")
        result.macd_signal = macd_vals.get("signal_line")
        result.macd_histogram = macd_vals.get("histogram")
        result.macd_crossover = macd_vals.get("crossover")

    # Bollinger Bands
    bb_df, bb_vals = compute_bollinger_bands(df)
    result.bb_series = bb_df
    if bb_vals:
        result.bb_upper = bb_vals.get("upper")
        result.bb_middle = bb_vals.get("middle")
        result.bb_lower = bb_vals.get("lower")
        result.bb_percent = bb_vals.get("percent")
        result.bb_squeeze = bb_vals.get("squeeze", False)

    # EMAs
    emas = compute_emas(df)
    result.ema20 = emas.get("ema20")
    result.ema50 = emas.get("ema50")
    result.ema200 = emas.get("ema200")
    result.ema20_series = emas.get("ema20_series")
    result.ema50_series = emas.get("ema50_series")
    result.ema200_series = emas.get("ema200_series")

    # Golden/Death cross detection
    if result.ema50_series is not None and result.ema200_series is not None:
        ema50_clean = result.ema50_series.dropna()
        ema200_clean = result.ema200_series.dropna()
        if len(ema50_clean) >= 2 and len(ema200_clean) >= 2:
            # Align by index
            common_idx = ema50_clean.index.intersection(ema200_clean.index)
            if len(common_idx) >= 2:
                e50 = ema50_clean.loc[common_idx]
                e200 = ema200_clean.loc[common_idx]
                prev_diff = e50.iloc[-2] - e200.iloc[-2]
                curr_diff = e50.iloc[-1] - e200.iloc[-1]
                if prev_diff < 0 and curr_diff >= 0:
                    result.golden_cross = True
                elif prev_diff > 0 and curr_diff <= 0:
                    result.death_cross = True

    # Price vs EMA200
    if result.ema200 is not None and result.current_price is not None:
        result.price_vs_ema200 = "above" if result.current_price > result.ema200 else "below"

    # Support & Resistance
    result.support_levels, result.resistance_levels = detect_support_resistance(df)

    return result
