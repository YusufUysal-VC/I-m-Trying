"""
narrative_engine.py — Strategic layer: narratives, action plans, action status.
Synthesizes technical signals into actionable Turkish market narratives.
"""

import logging
from dataclasses import dataclass, field
from typing import Optional

from src.indicators import IndicatorResult
from src.trend_analyzer import InstrumentAnalysis, TrendResult

logger = logging.getLogger(__name__)

# Action status constants
ACTION_AL = "Al"
ACTION_SAT = "Sat"
ACTION_IZLE = "İzle"
ACTION_NOTR = "Nötr"


@dataclass
class ActionPlan:
    """Concrete trade setup with entry, targets, and risk management."""
    direction: str           # "LONG" or "SHORT"
    bias_strength: str       # "Güçlü" | "Orta" | "Zayıf"
    narrative_alignment: str # "Kısa vade" | "Uzun vade" | "Her ikisi"

    # Entry
    entry_zone_low: float = 0.0
    entry_zone_high: float = 0.0
    entry_reasoning: str = ""

    # Targets
    target_1: float = 0.0
    target_2: float = 0.0
    target_3: float = 0.0

    # Risk
    stop_loss: float = 0.0
    stop_reasoning: str = ""

    # Metrics
    risk_reward_t1: float = 0.0
    risk_reward_t2: float = 0.0
    risk_reward_t3: float = 0.0

    # Conditions
    entry_trigger: str = ""
    invalidation: str = ""
    time_horizon: str = "Orta Vade (1-3 ay)"

    # Quality
    is_valid: bool = True
    quality_warning: str = ""


@dataclass
class NarrativeResult:
    """Complete narrative and action plan for one instrument."""
    symbol: str

    # Narratives
    short_narrative: str = ""
    short_narrative_confidence: str = "Düşük"  # "Yüksek" | "Orta" | "Düşük"
    long_narrative: str = ""
    long_narrative_confidence: str = "Düşük"

    # Action plans
    long_plan: Optional[ActionPlan] = None
    short_plan: Optional[ActionPlan] = None
    dominant_direction: str = "LONG"    # "LONG" | "SHORT"

    # Action status
    action_status: str = ACTION_NOTR    # Al | Sat | İzle | Nötr
    action_reason: str = ""             # One-line plain Turkish

    # Scenario tree (plain language)
    scenario_branches: list = field(default_factory=list)

    # Opportunity scoring
    opportunity_score: float = 0.0


def generate_narratives(analysis: InstrumentAnalysis) -> NarrativeResult:
    """
    Main entry point: generate narratives and action plans for one instrument.
    """
    result = NarrativeResult(symbol=analysis.symbol)

    daily_ind = analysis.indicators.get("Günlük")
    weekly_ind = analysis.indicators.get("Haftalık")
    monthly_ind = analysis.indicators.get("Aylık")
    daily_trend = analysis.trends.get("Günlük")
    weekly_trend = analysis.trends.get("Haftalık")
    monthly_trend = analysis.trends.get("Aylık")

    # Short-term narrative (daily/weekly)
    result.short_narrative, result.short_narrative_confidence = _build_short_narrative(
        daily_ind, weekly_ind, daily_trend
    )

    # Long-term narrative (monthly/yearly)
    result.long_narrative, result.long_narrative_confidence = _build_long_narrative(
        monthly_ind, monthly_trend, analysis
    )

    # Action plans
    price = analysis.current_price
    if price and price > 0:
        result.long_plan = _build_long_plan(analysis, daily_ind, daily_trend)
        result.short_plan = _build_short_plan(analysis, daily_ind, daily_trend)

    # Determine dominant direction
    if analysis.overall_score > 20:
        result.dominant_direction = "LONG"
    elif analysis.overall_score < -20:
        result.dominant_direction = "SHORT"
    else:
        result.dominant_direction = "LONG"  # Default to long in neutral

    # Action status
    result.action_status, result.action_reason = _compute_action_status(
        analysis, result.long_plan, result.short_plan, result.dominant_direction
    )

    # Scenario tree
    result.scenario_branches = _build_scenario_tree(
        analysis, result.long_plan, result.short_plan, result.dominant_direction
    )

    # Opportunity score
    result.opportunity_score = _score_opportunity(analysis, result)

    return result


