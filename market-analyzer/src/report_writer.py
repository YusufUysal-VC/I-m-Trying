"""
report_writer.py — Rule-based Turkish commentary generator.
Produces structured 150-250 word Turkish analysis paragraphs per instrument/timeframe.
"""

import logging
from typing import Optional

from src.indicators import IndicatorResult
from src.trend_analyzer import TrendResult, InstrumentAnalysis
from src.narrative_engine import NarrativeResult

logger = logging.getLogger(__name__)


def generate_commentary(
    indicator: IndicatorResult,
    trend: TrendResult,
    symbol: str,
    timeframe: str,
) -> str:
    """
    Generate a structured Turkish analysis paragraph for one instrument + timeframe.
    Covers: general status, indicators, S/R levels, trend, special signals, summary.
    """
    parts = []
    price = indicator.current_price
    currency_symbol = _guess_currency_display(symbol)

    # 1. Genel Durum
    trend_label = trend.label if trend else "Yatay"
    general = f"{symbol}, {_fmt_price(price)}{currency_symbol} seviyesinde işlem görüyor. "
    general += f"Güncel teknik görünüm '{trend_label}' olarak değerlendirilmektedir."
    parts.append(f"📊 Genel Durum: {general}")

    # 2. RSI
    rsi_comment = _rsi_comment(indicator.rsi, indicator.rsi_signal, indicator.rsi_divergence)
    parts.append(rsi_comment)

    # 3. MACD
    macd_comment = _macd_comment(indicator.macd_line, indicator.macd_signal, indicator.macd_signal_type)
    parts.append(macd_comment)

    # 4. Bollinger Bands
    bb_comment = _bb_comment(indicator.bb_pct, indicator.bb_squeeze, indicator.bb_upper, indicator.bb_lower)
    parts.append(bb_comment)

    # 5. EMA ve Destek/Direnç
    ema_comment = _ema_comment(price, indicator.ema_20, indicator.ema_50, indicator.ema_200, indicator.ema_alignment)
    parts.append(ema_comment)

    # 6. Destek/Direnç seviyeleri
    sr_comment = _sr_comment(indicator.support_levels, indicator.resistance_levels)
    parts.append(sr_comment)

    # 7. Özel sinyaller
    special = _special_signals_comment(indicator)
    if special:
        parts.append(special)

    # 8. Kısa özet
    summary = _build_summary(indicator, trend)
    parts.append(f"💡 Özet: {summary}")

    return " ".join(parts)


def _rsi_comment(rsi: Optional[float], signal: str, divergence: str) -> str:
    if rsi is None:
        return "RSI: Yeterli veri yok."

    if signal == "overbought":
        comment = f"RSI {rsi:.1f} ile aşırı alım bölgesinde seyrediyor; kısa vadede satış baskısı gelebilir."
    elif signal == "oversold":
        comment = f"RSI {rsi:.1f} ile aşırı satım bölgesinde; teknik toparlanma ihtimali artmış durumda."
    else:
        comment = f"RSI {rsi:.1f} ile nötr bölgede seyretmektedir."

    if divergence == "bullish":
        comment += " Fiyat düşerken RSI'nın yükselmesi pozitif ıraksama işareti veriyor."
    elif divergence == "bearish":
        comment += " Fiyat yükselirken RSI'nın gerilemesi negatif ıraksama uyarısı veriyor."

    return comment


def _macd_comment(macd_line: Optional[float], macd_sig: Optional[float], signal_type: str) -> str:
    if macd_line is None:
        return "MACD: Yeterli veri yok."

    if signal_type == "bullish_cross":
        return f"MACD, sinyal çizgisini yukarı kesiyor — güçlü alım sinyali oluştu. MACD: {macd_line:.4f}."
    elif signal_type == "bearish_cross":
        return f"MACD, sinyal çizgisini aşağı kesiyor — güçlü satım sinyali üretildi. MACD: {macd_line:.4f}."
    elif signal_type == "bullish":
        return f"MACD ({macd_line:.4f}) sinyal çizgisinin üzerinde, yükseliş momentumu korunuyor."
    elif signal_type == "bearish":
        return f"MACD ({macd_line:.4f}) sinyal çizgisinin altında, düşüş baskısı sürmekte."
    return f"MACD nötr bölgede seyretmektedir. ({macd_line:.4f})"


