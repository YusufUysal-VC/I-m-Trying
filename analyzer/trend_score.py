import math


def calculate_trend_score(df, indicators):
    """Calculate trend score from -100 to +100 based on 8 criteria."""
    score = 0

    price = indicators.get('price', 0)
    if price == 0:
        return 0

    # Price vs EMAs (+/- 15 points)
    ema20 = indicators.get('ema20', price)
    ema50 = indicators.get('ema50', price)
    ema200 = indicators.get('ema200', price)

    if not math.isnan(ema20) and price > ema20:
        score += 5
    if not math.isnan(ema50) and price > ema50:
        score += 5
    if not math.isnan(ema200):
        if price > ema200:
            score += 5
        else:
            score -= 5
    if not math.isnan(ema20) and not math.isnan(ema50):
        if ema20 > ema50:
            score += 5
        else:
            score -= 5

    # RSI (+/- 20 points)
    rsi = indicators.get('rsi', 50)
    if not math.isnan(rsi):
        if 50 < rsi < 70:
            score += 20
        elif rsi >= 70:
            score += 10
        elif 30 < rsi <= 50:
            score -= 10
        else:
            score -= 20

    # MACD (+/- 20 points)
    macd_val = indicators.get('macd', 0)
    macd_signal = indicators.get('macd_signal', 0)
    if not math.isnan(macd_val) and not math.isnan(macd_signal):
        if macd_val > macd_signal:
            score += 20
        else:
            score -= 20

    # Bollinger Bands position (+/- 15 points)
    bb_upper = indicators.get('bb_upper', 0)
    bb_lower = indicators.get('bb_lower', 0)
    if not math.isnan(bb_upper) and not math.isnan(bb_lower) and (bb_upper - bb_lower) > 0:
        bb_pos = (price - bb_lower) / (bb_upper - bb_lower)
        if 0.5 < bb_pos < 0.8:
            score += 15
        elif bb_pos >= 0.8:
            score += 5
        elif bb_pos < 0.2:
            score -= 15

    # Volume confirmation (+/- 10 points)
    vol = indicators.get('volume', 0)
    vol_ema = indicators.get('vol_ema20', 0)
    if vol and vol_ema and not math.isnan(vol_ema) and vol_ema > 0:
        if vol > vol_ema:
            score += 10
        else:
            score -= 5

    return max(-100, min(100, score))
