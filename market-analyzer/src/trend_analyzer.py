"""
trend_analyzer.py — Trend direction scoring, signal generation, and overall bias.
Computes a Trend Score from -100 to +100 based on multiple indicator signals.
"""

import logging
from dataclasses import dataclass, field
from typing import Optional

import pandas as pd

from src.indicators import IndicatorResult

logger = logging.getLogger(__name__)

# Trend score label mapping
TREND_LABELS = [
    (70, 100, "Güçlü Yükseliş"),
    (30, 69, "Yükseliş"),
    (-29, 29, "Yatay"),
    (-69, -30, "Düşüş"),
    (-100, -70, "Güçlü Düşüş"),
]


@dataclass
class TrendResult:
    """Trend analysis result for a single timeframe."""
    symbol: str
    timeframe: str
    score: int = 0              # -100 to +100
    label: str = "Yatay"
    score_breakdown: dict = field(default_factory=dict)

    # Derived signals
    price_vs_ema200: str = "neutral"    # "above" | "below" | "at"
    price_vs_ema50: str = "neutral"
    price_vs_ema20: str = "neutral"
    momentum: str = "neutral"           # "accelerating" | "decelerating" | "neutral"

    # Breakout detection
    above_recent_high: bool = False
    below_recent_low: bool = False

    # Multi-timeframe alignment (filled later)
    aligned_timeframes: int = 0         # How many timeframes agree on direction


@dataclass
class InstrumentAnalysis:
    """Complete analysis for one instrument across all timeframes."""
    symbol: str
    display_name: str
    category: str
    currency: str
    current_price: float = 0.0
    price_change_pct: float = 0.0

    # Per-timeframe results
    indicators: dict = field(default_factory=dict)    # tf_label -> IndicatorResult
    trends: dict = field(default_factory=dict)         # tf_label -> TrendResult

    # Primary timeframe (daily by default)
    primary_tf: str = "Günlük"

    # Aggregated signals
    overall_trend: str = "Yatay"
    overall_score: float = 0.0
    dominant_rsi: Optional[float] = None
    aligned_tf_count: int = 0


def compute_trend_score(indicator: IndicatorResult) -> TrendResult:
    """
    Compute trend score from -100 to +100 using multiple signal components.
    Returns a TrendResult with score, label, and breakdown.
    """
    result = TrendResult(symbol=indicator.symbol, timeframe=indicator.timeframe)
    breakdown = {}
    score = 0
    price = indicator.current_price

    # EMA-based scoring
    if indicator.ema_200 and price:
        if price > indicator.ema_200:
            score += 20
            breakdown["price_vs_ema200"] = +20
            result.price_vs_ema200 = "above"
        else:
            score -= 20
            breakdown["price_vs_ema200"] = -20
            result.price_vs_ema200 = "below"

    if indicator.ema_50 and price:
        if price > indicator.ema_50:
            score += 15
            breakdown["price_vs_ema50"] = +15
            result.price_vs_ema50 = "above"
        else:
            score -= 15
            breakdown["price_vs_ema50"] = -15
            result.price_vs_ema50 = "below"

    if indicator.ema_20 and price:
        if price > indicator.ema_20:
            score += 10
            breakdown["price_vs_ema20"] = +10
            result.price_vs_ema20 = "above"
        else:
            score -= 10
            breakdown["price_vs_ema20"] = -10
            result.price_vs_ema20 = "below"

    # EMA alignment
    if indicator.ema_alignment == "bullish":
        score += 15
        breakdown["ema_alignment"] = +15
    elif indicator.ema_alignment == "bearish":
        score -= 15
        breakdown["ema_alignment"] = -15

    # RSI scoring
    if indicator.rsi is not None:
        if indicator.rsi > 50:
            score += 10
            breakdown["rsi"] = +10
        else:
            score -= 10
            breakdown["rsi"] = -10

    # MACD scoring
    if indicator.macd_signal_type in ("bullish_cross", "bullish"):
        score += 10
        breakdown["macd"] = +10
    elif indicator.macd_signal_type in ("bearish_cross", "bearish"):
        score -= 10
        breakdown["macd"] = -10

    # Breakout detection (compare against recent period)
    df = indicator.df
    if df is not None and len(df) > 20:
        recent_high = df["High"].iloc[-21:-1].max()
        recent_low = df["Low"].iloc[-21:-1].min()

        if price > recent_high:
            score += 15
            breakdown["breakout_high"] = +15
            result.above_recent_high = True
        elif price < recent_low:
            score -= 15
            breakdown["breakdown_low"] = -15
            result.below_recent_low = True

    # Clamp to [-100, +100]
    score = max(-100, min(100, score))
    result.score = score
    result.score_breakdown = breakdown
    result.label = _score_to_label(score)

    # Momentum: compare RSI trend over last few bars
    if df is not None and "RSI" in df.columns and len(df) >= 5:
        recent_rsi = df["RSI"].dropna().tail(5)
        if len(recent_rsi) >= 3:
            if recent_rsi.iloc[-1] > recent_rsi.iloc[-3]:
                result.momentum = "accelerating"
            elif recent_rsi.iloc[-1] < recent_rsi.iloc[-3]:
                result.momentum = "decelerating"

    return result


def _score_to_label(score: int) -> str:
    for low, high, label in TREND_LABELS:
        if low <= score <= high:
            return label
    return "Yatay"


def compute_instrument_analysis(
    symbol: str,
    display_name: str,
    category: str,
    currency: str,
    all_indicators: dict,  # tf_label -> IndicatorResult
    current_price: float,
    price_change_pct: float,
) -> InstrumentAnalysis:
    """
    Aggregate all timeframe indicators into a single InstrumentAnalysis.
    Computes per-timeframe trend scores and overall alignment.
    """
    analysis = InstrumentAnalysis(
        symbol=symbol,
        display_name=display_name,
        category=category,
        currency=currency,
        current_price=current_price,
        price_change_pct=price_change_pct or 0.0,
    )

    trend_scores = []
    bullish_count = 0
    bearish_count = 0

    for tf_label, indicator in all_indicators.items():
        if indicator is None:
            continue
        analysis.indicators[tf_label] = indicator
        trend = compute_trend_score(indicator)
        analysis.trends[tf_label] = trend
        trend_scores.append(trend.score)

        if trend.score > 20:
            bullish_count += 1
        elif trend.score < -20:
            bearish_count += 1

    # Overall score = weighted average (daily has most weight)
    if trend_scores:
        weights = {
            "Günlük": 3,
            "Haftalık": 2,
            "Aylık": 1,
            "3 Aylık": 1,
            "Yıllık": 1,
            "5 Yıllık": 1,
        }
        total_weight = 0
        weighted_sum = 0
        for tf, trend in analysis.trends.items():
            w = weights.get(tf, 1)
            weighted_sum += trend.score * w
            total_weight += w
        analysis.overall_score = weighted_sum / total_weight if total_weight > 0 else 0
        analysis.overall_trend = _score_to_label(int(analysis.overall_score))

    analysis.aligned_tf_count = max(bullish_count, bearish_count)

    # Set primary timeframe RSI
    primary = analysis.indicators.get("Günlük") or analysis.indicators.get("Haftalık")
    if primary:
        analysis.dominant_rsi = primary.rsi

    return analysis