def _build_short_narrative(
    daily: Optional[IndicatorResult],
    weekly: Optional[IndicatorResult],
    daily_trend: Optional[TrendResult],
) -> tuple[str, str]:
    """
    Build short-term narrative using daily/weekly signals.
    Returns (narrative_text, confidence_level).
    """
    if daily is None:
        return "Kısa vadeli veri mevcut değil.", "Düşük"

    signals_count = 0
    narrative_parts = []

    rsi = daily.rsi
    macd_type = daily.macd_signal_type
    bb_pct = daily.bb_pct
    bb_squeeze = daily.bb_squeeze

    # RSI patterns
    if rsi is not None:
        if rsi > 70 and daily_trend and daily_trend.score < 30:
            narrative_parts.append("aşırı alım bölgesinde güç kaybı")
            signals_count += 1
        elif rsi < 30 and daily.rsi_divergence == "bullish":
            narrative_parts.append("aşırı satım sonrası destekte toparlanma beklentisi")
            signals_count += 2
        elif rsi > 70:
            narrative_parts.append("aşırı alım bölgesinde direnç testi")
            signals_count += 1
        elif rsi < 30:
            narrative_parts.append("aşırı satım bölgesinde destek arayışı")
            signals_count += 1

    # Bollinger Band squeeze
    if bb_squeeze:
        narrative_parts.append("volatilite sıkışması — yakın vadede güçlü bir hareket bekleniyor")
        signals_count += 2

    # MACD patterns
    if macd_type == "bullish_cross":
        narrative_parts.append("MACD alım sinyali üretildi")
        signals_count += 1
    elif macd_type == "bearish_cross":
        narrative_parts.append("MACD satım sinyali üretildi")
        signals_count += 1

    # Breakout/breakdown
    if daily_trend:
        if daily_trend.above_recent_high:
            narrative_parts.append("direnç kırılımı — yeni bir yükseliş dalgası başlıyor olabilir")
            signals_count += 2
        elif daily_trend.below_recent_low:
            narrative_parts.append("destek kırılımı — satış baskısı artıyor")
            signals_count += 2

    # Death/golden cross
    if daily.death_cross:
        narrative_parts.append("kısa vadeli trend bozulması — EMA ölüm kesişimi oluştu")
        signals_count += 2
    elif daily.golden_cross:
        narrative_parts.append("altın kesişim oluştu — yükseliş trendine güçlü sinyal")
        signals_count += 2

    if not narrative_parts:
        if daily_trend and daily_trend.label in ("Güçlü Yükseliş", "Yükseliş"):
            narrative_parts.append("fiyat yükseliş momentumunu koruyor")
        elif daily_trend and daily_trend.label in ("Güçlü Düşüş", "Düşüş"):
            narrative_parts.append("fiyat düşüş baskısı altında seyrine devam ediyor")
        else:
            narrative_parts.append("fiyat belirgin bir yön aramaya devam ediyor")
        signals_count += 1

    narrative = narrative_parts[0].capitalize()
    if len(narrative_parts) > 1:
        narrative += "; " + ", ".join(narrative_parts[1:])
    narrative += "."

    confidence = "Düşük" if signals_count <= 1 else "Orta" if signals_count <= 3 else "Yüksek"
    return narrative, confidence


