"""
Optional Claude API integration for richer AI-written analysis.
Activated with --ai flag. Falls back to rule-based analysis silently on failure.
"""

import logging
import os

logger = logging.getLogger(__name__)


def is_ai_available() -> bool:
    """Check if the Anthropic API key is configured."""
    return bool(os.environ.get("ANTHROPIC_API_KEY"))


def get_ai_analysis(symbol: str, timeframe: str, indicator_data: dict) -> str | None:
    """
    Send technical data to Claude and receive a detailed Turkish analysis.
    Returns None on failure (caller should fall back to rule-based analysis).
    """
    try:
        import anthropic
    except ImportError:
        logger.warning("anthropic package not installed. Skipping AI analysis.")
        return None

    if not is_ai_available():
        logger.info("ANTHROPIC_API_KEY not set. Skipping AI analysis.")
        return None

    try:
        client = anthropic.Anthropic()

        prompt = f"""Aşağıdaki teknik analiz verilerine dayanarak {symbol} enstrümanı için
{timeframe} zaman diliminde detaylı bir Türkçe analiz yaz.

Veriler:
{indicator_data}

Analizde şunları kapsa:
- Mevcut trend ve momentum değerlendirmesi
- Kritik destek ve direnç seviyeleri
- RSI, MACD ve Bollinger Bands yorumu
- Olası senaryolar (yükseliş / düşüş)
- Risk faktörleri

Analiz profesyonel, nesnel ve 200-300 kelime arasında olsun.
Yatırım tavsiyesi verme, sadece teknik analiz yap."""

        message = client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=1024,
            messages=[{"role": "user", "content": prompt}],
        )
        return message.content[0].text

    except Exception as e:
        logger.error(f"AI analysis failed for {symbol} [{timeframe}]: {e}")
        return None


def get_ai_narrative(symbol: str, short_narrative: str, long_narrative: str,
                     long_plan_summary: str, short_plan_summary: str) -> str | None:
    """
    Send narrative + action plan context to Claude API for enriched commentary.
    Returns None on failure.
    """
    try:
        import anthropic
    except ImportError:
        return None

    if not is_ai_available():
        return None

    try:
        client = anthropic.Anthropic()

        prompt = f"""{symbol} için aşağıdaki teknik narratifler ve aksiyon planları oluşturuldu.
Bunları değerlendirip 150-200 kelimelik Türkçe bir stratejik özet yaz.

Kısa Vade Narratif: {short_narrative}
Uzun Vade Narratif: {long_narrative}
Long Plan: {long_plan_summary}
Short Plan: {short_plan_summary}

Hangi senaryo daha güçlü görünüyor ve neden? Risk faktörlerini de belirt.
Yatırım tavsiyesi verme, teknik analiz çerçevesinde kal."""

        message = client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=1024,
            messages=[{"role": "user", "content": prompt}],
        )
        return message.content[0].text

    except Exception as e:
        logger.error(f"AI narrative failed for {symbol}: {e}")
        return None