def _bb_comment(
    bb_pct: Optional[float],
    squeeze: bool,
    bb_upper: Optional[float],
    bb_lower: Optional[float],
) -> str:
    parts = []

    if squeeze:
        parts.append("Bollinger Bantları sıkışma gösteriyor; yakın vadede volatilite artışı ve güçlü bir fiyat hareketi bekleniyor.")
    elif bb_pct is not None:
        if bb_pct > 80:
            parts.append(f"Bollinger Bantları'nda fiyat üst banda yakın (%{bb_pct:.0f} konumda); aşırı alım bölgesi.")
        elif bb_pct < 20:
            parts.append(f"Bollinger Bantları'nda fiyat alt banda yakın (%{bb_pct:.0f} konumda); aşırı satım bölgesi.")
        else:
            parts.append(f"Fiyat Bollinger Bantları içinde orta seviyede seyretmektedir (%{bb_pct:.0f} konumda).")

    if bb_upper and bb_lower:
        parts.append(f"Üst bant: {_fmt_price(bb_upper)}, Alt bant: {_fmt_price(bb_lower)}.")

    return " ".join(parts) if parts else "Bollinger Bantları: Yeterli veri yok."


def _ema_comment(
    price: float,
    ema_20: Optional[float],
    ema_50: Optional[float],
    ema_200: Optional[float],
    alignment: str,
) -> str:
    parts = []

    if ema_200:
        if price > ema_200:
            parts.append(f"Fiyat 200 günlük EMA ({_fmt_price(ema_200)}) üzerinde — uzun vadeli yükseliş yapısı korunuyor.")
        else:
            parts.append(f"Fiyat 200 günlük EMA ({_fmt_price(ema_200)}) altında — uzun vadeli baskı sürüyor.")

    if ema_50:
        if price > ema_50:
            parts.append(f"EMA50 ({_fmt_price(ema_50)}) üzerinde işlem görüyor.")
        else:
            parts.append(f"EMA50 ({_fmt_price(ema_50)}) altında işlem görüyor.")

    if alignment == "bullish":
        parts.append("EMA 20 > EMA 50 > EMA 200 uyumu yükseliş trendini destekliyor.")
    elif alignment == "bearish":
        parts.append("EMA 20 < EMA 50 < EMA 200 uyumu düşüş trendine işaret ediyor.")

    return " ".join(parts) if parts else "EMA seviyeleri: Yeterli veri yok."


def _sr_comment(supports: list, resistances: list) -> str:
    parts = []

    if supports:
        sup_strs = [f"{_fmt_price(s['price'])} ({s['strength']})" for s in supports[:2]]
        parts.append(f"Önemli destek seviyeleri: {', '.join(sup_strs)}.")

    if resistances:
        res_strs = [f"{_fmt_price(r['price'])} ({r['strength']})" for r in resistances[:2]]
        parts.append(f"Önemli direnç seviyeleri: {', '.join(res_strs)}.")

    return " ".join(parts) if parts else "Belirgin destek/direnç seviyesi tespit edilemedi."


def _special_signals_comment(indicator: IndicatorResult) -> str:
    signals = []

    if indicator.golden_cross:
        signals.append("⭐ Altın Kesişim: EMA50, EMA200'ü yukarı kesti — güçlü uzun vadeli alım sinyali.")
    if indicator.death_cross:
        signals.append("⚠️ Ölüm Kesişimi: EMA50, EMA200'ü aşağı kesti — uzun vadeli satış baskısı uyarısı.")
    if indicator.bb_squeeze:
        signals.append("🔔 Bollinger Sıkışması: Volatilite tarihsel düşük seviyede — yakında güçlü hareket bekleniyor.")
    if indicator.rsi_divergence == "bullish":
        signals.append("📈 Pozitif Iraksama: Fiyat düşerken RSI yükseliyor — dönüş habercisi.")
    if indicator.rsi_divergence == "bearish":
        signals.append("📉 Negatif Iraksama: Fiyat yükselirken RSI düşüyor — momentum zayıflıyor.")

    return " ".join(signals)