def _build_long_narrative(
    monthly: Optional[IndicatorResult],
    monthly_trend: Optional[TrendResult],
    analysis: InstrumentAnalysis,
) -> tuple[str, str]:
    """Build long-term narrative using monthly/yearly signals."""
    signals_count = 0
    narrative_parts = []

    # EMA200 structural position
    ind = monthly or analysis.indicators.get("Haftalık")
    if ind:
        price = analysis.current_price
        if ind.ema_200 and price:
            if price > ind.ema_200:
                narrative_parts.append("EMA200 üzerinde sağlam yapı — büyük resim boğa")
                signals_count += 2
            else:
                narrative_parts.append("EMA200 altında yapısal baskı — uzun vadeli düşüş devam ediyor")
                signals_count += 2

        if ind.golden_cross:
            narrative_parts.append("altın kesişim uzun vadeli yükseliş trendini teyit ediyor")
            signals_count += 2
        elif ind.death_cross:
            narrative_parts.append("ölüm kesişimi uzun vadeli düşüş eğilimini güçlendiriyor")
            signals_count += 2

        if ind.rsi and ind.rsi > 80:
            narrative_parts.append("aylık RSI aşırı alım bölgesinde — uzun vadede sürdürülemez momentum riski")
            signals_count += 1
        elif ind.rsi and ind.rsi < 25:
            narrative_parts.append("aylık RSI aşırı satım bölgesinde — dip oluşturma aşaması")
            signals_count += 1

    if analysis.aligned_tf_count >= 4:
        if analysis.overall_score > 0:
            narrative_parts.append("çoklu zaman diliminde yükseliş uyumu — trend güçlü")
            signals_count += 2
        else:
            narrative_parts.append("çoklu zaman diliminde düşüş uyumu — baskı yaygın")
            signals_count += 2

    if not narrative_parts:
        if analysis.overall_score > 20:
            narrative_parts.append("uzun vadeli yapı genel olarak destekleyici")
        elif analysis.overall_score < -20:
            narrative_parts.append("uzun vadeli yapı baskı altında")
        else:
            narrative_parts.append("uzun vadeli yapı yatay seyirde, yön belirsiz")
        signals_count = 1

    narrative = narrative_parts[0].capitalize()
    if len(narrative_parts) > 1:
        narrative += "; " + narrative_parts[1]
    narrative += "."

    confidence = "Düşük" if signals_count <= 1 else "Orta" if signals_count <= 3 else "Yüksek"
    return narrative, confidence


def _build_long_plan(
    analysis: InstrumentAnalysis,
    daily: Optional[IndicatorResult],
    trend: Optional[TrendResult],
) -> ActionPlan:
    """Build LONG action plan with entry zones, targets, and stop loss."""
    price = analysis.current_price
    plan = ActionPlan(direction="LONG", bias_strength="Orta", narrative_alignment="Kısa vade")

    if not price or price <= 0 or daily is None:
        plan.is_valid = False
        return plan

    supports = daily.support_levels
    resistances = daily.resistance_levels

    # Entry zone: nearest support level
    nearest_support = None
    if supports:
        below_supports = [s for s in supports if s["price"] < price * 1.02]
        if below_supports:
            nearest_support = below_supports[0]["price"]

    if nearest_support:
        plan.entry_zone_low = round(nearest_support * 0.995, 4)
        plan.entry_zone_high = round(nearest_support * 1.005, 4)
        plan.entry_reasoning = f"Destek seviyesi {_fmt_price(nearest_support)} bölgesine yaklaşımda"
    elif daily.ema_50 and daily.ema_50 < price:
        plan.entry_zone_low = round(daily.ema_50 * 0.99, 4)
        plan.entry_zone_high = round(daily.ema_50 * 1.01, 4)
        plan.entry_reasoning = f"EMA50 ({_fmt_price(daily.ema_50)}) desteğine yaklaşımda"
    else:
        # Current price entry
        plan.entry_zone_low = round(price * 0.99, 4)
        plan.entry_zone_high = round(price * 1.01, 4)
        plan.entry_reasoning = "Mevcut fiyat bölgesinde teknik görünüm destekleyici"

    entry_mid = (plan.entry_zone_low + plan.entry_zone_high) / 2

    # Targets: resistance levels
    above_res = [r for r in resistances if r["price"] > entry_mid * 1.01] if resistances else []

    if len(above_res) >= 1:
        plan.target_1 = above_res[0]["price"]
    else:
        plan.target_1 = round(entry_mid * 1.08, 4)

    if len(above_res) >= 2:
        plan.target_2 = above_res[1]["price"]
    else:
        plan.target_2 = round(entry_mid * 1.15, 4)

    if len(above_res) >= 3:
        plan.target_3 = above_res[2]["price"]
    else:
        plan.target_3 = round(entry_mid * 1.25, 4)

    # Stop loss: below entry support
    if nearest_support:
        plan.stop_loss = round(nearest_support * 0.98, 4)
        plan.stop_reasoning = f"Destek bölgesi {_fmt_price(nearest_support)} altına kapanış"
    elif daily.ema_200 and daily.ema_200 < entry_mid:
        plan.stop_loss = round(daily.ema_200 * 0.99, 4)
        plan.stop_reasoning = "EMA200 altına günlük kapanış"
    else:
        plan.stop_loss = round(entry_mid * 0.93, 4)  # Hard 7% stop
        plan.stop_reasoning = "Teknik yapıyı bozan kırılım seviyesi"

    # Hard maximum 8% stop
    max_stop = entry_mid * 0.92
    if plan.stop_loss < max_stop:
        plan.stop_loss = round(max_stop, 4)
        plan.stop_reasoning += " (maksimum %8 risk uygulandı)"

    # R:R calculations
    risk = entry_mid - plan.stop_loss
    if risk > 0:
        plan.risk_reward_t1 = round((plan.target_1 - entry_mid) / risk, 2)
        plan.risk_reward_t2 = round((plan.target_2 - entry_mid) / risk, 2)
        plan.risk_reward_t3 = round((plan.target_3 - entry_mid) / risk, 2)

    # Quality check
    if plan.risk_reward_t1 < 1.5:
        plan.quality_warning = "Düşük Kaliteli Kurulum (R:R < 1.5)"

    # Entry trigger
    if daily.rsi and daily.rsi > 55:
        plan.entry_trigger = f"RSI 50'nin altına düştüğünde ve destek bölgesine yaklaşıldığında al"
    else:
        plan.entry_trigger = f"{_fmt_price(plan.entry_zone_high)} fiyatına gelindiğinde al"

    plan.invalidation = "Haftalık kapanış EMA200 altında gerçekleşirse kurulumu iptal et"

    # Time horizon based on timeframe alignment
    if analysis.aligned_tf_count >= 4:
        plan.time_horizon = "Uzun Vade (3+ ay)"
        plan.narrative_alignment = "Her ikisi"
        plan.bias_strength = "Güçlü"
    elif analysis.aligned_tf_count >= 2:
        plan.time_horizon = "Orta Vade (1-3 ay)"
        plan.bias_strength = "Orta"
    else:
        plan.time_horizon = "Kısa Vade (1-2 hafta)"
        plan.bias_strength = "Zayıf"

    return plan


