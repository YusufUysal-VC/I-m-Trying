"""
Rule-based Turkish commentary generator.
Generates structured Turkish paragraphs for each instrument + timeframe combination.
"""

import logging

from .indicators import IndicatorResult
from .trend_analyzer import TrendResult
from .narrative_engine import NarrativeResult

logger = logging.getLogger(__name__)


def generate_commentary(symbol: str, timeframe: str, indicators: IndicatorResult,
                        trend: TrendResult, narrative: NarrativeResult | None = None) -> str:
    """
    Generate a structured Turkish paragraph (150-250 words) covering:
    1. Genel Durum
    2. Teknik Göstergeler
    3. Destek/Direnç
    4. Trend Analizi
    5. Önemli Notlar
    6. Kısa Özet
    """
    if indicators is None or indicators.current_price is None:
        return f"{symbol} için {timeframe} zaman diliminde yeterli veri bulunamadı."

    sections = []
    price = indicators.current_price

    # 1. Genel Durum
    change_str = ""
    if indicators.price_change_pct is not None:
        direction = "yükselişle" if indicators.price_change_pct > 0 else "düşüşle"
        change_str = f" Son dönemde %{abs(indicators.price_change_pct):.2f} {direction} {price:.4g} seviyesinden işlem görüyor."
    else:
        change_str = f" {price:.4g} seviyesinden işlem görüyor."

    trend_label = trend.label if trend else "Belirsiz"
    sections.append(f"Genel Durum: {symbol} {timeframe} bazında {trend_label} eğiliminde.{change_str}")

    # 2. Teknik Göstergeler
    tech_parts = []

    # RSI
    if indicators.rsi is not None:
        rsi = indicators.rsi
        if rsi > 70:
            tech_parts.append(f"RSI {rsi:.1f} ile aşırı alım bölgesinde seyrediyor, kısa vadede satış baskısı gelebilir.")
        elif rsi < 30:
            tech_parts.append(f"RSI {rsi:.1f} ile aşırı satım bölgesinde, teknik toparlanma ihtimali artmış durumda.")
        elif rsi > 60:
            tech_parts.append(f"RSI {rsi:.1f} ile güçlü bölgede, momentum alıcıların lehine.")
        elif rsi < 40:
            tech_parts.append(f"RSI {rsi:.1f} ile zayıf bölgede, satıcılar baskın durumda.")
        else:
            tech_parts.append(f"RSI {rsi:.1f} ile nötr bölgede.")

    # MACD
    if indicators.macd_histogram is not None:
        hist = indicators.macd_histogram
        if indicators.macd_crossover == "bullish_cross":
            tech_parts.append("MACD boğa kesişimi gerçekleştirdi, yukarı yönlü momentum artıyor.")
        elif indicators.macd_crossover == "bearish_cross":
            tech_parts.append("MACD ayı kesişimi gerçekleştirdi, aşağı yönlü baskı güçleniyor.")
        elif hist > 0:
            tech_parts.append("MACD histogramı pozitif bölgede, trend yukarı yönlü.")
        else:
            tech_parts.append("MACD histogramı negatif bölgede, trend aşağı yönlü.")

    # Bollinger Bands
    if indicators.bb_percent is not None:
        bp = indicators.bb_percent
        if bp > 80:
            tech_parts.append(f"Fiyat Bollinger Bandının üst bölgesinde (%{bp:.0f}), aşırı gerilme riski mevcut.")
        elif bp < 20:
            tech_parts.append(f"Fiyat Bollinger Bandının alt bölgesinde (%{bp:.0f}), tepki potansiyeli var.")
        else:
            tech_parts.append(f"Fiyat Bollinger Bandının orta bölgesinde (%{bp:.0f}).")

        if indicators.bb_squeeze:
            tech_parts.append("Bollinger Band sıkışması tespit edildi — yakın vadede volatilite artışı bekleniyor.")

    if tech_parts:
        sections.append("Teknik Göstergeler: " + " ".join(tech_parts))

    # 3. Destek/Direnç
    sr_parts = []
    if indicators.support_levels:
        supports = indicators.support_levels[:2]
        support_strs = [f"{s.price:.4g} ({s.strength})" for s in supports]
        sr_parts.append(f"Destek seviyeleri: {', '.join(support_strs)}.")

    if indicators.resistance_levels:
        resistances = indicators.resistance_levels[:2]
        resistance_strs = [f"{r.price:.4g} ({r.strength})" for r in resistances]
        sr_parts.append(f"Direnç seviyeleri: {', '.join(resistance_strs)}.")

    if sr_parts:
        sections.append("Destek/Direnç: " + " ".join(sr_parts))
    else:
        sections.append("Destek/Direnç: Belirgin destek ve direnç seviyeleri tespit edilemedi.")

    # 4. Trend Analizi
    trend_parts = []
    trend_parts.append(f"Trend skoru: {trend.score}/100 ({trend.label}).")

    if indicators.ema20 is not None and indicators.ema50 is not None and indicators.ema200 is not None:
        if indicators.ema20 > indicators.ema50 > indicators.ema200:
            trend_parts.append("EMA'lar boğa diziliminde (20 > 50 > 200), trend güçlü.")
        elif indicators.ema20 < indicators.ema50 < indicators.ema200:
            trend_parts.append("EMA'lar ayı diziliminde (20 < 50 < 200), aşağı yönlü baskı hakim.")
        else:
            trend_parts.append("EMA'lar karışık sinyal veriyor.")

    if indicators.price_vs_ema200 == "above":
        trend_parts.append(f"Fiyat EMA200 ({indicators.ema200:.4g}) üzerinde, ana trend yukarı.")
    elif indicators.price_vs_ema200 == "below" and indicators.ema200 is not None:
        trend_parts.append(f"Fiyat EMA200 ({indicators.ema200:.4g}) altında, ana trend aşağı.")

    sections.append("Trend Analizi: " + " ".join(trend_parts))

    # 5. Önemli Notlar
    notes = []
    if indicators.rsi_divergence == "bullish":
        notes.append("RSI boğa uyumsuzluğu tespit edildi — fiyat düşerken RSI yükseliyor, potansiyel dönüş sinyali.")
    elif indicators.rsi_divergence == "bearish":
        notes.append("RSI ayı uyumsuzluğu tespit edildi — fiyat yükselirken RSI düşüyor, güç kaybı sinyali.")
    if indicators.golden_cross:
        notes.append("Altın Çapraz (Golden Cross) oluştu — uzun vadeli boğa sinyali.")
    if indicators.death_cross:
        notes.append("Ölüm Çaprazı (Death Cross) oluştu — uzun vadeli ayı sinyali.")
    if indicators.bb_squeeze:
        notes.append("Bollinger Band sıkışması devam ediyor.")
    if indicators.macd_crossover:
        cross_type = "Boğa" if indicators.macd_crossover == "bullish_cross" else "Ayı"
        notes.append(f"MACD {cross_type} kesişimi yakın zamanda gerçekleşti.")

    if notes:
        sections.append("Önemli Notlar: " + " ".join(notes))

    # 6. Kısa Özet
    summary = _generate_short_summary(indicators, trend)
    sections.append(f"Kısa Özet: {summary}")

    return "\n\n".join(sections)


