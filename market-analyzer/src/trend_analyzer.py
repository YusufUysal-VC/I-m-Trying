"""
Trend direction analysis, scoring system, and signal generation.
Computes a Trend Score from -100 to +100 for each timeframe.
"""

import logging
from dataclasses import dataclass

from .indicators import IndicatorResult

logger = logging.getLogger(__name__)

TREND_LABELS = {
    (70, 101): "Güçlü Yükseliş",
    (30, 70): "Yükseliş",
    (-29, 30): "Yatay",
    (-69, -29): "Düşüş",
    (-101, -69): "Güçlü Düşüş",
}


@dataclass
class TrendResult:
    score: int = 0
    label: str = "Yatay"
    components: dict = None  # Breakdown of score components
    signals: list = None  # List of notable signals

    def __post_init__(self):
        if self.components is None:
            self.components = {}
        if self.signals is None:
            self.signals = []


def score_to_label(score: int) -> str:
    """Map a trend score to its Turkish label."""
    if score >= 70:
        return "Güçlü Yükseliş"
    elif score >= 30:
        return "Yükseliş"
    elif score >= -29:
        return "Yatay"
    elif score >= -69:
        return "Düşüş"
    else:
        return "Güçlü Düşüş"


def compute_trend_score(indicators: IndicatorResult, df=None) -> TrendResult:
    """
    Compute trend score from -100 to +100 based on indicator data.

    Scoring breakdown:
      +20 if price > EMA200
      +15 if price > EMA50
      +10 if price > EMA20
      +15 if EMA20 > EMA50 > EMA200 (bullish alignment)
      -15 if EMA20 < EMA50 < EMA200 (bearish alignment)
      +10 if RSI > 50, -10 if RSI < 50
      +10 if MACD > Signal, -10 if below
      +15 if breakout above previous high, -15 if below key support
    """
    if indicators is None:
        return TrendResult()

    result = TrendResult()
    score = 0
    price = indicators.current_price

    if price is None:
        return result

    # Price vs EMA200
    if indicators.ema200 is not None:
        if price > indicators.ema200:
            score += 20
            result.components["price_vs_ema200"] = +20
            result.signals.append("Fiyat EMA200 üzerinde (yükseliş eğilimi)")
        else:
            score -= 20
            result.components["price_vs_ema200"] = -20
            result.signals.append("Fiyat EMA200 altında (düşüş eğilimi)")

    # Price vs EMA50
    if indicators.ema50 is not None:
        if price > indicators.ema50:
            score += 15
            result.components["price_vs_ema50"] = +15
        else:
            score -= 15
            result.components["price_vs_ema50"] = -15

    # Price vs EMA20
    if indicators.ema20 is not None:
        if price > indicators.ema20:
            score += 10
            result.components["price_vs_ema20"] = +10
        else:
            score -= 10
            result.components["price_vs_ema20"] = -10

    # EMA alignment
    if indicators.ema20 is not None and indicators.ema50 is not None and indicators.ema200 is not None:
        if indicators.ema20 > indicators.ema50 > indicators.ema200:
            score += 15
            result.components["ema_alignment"] = +15
            result.signals.append("EMA'lar boğa diziliminde (20 > 50 > 200)")
        elif indicators.ema20 < indicators.ema50 < indicators.ema200:
            score -= 15
            result.components["ema_alignment"] = -15
            result.signals.append("EMA'lar ayı diziliminde (20 < 50 < 200)")

    # RSI
    if indicators.rsi is not None:
        if indicators.rsi > 50:
            score += 10
            result.components["rsi"] = +10
        else:
            score -= 10
            result.components["rsi"] = -10

    # MACD
    if indicators.macd_line is not None and indicators.macd_signal is not None:
        if indicators.macd_line > indicators.macd_signal:
            score += 10
            result.components["macd"] = +10
            result.signals.append("MACD sinyal çizgisinin üzerinde")
        else:
            score -= 10
            result.components["macd"] = -10
            result.signals.append("MACD sinyal çizgisinin altında")

    # Breakout/breakdown detection
    if df is not None and len(df) >= 5:
        recent_high = df["High"].tail(20).max() if len(df) >= 20 else df["High"].max()
        recent_low = df["Low"].tail(20).min() if len(df) >= 20 else df["Low"].min()

        if price >= recent_high * 0.99:  # Near or above recent high
            score += 15
            result.components["breakout"] = +15
            result.signals.append("Son dönem zirvesine yakın / kırılım")
        elif price <= recent_low * 1.01:  # Near or below recent low
            score -= 15
            result.components["breakdown"] = -15
            result.signals.append("Son dönem dibine yakın / kırılım aşağı")

    # Special signals
    if indicators.golden_cross:
        result.signals.append("Altın Çapraz (Golden Cross) oluştu")
    if indicators.death_cross:
        result.signals.append("Ölüm Çaprazı (Death Cross) oluştu")
    if indicators.macd_crossover == "bullish_cross":
        result.signals.append("MACD boğa kesişimi")
    elif indicators.macd_crossover == "bearish_cross":
        result.signals.append("MACD ayı kesişimi")
    if indicators.bb_squeeze:
        result.signals.append("Bollinger Band sıkışması — volatilite artışı bekleniyor")
    if indicators.rsi_divergence == "bullish":
        result.signals.append("RSI boğa uyumsuzluğu (bullish divergence)")
    elif indicators.rsi_divergence == "bearish":
        result.signals.append("RSI ayı uyumsuzluğu (bearish divergence)")

    # Clamp score to -100..+100
    score = max(-100, min(100, score))
    result.score = score
    result.label = score_to_label(score)

    return result


def get_trend_emoji(label: str) -> str:
    """Return an emoji arrow for the trend label."""
    mapping = {
        "Güçlü Yükseliş": "▲▲",
        "Yükseliş": "▲",
        "Yatay": "►",
        "Düşüş": "▼",
        "Güçlü Düşüş": "▼▼",
    }
    return mapping.get(label, "►")


def get_trend_color(label: str) -> str:
    """Return a CSS color for the trend label."""
    mapping = {
        "Güçlü Yükseliş": "#00b894",
        "Yükseliş": "#00cec9",
        "Yatay": "#fdcb6e",
        "Düşüş": "#e17055",
        "Güçlü Düşüş": "#d63031",
    }
    return mapping.get(label, "#636e72")


def compute_timeframe_alignment(trend_results: dict[str, TrendResult]) -> dict:
    """
    Check how many timeframes agree on the direction.
    Returns alignment info used by the narrative engine.
    """
    bullish_count = 0
    bearish_count = 0
    neutral_count = 0

    for tf_name, trend in trend_results.items():
        if trend.score >= 30:
            bullish_count += 1
        elif trend.score <= -30:
            bearish_count += 1
        else:
            neutral_count += 1

    total = len(trend_results)
    dominant = "bullish" if bullish_count > bearish_count else "bearish" if bearish_count > bullish_count else "neutral"

    return {
        "bullish_count": bullish_count,
        "bearish_count": bearish_count,
        "neutral_count": neutral_count,
        "total": total,
        "dominant": dominant,
        "alignment_score": max(bullish_count, bearish_count) / total if total > 0 else 0,
    }