def _build_short_plan(
    analysis: InstrumentAnalysis,
    daily: Optional[IndicatorResult],
    trend: Optional[TrendResult],
) -> ActionPlan:
    """Build SHORT action plan."""
    price = analysis.current_price
    plan = ActionPlan(direction="SHORT", bias_strength="Zayıf", narrative_alignment="Kısa vade")

    if not price or price <= 0 or daily is None:
        plan.is_valid = False
        return plan

    supports = daily.support_levels
    resistances = daily.resistance_levels

    # Entry zone: nearest resistance
    nearest_resistance = None
    if resistances:
        above_res = [r for r in resistances if r["price"] > price * 0.98]
        if above_res:
            nearest_resistance = above_res[0]["price"]

    if nearest_resistance:
        plan.entry_zone_low = round(nearest_resistance * 0.995, 4)
        plan.entry_zone_high = round(nearest_resistance * 1.005, 4)
        plan.entry_reasoning = f"Direnç seviyesi {_fmt_price(nearest_resistance)} bölgesine yaklaşımda"
    elif daily.ema_20 and daily.ema_20 > price:
        plan.entry_zone_low = round(daily.ema_20 * 0.99, 4)
        plan.entry_zone_high = round(daily.ema_20 * 1.01, 4)
        plan.entry_reasoning = f"EMA20 ({_fmt_price(daily.ema_20)}) direnç bölgesinde"
    else:
        plan.entry_zone_low = round(price * 1.01, 4)
        plan.entry_zone_high = round(price * 1.03, 4)
        plan.entry_reasoning = "Fiyatın üstündeki teknik direnç bölgesinde"

    entry_mid = (plan.entry_zone_low + plan.entry_zone_high) / 2

    # Targets: support levels
    below_sup = [s for s in supports if s["price"] < entry_mid * 0.99] if supports else []

    if len(below_sup) >= 1:
        plan.target_1 = below_sup[-1]["price"]
    else:
        plan.target_1 = round(entry_mid * 0.92, 4)

    if len(below_sup) >= 2:
        plan.target_2 = below_sup[-2]["price"]
    else:
        plan.target_2 = round(entry_mid * 0.85, 4)

    # Stop loss: above entry resistance
    if nearest_resistance:
        plan.stop_loss = round(nearest_resistance * 1.02, 4)
        plan.stop_reasoning = f"Direnç bölgesi {_fmt_price(nearest_resistance)} üstüne kapanış"
    else:
        plan.stop_loss = round(entry_mid * 1.07, 4)
        plan.stop_reasoning = "Teknik yapıyı bozan kırılım seviyesi"

    max_stop = entry_mid * 1.08
    if plan.stop_loss > max_stop:
        plan.stop_loss = round(max_stop, 4)
        plan.stop_reasoning += " (maksimum %8 risk uygulandı)"

    # R:R
    risk = plan.stop_loss - entry_mid
    if risk > 0:
        plan.risk_reward_t1 = round((entry_mid - plan.target_1) / risk, 2)
        plan.risk_reward_t2 = round((entry_mid - plan.target_2) / risk, 2)

    if plan.risk_reward_t1 < 1.5:
        plan.quality_warning = "Düşük Kaliteli Kurulum (R:R < 1.5)"

    plan.entry_trigger = f"{_fmt_price(plan.entry_zone_low)} fiyatına gelindiğinde sat"
    plan.invalidation = "Direnç bölgesinin üstünde güçlü kapanış gerçekleşirse kurulumu iptal et"
    plan.time_horizon = "Kısa Vade (1-2 hafta)"

    return plan


