import math


def generate_signal(trend_score, rsi, price, bb_upper, bb_lower, ema50):
    """
    Generate trading signal.
    Returns: { 'signal': 'AL'|'SAT'|'İZLE'|'NÖTR', 'color': str, 'emoji': str }
    """
    signal = 'NÖTR'

    # Handle NaN values
    if math.isnan(rsi):
        rsi = 50
    if math.isnan(ema50):
        ema50 = price

    if trend_score >= 40 and rsi < 65 and price > ema50:
        signal = 'AL'
    elif trend_score <= -40 and rsi > 55:
        signal = 'SAT'
    elif 20 <= trend_score < 40:
        signal = 'İZLE'
    elif -20 < trend_score < 20:
        signal = 'NÖTR'

    mapping = {
        'AL':   {'color': '#00ff88', 'emoji': '🟢'},
        'SAT':  {'color': '#ff4444', 'emoji': '🔴'},
        'İZLE': {'color': '#ffaa00', 'emoji': '🟡'},
        'NÖTR': {'color': '#888888', 'emoji': '⚪'},
    }
    return {'signal': signal, **mapping[signal]}