def _build_summary(indicator: IndicatorResult, trend: TrendResult) -> str:
    """1-2 sentence conclusion."""
    parts = []
    price = indicator.current_price

    if trend:
        if trend.label == "Güçlü Yükseliş":
            parts.append("Tüm göstergeler yükseliş yönünde uyum içinde.")
        elif trend.label == "Yükseliş":
            parts.append("Genel görünüm olumlu, ancak dikkatli izleme önerilir.")
        elif trend.label == "Güçlü Düşüş":
            parts.append("Satış baskısı baskın, yeni bir yükseliş için sinyal beklenmeli.")
        elif trend.label == "Düşüş":
            parts.append("Düşüş trendi sürmekte; giriş için net bir toparlanma sinyali beklenmeli.")
        else:
            parts.append("Yatay hareket devam ediyor, belirgin bir yön için kırılım beklenebilir.")

    if indicator.rsi and indicator.rsi > 70 and indicator.ema_200 and price > indicator.ema_200:
        parts.append("RSI aşırı alım bölgesinde, 200-günlük EMA desteği kırılmazsa yükseliş sürebilir.")
    elif indicator.rsi and indicator.rsi < 30:
        parts.append("Aşırı satım sonrası teknik toparlanma fırsatı değerlendirilebilir.")

    return " ".join(parts) if parts else "Piyasa normal koşullarda seyretmektedir."


def generate_card_summary(
    analysis: InstrumentAnalysis,
    narrative: NarrativeResult,
) -> dict:
    """
    Generate the Layer 2 plain Turkish card summary.
    Returns dict with action text, scenario summary, entry/target/stop info.
    """
    plan = narrative.long_plan if narrative.dominant_direction == "LONG" else narrative.short_plan

    summary = {
        "action_status": narrative.action_status,
        "action_reason": narrative.action_reason,
        "entry_text": "",
        "target_1_text": "",
        "target_2_text": "",
        "stop_text": "",
        "rr_text": "",
        "scenario_branches": narrative.scenario_branches,
    }

    if plan and plan.is_valid:
        price = analysis.current_price
        summary["entry_text"] = f"{_fmt_price(plan.entry_zone_low)} – {_fmt_price(plan.entry_zone_high)} aralığında giriş"
        summary["target_1_text"] = f"Hedef 1: {_fmt_price(plan.target_1)} ({_pct(price, plan.target_1)})"
        summary["target_2_text"] = f"Hedef 2: {_fmt_price(plan.target_2)} ({_pct(price, plan.target_2)})"
        summary["stop_text"] = f"Stop: {_fmt_price(plan.stop_loss)} ({_pct(price, plan.stop_loss)})"
        summary["rr_text"] = f"R:R 1:{plan.risk_reward_t1}"

    return summary


def _guess_currency_display(symbol: str) -> str:
    """Guess currency symbol for display."""
    if symbol.endswith(".IS"):
        return "₺"
    elif "USD" in symbol or symbol.endswith("=X"):
        return "$"
    elif "EUR" in symbol:
        return "€"
    elif "GBP" in symbol:
        return "£"
    return ""


def _fmt_price(price: float) -> str:
    if not price:
        return "N/A"
    if price >= 1000:
        return f"{price:,.0f}"
    elif price >= 10:
        return f"{price:.2f}"
    elif price >= 1:
        return f"{price:.3f}"
    else:
        return f"{price:.5f}"


def _pct(entry: float, target: float) -> str:
    if entry and entry > 0:
        pct = (target - entry) / entry * 100
        sign = "+" if pct >= 0 else ""
        return f"{sign}{pct:.1f}%"
    return ""