def _compute_action_status(
    analysis: InstrumentAnalysis,
    long_plan: Optional[ActionPlan],
    short_plan: Optional[ActionPlan],
    dominant: str,
) -> tuple[str, str]:
    """
    Determine action status: Al / Sat / İzle / Nötr.
    Returns (status, one_line_reason).
    """
    price = analysis.current_price

    def price_in_zone(low, high):
        return low * 0.99 <= price <= high * 1.01

    # Check LONG setup
    if dominant == "LONG" and long_plan and long_plan.is_valid:
        rr = long_plan.risk_reward_t1
        in_zone = price_in_zone(long_plan.entry_zone_low, long_plan.entry_zone_high)
        if in_zone and rr >= 1.5:
            reason = f"Giriş bölgesinde ({_fmt_price(long_plan.entry_zone_low)}–{_fmt_price(long_plan.entry_zone_high)}), R:R 1:{rr}"
            return ACTION_AL, reason
        elif rr >= 1.5:
            reason = f"Kurulum hazır — giriş bölgesi {_fmt_price(long_plan.entry_zone_low)}–{_fmt_price(long_plan.entry_zone_high)}"
            return ACTION_IZLE, reason

    # Check SHORT setup
    if dominant == "SHORT" and short_plan and short_plan.is_valid:
        rr = short_plan.risk_reward_t1
        in_zone = price_in_zone(short_plan.entry_zone_low, short_plan.entry_zone_high)
        if in_zone and rr >= 1.5:
            reason = f"Direnç bölgesinde ({_fmt_price(short_plan.entry_zone_low)}–{_fmt_price(short_plan.entry_zone_high)}), R:R 1:{rr}"
            return ACTION_SAT, reason
        elif rr >= 1.5:
            reason = f"Short kurulum hazırlanıyor — direnç bölgesi {_fmt_price(short_plan.entry_zone_low)}–{_fmt_price(short_plan.entry_zone_high)}"
            return ACTION_IZLE, reason

    # Check if any valid setup with decent R:R
    daily_ind = analysis.indicators.get("Günlük")
    if daily_ind and daily_ind.bb_squeeze:
        return ACTION_IZLE, "Bollinger sıkışması — yakında güçlü hareket bekleniyor"

    trend_label = analysis.overall_trend
    if trend_label in ("Güçlü Yükseliş", "Yükseliş", "Güçlü Düşüş", "Düşüş"):
        return ACTION_IZLE, f"{trend_label} trendi — giriş seviyesi bekleniyor"

    return ACTION_NOTR, "Net kurulum yok, çakışan sinyaller mevcut"


