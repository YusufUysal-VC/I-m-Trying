"""
ai_analyst.py — Optional Claude API integration for AI-written Turkish analysis.
Falls back to rule-based analysis silently if API call fails.
"""

import logging
import os
from typing import Optional

logger = logging.getLogger(__name__)


def get_ai_analysis(symbol: str, timeframe: str, indicator_data: dict) -> Optional[str]:
    """
    Send technical indicator data to Claude and receive a detailed Turkish analysis.
    Returns analysis text, or None if API is unavailable/fails.
    """
    try:
        import anthropic
    except ImportError:
        logger.warning("anthropic package not installed. Skipping AI analysis.")
        return None

    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        logger.warning("ANTHROPIC_API_KEY not set. Skipping AI analysis.")
        return None

    try:
        client = anthropic.Anthropic()

        prompt = f"""
Aşağıdaki teknik analiz verilerine dayanarak {symbol} enstrümanı için
{timeframe} zaman diliminde detaylı bir Türkçe analiz yaz.

Veriler:
{_format_indicator_data(indicator_data)}

Analizde şunları kapsa:
- Mevcut trend ve momentum değerlendirmesi
- Kritik destek ve direnç seviyeleri
- RSI, MACD ve Bollinger Bands yorumu
- Olası senaryolar (yükseliş / düşüş)
- Risk faktörleri

Analiz profesyonel, nesnel ve 200-300 kelime arasında olsun.
Yatırım tavsiyesi verme, sadece teknik analiz yap.
"""

        message = client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=1024,
            messages=[{"role": "user", "content": prompt}],
        )
        return message.content[0].text

    except Exception as e:
        logger.error(f"AI analysis failed for {symbol}: {e}")
        return None


def get_ai_narrative(
    symbol: str,
    short_narrative: str,
    long_narrative: str,
    long_plan_summary: str,
    short_plan_summary: str,
) -> Optional[str]:
    """
    Send narrative and action plan context to Claude for enriched strategic commentary.
    Returns 150-200 word Turkish strategic summary, or None if unavailable.
    """
    try:
        import anthropic
    except ImportError:
        return None

    if not os.environ.get("ANTHROPIC_API_KEY"):
        return None

    try:
        client = anthropic.Anthropic()

        prompt = f"""
{symbol} için aşağıdaki teknik narratifler ve aksiyon planları oluşturuldu.
Bunları değerlendirip 150-200 kelimelik Türkçe bir stratejik özet yaz.

Kısa Vade Narratif: {short_narrative}
Uzun Vade Narratif: {long_narrative}
Long Plan: {long_plan_summary}
Short Plan: {short_plan_summary}

Hangi senaryo daha güçlü görünüyor ve neden? Risk faktörlerini de belirt.
Yatırım tavsiyesi verme, teknik analiz çerçevesinde kal.
Yanıtı düz metin olarak ver, başlık veya madde işaretleri kullanma.
"""

        message = client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=512,
            messages=[{"role": "user", "content": prompt}],
        )
        return message.content[0].text

    except Exception as e:
        logger.error(f"AI narrative failed for {symbol}: {e}")
        return None


def enrich_analysis_with_ai(
    symbol: str,
    timeframe: str,
    indicator_data: dict,
    rule_based_commentary: str,
) -> str:
    """
    Attempt to get AI analysis; fall back to rule-based commentary if it fails.
    """
    ai_text = get_ai_analysis(symbol, timeframe, indicator_data)
    if ai_text:
        logger.info(f"AI analysis successful for {symbol} ({timeframe})")
        return ai_text
    return rule_based_commentary


def _format_indicator_data(data: dict) -> str:
    """Format indicator dict for prompt injection."""
    lines = []
    for key, value in data.items():
        if value is not None:
            if isinstance(value, float):
                lines.append(f"  {key}: {value:.4f}")
            elif isinstance(value, list) and value:
                formatted = [
                    f"{item.get('price', '?'):.4f} ({item.get('strength', '')})"
                    for item in value[:3]
                    if isinstance(item, dict)
                ]
                lines.append(f"  {key}: {', '.join(formatted)}")
            else:
                lines.append(f"  {key}: {value}")
    return "\n".join(lines)


def build_indicator_dict(indicator) -> dict:
    """Build a clean dict from IndicatorResult for AI prompt injection."""
    return {
        "Güncel Fiyat": indicator.current_price,
        "RSI (14)": indicator.rsi,
        "RSI Sinyal": indicator.rsi_signal,
        "RSI Iraksama": indicator.rsi_divergence,
        "MACD": indicator.macd_line,
        "MACD Signal": indicator.macd_signal,
        "MACD Histogram": indicator.macd_histogram,
        "MACD Sinyal Tipi": indicator.macd_signal_type,
        "Bollinger Üst Band": indicator.bb_upper,
        "Bollinger Orta Band": indicator.bb_middle,
        "Bollinger Alt Band": indicator.bb_lower,
        "Bollinger Bant Pozisyonu (%)": indicator.bb_pct,
        "Bollinger Sıkışması": indicator.bb_squeeze,
        "EMA 20": indicator.ema_20,
        "EMA 50": indicator.ema_50,
        "EMA 200": indicator.ema_200,
        "EMA Hizalaması": indicator.ema_alignment,
        "Altın Kesişim": indicator.golden_cross,
        "Ölüm Kesişimi": indicator.death_cross,
        "Destek Seviyeleri": indicator.support_levels,
        "Direnç Seviyeleri": indicator.resistance_levels,
    }
