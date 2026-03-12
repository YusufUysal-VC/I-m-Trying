from scipy.signal import argrelextrema
import numpy as np


def find_levels(df, order=5, n_levels=5):
    """Find support and resistance levels using pivot points + clustering."""
    if df is None or df.empty or len(df) < order * 2 + 1:
        price = df['Close'].iloc[-1] if df is not None and not df.empty else 0
        return {
            "resistance": [price * 1.02, price * 1.05],
            "support": [price * 0.98, price * 0.95]
        }

    highs = df['High'].values
    lows = df['Low'].values

    # Local maximum and minimum points
    local_max_idx = argrelextrema(highs, np.greater, order=order)[0]
    local_min_idx = argrelextrema(lows, np.less, order=order)[0]

    resistance_levels = highs[local_max_idx].tolist()
    support_levels = lows[local_min_idx].tolist()

    # Cluster nearby levels (0.5% tolerance)
    def cluster(levels, tolerance=0.005):
        if not levels:
            return []
        levels = sorted(levels)
        clusters = [[levels[0]]]
        for lvl in levels[1:]:
            if abs(lvl - clusters[-1][-1]) / max(clusters[-1][-1], 1e-10) < tolerance:
                clusters[-1].append(lvl)
            else:
                clusters.append([lvl])
        return [float(np.mean(c)) for c in clusters]

    current_price = float(df['Close'].iloc[-1])
    all_resistance = [r for r in cluster(resistance_levels) if r > current_price]
    all_support = [s for s in cluster(support_levels) if s < current_price]

    # Ensure we always have some levels
    if not all_resistance:
        all_resistance = [current_price * 1.02, current_price * 1.05]
    if not all_support:
        all_support = [current_price * 0.98, current_price * 0.95]

    return {
        "resistance": sorted(all_resistance)[:n_levels],
        "support": sorted(all_support, reverse=True)[:n_levels]
    }