def _build_scenario_tree(
    analysis: InstrumentAnalysis,
    long_plan: Optional[ActionPlan],
    short_plan: Optional[ActionPlan],
    dominant: str,
) -> list[dict]:
    """
    Build 2-3 plain Turkish scenario branches for the scenario tree.
    Each branch: {icon, condition, action, target, stop, horizon}
    """
    branches = []
    price = analysis.current_price

    if long_plan and long_plan.is_valid and dominant == "LONG":
        # Primary bullish scenario
        branches.append({
            "icon": "✅",
            "condition": f"Fiyat {_fmt_price(long_plan.entry_zone_high)} seviyesinin üstünde kapanırsa",
            "action": "AL",
            "target": f"Hedef: {_fmt_price(long_plan.target_1)} ({_pct(price, long_plan.target_1)})",
            "stop": f"Stop: {_fmt_price(long_plan.stop_loss)} ({_pct(price, long_plan.stop_loss)})",
            "horizon": long_plan.time_horizon,
        })
        # Stop scenario
        branches.append({
            "icon": "⚠️",
            "condition": f"Fiyat {_fmt_price(long_plan.stop_loss)} seviyesinin altına düşerse",
            "action": "BEKLE",
            "target": "Güvenli bölge değil",
            "stop": "",
            "horizon": "",
        })
        # Re-entry scenario
        if long_plan.entry_zone_low < price:
            branches.append({
                "icon": "🔄",
                "condition": f"Fiyat {_fmt_price(long_plan.entry_zone_low)}'a kadar geri çekilirse",
                "action": "Daha iyi fiyattan AL",
                "target": f"Hedef: {_fmt_price(long_plan.target_2)}",
                "stop": f"Stop: {_fmt_price(long_plan.stop_loss)}",
                "horizon": long_plan.time_horizon,
            })

    elif short_plan and short_plan.is_valid and dominant == "SHORT":
        branches.append({
            "icon": "✅",
            "condition": f"Fiyat {_fmt_price(short_plan.entry_zone_low)} seviyesinin altında kapanırsa",
            "action": "SAT",
            "target": f"Hedef: {_fmt_price(short_plan.target_1)} ({_pct(price, short_plan.target_1)})",
            "stop": f"Stop: {_fmt_price(short_plan.stop_loss)} ({_pct(price, short_plan.stop_loss)})",
            "horizon": short_plan.time_horizon,
        })
        branches.append({
            "icon": "⚠️",
            "condition": f"Fiyat {_fmt_price(short_plan.stop_loss)} seviyesinin üstüne çıkarsa",
            "action": "ÇIK",
            "target": "Kısa pozisyonu kapat",
            "stop": "",
            "horizon": "",
        })
    else:
        # Neutral scenario
        branches.append({
            "icon": "🔄",
            "condition": "Fiyat net bir yön belirleyene kadar",
            "action": "BEKLE",
            "target": "Kurulum oluşmasını izle",
            "stop": "",
            "horizon": "",
        })

    return branches


def _score_opportunity(analysis: InstrumentAnalysis, narrative: NarrativeResult) -> float:
    """
    Score this instrument as an opportunity (0-100).
    Higher = more actionable/attractive setup.
    """
    score = 0.0

    if narrative.action_status == ACTION_AL:
        score += 40
    elif narrative.action_status == ACTION_SAT:
        score += 40
    elif narrative.action_status == ACTION_IZLE:
        score += 20

    # R:R bonus
    plan = narrative.long_plan if narrative.dominant_direction == "LONG" else narrative.short_plan
    if plan and plan.risk_reward_t1 > 0:
        score += min(plan.risk_reward_t1 * 10, 30)

    # Multi-timeframe alignment bonus
    score += analysis.aligned_tf_count * 5

    # Narrative confidence bonus
    conf_map = {"Yüksek": 10, "Orta": 5, "Düşük": 0}
    score += conf_map.get(narrative.short_narrative_confidence, 0)

    return round(score, 1)


def _fmt_price(price: float) -> str:
    """Format price for display."""
    if price >= 1000:
        return f"{price:,.0f}"
    elif price >= 10:
        return f"{price:.2f}"
    elif price >= 1:
        return f"{price:.3f}"
    else:
        return f"{price:.4f}"


def _pct(entry: float, target: float) -> str:
    """Format percentage change from entry to target."""
    if entry and entry > 0:
        pct = (target - entry) / entry * 100
        sign = "+" if pct >= 0 else ""
        return f"{sign}{pct:.1f}%"
    return ""