def _generate_short_summary(indicators: IndicatorResult, trend: TrendResult) -> str:
    """Generate a 1-2 sentence conclusion summary."""
    parts = []

    # Main direction
    if trend.score >= 50:
        parts.append("Güçlü yükseliş trendi devam ediyor")
    elif trend.score >= 20:
        parts.append("Yükseliş eğilimi mevcut")
    elif trend.score <= -50:
        parts.append("Güçlü düşüş trendi hakim")
    elif trend.score <= -20:
        parts.append("Düşüş eğilimi baskın")
    else:
        parts.append("Yatay seyir devam ediyor")

    # Key condition
    if indicators.rsi is not None:
        if indicators.rsi > 70:
            parts.append("ancak RSI aşırı alım bölgesinde, dikkatli olunmalı")
        elif indicators.rsi < 30:
            parts.append("RSI aşırı satım bölgesinde, teknik toparlanma fırsatı olabilir")

    if indicators.resistance_levels and indicators.current_price is not None:
        r1 = indicators.resistance_levels[0].price
        pct = ((r1 - indicators.current_price) / indicators.current_price) * 100
        if 0 < pct < 3:
            parts.append(f"yakın direnç {r1:.4g} seviyesi kritik")

    if indicators.support_levels and indicators.current_price is not None:
        s1 = indicators.support_levels[0].price
        pct = ((indicators.current_price - s1) / indicators.current_price) * 100
        if 0 < pct < 3:
            parts.append(f"yakın destek {s1:.4g} seviyesi takip edilmeli")

    return ", ".join(parts) + "."
