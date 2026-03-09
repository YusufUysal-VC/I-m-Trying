"""
Narrative Engine: Short/long-term narrative identification, action plan generation,
scenario trees, and opportunity scoring.
"""

import logging
from dataclasses import dataclass, field

from .indicators import IndicatorResult
from .trend_analyzer import TrendResult

logger = logging.getLogger(__name__)


@dataclass
class ActionPlan:
    direction: str = ""  # "LONG" or "SHORT"
    bias_strength: str = "Zayıf"  # "Güçlü" | "Orta" | "Zayıf"
    narrative_alignment: str = ""  # "Kısa vade" | "Uzun vade" | "Her ikisi"

    # Entry
    entry_zone_low: float = 0.0
    entry_zone_high: float = 0.0
    entry_reasoning: str = ""

    # Targets
    target_1: float = 0.0
    target_2: float = 0.0
    target_3: float = 0.0

    # Risk management
    stop_loss: float = 0.0
    stop_reasoning: str = ""

    # Metrics
    risk_reward_t1: float = 0.0
    risk_reward_t2: float = 0.0
    risk_reward_t3: float = 0.0

    # Conditions
    entry_trigger: str = ""
    invalidation: str = ""

    # Time horizon
    time_horizon: str = ""

    # Quality flag
    is_valid: bool = True
    quality_warning: str = ""


@dataclass
class ScenarioBranch:
    icon: str = ""  # ✅, ⚠️, 🔄
    condition: str = ""
    action: str = ""
    target: str = ""
    time_horizon: str = ""


@dataclass
class NarrativeResult:
    short_term_narrative: str = ""
    short_term_confidence: str = "Düşük"  # "Yüksek", "Orta", "Düşük"
    long_term_narrative: str = ""
    long_term_confidence: str = "Düşük"

    long_plan: ActionPlan = None
    short_plan: ActionPlan = None
    dominant_direction: str = ""  # "LONG" or "SHORT"

    action_status: str = "Nötr"  # "Al", "Sat", "İzle", "Nötr"
    action_badge: str = "⚪ NÖTR"
    action_color: str = "#636e72"

    scenario_tree: list = None  # List of ScenarioBranch

    opportunity_score: float = 0.0
    summary_line: str = ""  # One-line plain Turkish summary

    def __post_init__(self):
        if self.long_plan is None:
            self.long_plan = ActionPlan(direction="LONG")
        if self.short_plan is None:
            self.short_plan = ActionPlan(direction="SHORT")
        if self.scenario_tree is None:
            self.scenario_tree = []


def calculate_rr(entry_mid: float, target: float, stop: float) -> float:
    """Calculate risk/reward ratio."""
    risk = abs(entry_mid - stop)
    if risk == 0:
        return 0.0
    reward = abs(target - entry_mid)
    return round(reward / risk, 2)


def _identify_short_term_narrative(indicators: IndicatorResult, trend: TrendResult) -> tuple[str, str, int]:
    """Identify the short-term narrative based on technical signals."""
    narratives = []
    signal_count = 0

    rsi = indicators.rsi
    price = indicators.current_price

    # RSI overbought + resistance
    if rsi is not None and rsi > 70 and indicators.resistance_levels:
        narratives.append("Aşırı alım bölgesinde güç kaybı — direnç seviyesinde dönüş sinyali")
        signal_count += 2

    # RSI oversold + support
    elif rsi is not None and rsi < 30 and indicators.support_levels:
        narratives.append("Aşırı satım sonrası destekte toparlanma beklentisi")
        signal_count += 2

    # Bollinger squeeze
    if indicators.bb_squeeze:
        narratives.append("Volatilite sıkışması — yakın vadede güçlü bir hareket bekleniyor")
        signal_count += 1

    # MACD crossovers
    if indicators.macd_crossover == "bullish_cross":
        narratives.append("MACD boğa kesişimi — momentum yukarı dönüyor")
        signal_count += 1
    elif indicators.macd_crossover == "bearish_cross":
        narratives.append("MACD ayı kesişimi — momentum aşağı dönüyor")
        signal_count += 1

    # RSI divergence
    if indicators.rsi_divergence == "bullish":
        narratives.append("RSI boğa uyumsuzluğu — gizli güç birikimi")
        signal_count += 1
    elif indicators.rsi_divergence == "bearish":
        narratives.append("RSI ayı uyumsuzluğu — zayıflama sinyali")
        signal_count += 1

    # Price vs EMA
    if indicators.ema20 is not None and indicators.ema50 is not None:
        if indicators.death_cross:
            narratives.append("Kısa vadeli trend bozulması — satış baskısı artıyor")
            signal_count += 1
        elif indicators.golden_cross:
            narratives.append("Altın çapraz oluşumu — yükseliş trendi güçleniyor")
            signal_count += 1

    # BB position
    if indicators.bb_percent is not None:
        if indicators.bb_percent > 95:
            narratives.append("Fiyat Bollinger üst bandında — aşırı gerilme riski")
            signal_count += 1
        elif indicators.bb_percent < 5:
            narratives.append("Fiyat Bollinger alt bandında — tepki potansiyeli")
            signal_count += 1

    # Default
    if not narratives:
        if trend.score > 0:
            narratives.append("Kısa vadede yukarı yönlü momentum devam ediyor")
        elif trend.score < 0:
            narratives.append("Kısa vadede aşağı yönlü baskı hakim")
        else:
            narratives.append("Kısa vadede belirgin bir yön sinyali yok — kararsız piyasa")

    narrative = narratives[0] if len(narratives) == 1 else ". ".join(narratives[:2])

    if signal_count >= 4:
        confidence = "Yüksek"
    elif signal_count >= 2:
        confidence = "Orta"
    else:
        confidence = "Düşük"

    return narrative, confidence, signal_count


def _identify_long_term_narrative(indicators: IndicatorResult, trend: TrendResult) -> tuple[str, str, int]:
    """Identify the long-term narrative."""
    narratives = []
    signal_count = 0

    # EMA200 position + alignment
    if indicators.price_vs_ema200 == "above":
        if indicators.ema50 is not None and indicators.ema200 is not None and indicators.ema50 > indicators.ema200:
            narratives.append("Uzun vadeli yükseliş trendi sağlam — büyük resim boğa")
            signal_count += 2
        else:
            narratives.append("EMA200 üzerinde yapı korunuyor — uzun vadeli destek mevcut")
            signal_count += 1
    elif indicators.price_vs_ema200 == "below":
        if indicators.ema50 is not None and indicators.ema200 is not None and indicators.ema50 < indicators.ema200:
            narratives.append("Yapısal düşüş trendi — uzun vadeli baskı devam ediyor")
            signal_count += 2
        else:
            narratives.append("EMA200 altında işlem görüyor — uzun vadeli risklere dikkat")
            signal_count += 1

    # 52w positioning
    if indicators.current_price is not None and indicators.high_52w is not None:
        pct_from_high = (indicators.current_price / indicators.high_52w) * 100
        if pct_from_high > 95:
            narratives.append("Tarihi zirve bölgesinde — kırılım ya da dönüş kritik")
            signal_count += 1
        elif pct_from_high < 40:
            narratives.append("Dip oluşturma aşaması — uzun vadeli dönüş habercisi olabilir")
            signal_count += 1

    # RSI on higher timeframe
    if indicators.rsi is not None:
        if indicators.rsi > 80:
            narratives.append("Uzun vadede aşırı alım — sürdürülemez momentum riski")
            signal_count += 1
        elif indicators.rsi < 20:
            narratives.append("Uzun vadede aşırı satım — değerleme cazibesi artıyor")
            signal_count += 1

    if not narratives:
        if trend.score > 0:
            narratives.append("Uzun vadeli görünüm olumlu — yapısal trend yukarı")
        elif trend.score < 0:
            narratives.append("Uzun vadeli görünüm olumsuz — yapısal trend aşağı")
        else:
            narratives.append("Uzun vadeli yön belirsiz — konsolidasyon sürecinde")

    narrative = narratives[0] if len(narratives) == 1 else ". ".join(narratives[:2])

    if signal_count >= 4:
        confidence = "Yüksek"
    elif signal_count >= 2:
        confidence = "Orta"
    else:
        confidence = "Düşük"

    return narrative, confidence, signal_count


def _generate_long_plan(indicators: IndicatorResult, trend: TrendResult) -> ActionPlan:
    """Generate a LONG action plan."""
    plan = ActionPlan(direction="LONG")
    price = indicators.current_price
    if price is None or price == 0:
        plan.is_valid = False
        return plan

    # Entry zone: nearest support
    if indicators.support_levels:
        nearest_support = indicators.support_levels[0].price
        plan.entry_zone_low = round(nearest_support * 0.995, 4)
        plan.entry_zone_high = round(nearest_support * 1.005, 4)
        plan.entry_reasoning = f"En yakın destek seviyesi ({nearest_support:.4g}) bölgesinde alım"
    elif indicators.ema50 is not None:
        plan.entry_zone_low = round(indicators.ema50 * 0.99, 4)
        plan.entry_zone_high = round(indicators.ema50 * 1.01, 4)
        plan.entry_reasoning = f"EMA50 ({indicators.ema50:.4g}) destek bölgesinde alım"
    elif indicators.ema20 is not None:
        plan.entry_zone_low = round(indicators.ema20 * 0.99, 4)
        plan.entry_zone_high = round(indicators.ema20 * 1.01, 4)
        plan.entry_reasoning = f"EMA20 ({indicators.ema20:.4g}) destek bölgesinde alım"
    else:
        plan.entry_zone_low = round(price * 0.97, 4)
        plan.entry_zone_high = round(price * 0.99, 4)
        plan.entry_reasoning = "Mevcut fiyattan %1-3 geri çekilme bölgesinde alım"

    entry_mid = (plan.entry_zone_low + plan.entry_zone_high) / 2

    # Targets: resistance levels
    if len(indicators.resistance_levels) >= 1:
        plan.target_1 = indicators.resistance_levels[0].price
    else:
        plan.target_1 = round(entry_mid * 1.05, 4)

    if len(indicators.resistance_levels) >= 2:
        plan.target_2 = indicators.resistance_levels[1].price
    else:
        plan.target_2 = round(entry_mid * 1.10, 4)

    if len(indicators.resistance_levels) >= 3:
        plan.target_3 = indicators.resistance_levels[2].price
    elif indicators.high_52w is not None:
        plan.target_3 = indicators.high_52w
    else:
        plan.target_3 = round(entry_mid * 1.20, 4)

    # Stop loss: below entry support by 1-2%, max 8% below entry
    if indicators.support_levels:
        plan.stop_loss = round(indicators.support_levels[0].price * 0.98, 4)
        plan.stop_reasoning = "Destek bölgesinin altına kapanış"
    else:
        plan.stop_loss = round(entry_mid * 0.95, 4)
        plan.stop_reasoning = "Giriş bölgesinin %5 altı"

    # Enforce max 8% stop
    max_stop = entry_mid * 0.92
    if plan.stop_loss < max_stop:
        plan.stop_loss = round(max_stop, 4)
        plan.stop_reasoning = "Maksimum %8 zarar limiti"

    # R:R calculations
    plan.risk_reward_t1 = calculate_rr(entry_mid, plan.target_1, plan.stop_loss)
    plan.risk_reward_t2 = calculate_rr(entry_mid, plan.target_2, plan.stop_loss)
    plan.risk_reward_t3 = calculate_rr(entry_mid, plan.target_3, plan.stop_loss)

    # Quality check
    if plan.risk_reward_t1 < 1.5:
        plan.quality_warning = "Düşük Kaliteli Kurulum — R:R < 1.5"

    # Bias strength
    if trend.score >= 50:
        plan.bias_strength = "Güçlü"
    elif trend.score >= 20:
        plan.bias_strength = "Orta"
    else:
        plan.bias_strength = "Zayıf"

    # Entry trigger
    if indicators.rsi is not None and indicators.rsi > 50:
        plan.entry_trigger = f"RSI {indicators.rsi:.0f} altına düşerse giriş bölgesini bekle"
    else:
        plan.entry_trigger = "Fiyat giriş bölgesine çekildiğinde al"

    # Invalidation
    if indicators.ema200 is not None:
        plan.invalidation = f"Haftalık kapanış EMA200 ({indicators.ema200:.4g}) altında olursa iptal"
    else:
        plan.invalidation = f"Stop loss ({plan.stop_loss:.4g}) seviyesi kırılırsa iptal"

    # Time horizon
    if trend.score >= 50:
        plan.time_horizon = "Orta Vade (1-3 ay)"
        plan.narrative_alignment = "Her ikisi"
    elif trend.score >= 20:
        plan.time_horizon = "Kısa Vade (1-2 hafta)"
        plan.narrative_alignment = "Kısa vade"
    else:
        plan.time_horizon = "Kısa Vade (1-2 hafta)"
        plan.narrative_alignment = "Kısa vade"

    return plan


def _generate_short_plan(indicators: IndicatorResult, trend: TrendResult) -> ActionPlan:
    """Generate a SHORT action plan."""
    plan = ActionPlan(direction="SHORT")
    price = indicators.current_price
    if price is None or price == 0:
        plan.is_valid = False
        return plan

    # Entry zone: nearest resistance
    if indicators.resistance_levels:
        nearest_resistance = indicators.resistance_levels[0].price
        plan.entry_zone_low = round(nearest_resistance * 0.995, 4)
        plan.entry_zone_high = round(nearest_resistance * 1.005, 4)
        plan.entry_reasoning = f"En yakın direnç seviyesi ({nearest_resistance:.4g}) bölgesinde satış"
    elif indicators.ema20 is not None and trend.score < 0:
        plan.entry_zone_low = round(indicators.ema20 * 0.99, 4)
        plan.entry_zone_high = round(indicators.ema20 * 1.01, 4)
        plan.entry_reasoning = f"EMA20 ({indicators.ema20:.4g}) direnci bölgesinde satış"
    else:
        plan.entry_zone_low = round(price * 1.01, 4)
        plan.entry_zone_high = round(price * 1.03, 4)
        plan.entry_reasoning = "Mevcut fiyattan %1-3 yukarı sıçrama bölgesinde satış"

    entry_mid = (plan.entry_zone_low + plan.entry_zone_high) / 2

    # Targets: support levels
    if len(indicators.support_levels) >= 1:
        plan.target_1 = indicators.support_levels[0].price
    else:
        plan.target_1 = round(entry_mid * 0.95, 4)

    if len(indicators.support_levels) >= 2:
        plan.target_2 = indicators.support_levels[1].price
    else:
        plan.target_2 = round(entry_mid * 0.90, 4)

    if len(indicators.support_levels) >= 3:
        plan.target_3 = indicators.support_levels[2].price
    elif indicators.low_52w is not None:
        plan.target_3 = indicators.low_52w
    else:
        plan.target_3 = round(entry_mid * 0.80, 4)

    # Stop loss: above entry resistance by 1-2%, max 8%
    if indicators.resistance_levels:
        plan.stop_loss = round(indicators.resistance_levels[0].price * 1.02, 4)
        plan.stop_reasoning = "Direnç bölgesinin üstüne kapanış"
    else:
        plan.stop_loss = round(entry_mid * 1.05, 4)
        plan.stop_reasoning = "Giriş bölgesinin %5 üstü"

    max_stop = entry_mid * 1.08
    if plan.stop_loss > max_stop:
        plan.stop_loss = round(max_stop, 4)
        plan.stop_reasoning = "Maksimum %8 zarar limiti"

    plan.risk_reward_t1 = calculate_rr(entry_mid, plan.target_1, plan.stop_loss)
    plan.risk_reward_t2 = calculate_rr(entry_mid, plan.target_2, plan.stop_loss)
    plan.risk_reward_t3 = calculate_rr(entry_mid, plan.target_3, plan.stop_loss)

    if plan.risk_reward_t1 < 1.5:
        plan.quality_warning = "Düşük Kaliteli Kurulum — R:R < 1.5"

    if trend.score <= -50:
        plan.bias_strength = "Güçlü"
    elif trend.score <= -20:
        plan.bias_strength = "Orta"
    else:
        plan.bias_strength = "Zayıf"

    if indicators.rsi is not None and indicators.rsi < 50:
        plan.entry_trigger = f"RSI {indicators.rsi:.0f} üstüne çıkarsa direnç bölgesini bekle"
    else:
        plan.entry_trigger = "Fiyat giriş bölgesine yükseldiğinde sat"

    if indicators.ema200 is not None:
        plan.invalidation = f"Günlük kapanış EMA200 ({indicators.ema200:.4g}) üstünde olursa iptal"
    else:
        plan.invalidation = f"Stop loss ({plan.stop_loss:.4g}) seviyesi kırılırsa iptal"

    if trend.score <= -50:
        plan.time_horizon = "Orta Vade (1-3 ay)"
        plan.narrative_alignment = "Her ikisi"
    else:
        plan.time_horizon = "Kısa Vade (1-2 hafta)"
        plan.narrative_alignment = "Kısa vade"

    return plan


def _generate_scenario_tree(indicators: IndicatorResult, long_plan: ActionPlan, short_plan: ActionPlan, trend: TrendResult) -> list[ScenarioBranch]:
    """Generate plain-Turkish scenario tree (2-3 branches)."""
    branches = []
    price = indicators.current_price
    if price is None:
        return branches

    if trend.score >= 0:
        # Bullish dominant
        if indicators.resistance_levels:
            r1 = indicators.resistance_levels[0].price
            branches.append(ScenarioBranch(
                icon="✅",
                condition=f"Fiyat {r1:.4g} seviyesinin üstünde kapanırsa",
                action="AL",
                target=f"Hedef: {long_plan.target_2:.4g}" if long_plan.target_2 else "",
                time_horizon="2-4 hafta",
            ))

        if long_plan.stop_loss:
            branches.append(ScenarioBranch(
                icon="⚠️",
                condition=f"Fiyat {long_plan.stop_loss:.4g} altına düşerse",
                action="BEKLE, güvenli bölge değil",
                target="",
                time_horizon="",
            ))

        if indicators.support_levels:
            s1 = indicators.support_levels[0].price
            branches.append(ScenarioBranch(
                icon="🔄",
                condition=f"Fiyat {s1:.4g} bölgesine çekilirse",
                action="Daha iyi fiyattan AL fırsatı",
                target=f"Hedef: {long_plan.target_1:.4g}" if long_plan.target_1 else "",
                time_horizon="1-2 hafta",
            ))
    else:
        # Bearish dominant
        if indicators.support_levels:
            s1 = indicators.support_levels[0].price
            branches.append(ScenarioBranch(
                icon="✅",
                condition=f"Fiyat {s1:.4g} desteğini kırarsa",
                action="SAT",
                target=f"Hedef: {short_plan.target_1:.4g}" if short_plan.target_1 else "",
                time_horizon="1-2 hafta",
            ))

        if short_plan.stop_loss:
            branches.append(ScenarioBranch(
                icon="⚠️",
                condition=f"Fiyat {short_plan.stop_loss:.4g} üstüne çıkarsa",
                action="BEKLE, trend bozulmuş olabilir",
                target="",
                time_horizon="",
            ))

        if indicators.resistance_levels:
            r1 = indicators.resistance_levels[0].price
            branches.append(ScenarioBranch(
                icon="🔄",
                condition=f"Fiyat {r1:.4g} direncine yükselirse",
                action="Yeniden değerlendir",
                target="",
                time_horizon="",
            ))

    return branches[:3]


def _determine_action_status(long_plan: ActionPlan, short_plan: ActionPlan, indicators: IndicatorResult, trend: TrendResult) -> tuple[str, str, str]:
    """
    Determine action status: Al / Sat / İzle / Nötr.
    Returns (status, badge, color).
    """
    price = indicators.current_price
    if price is None:
        return "Nötr", "⚪ NÖTR", "#636e72"

    # Check LONG: price in entry zone + R:R >= 1.5
    long_in_zone = long_plan.entry_zone_low <= price <= long_plan.entry_zone_high
    long_near_zone = long_plan.entry_zone_low * 0.98 <= price <= long_plan.entry_zone_high * 1.02
    long_valid_rr = long_plan.risk_reward_t1 >= 1.5

    # Check SHORT: price in entry zone + R:R >= 1.5
    short_in_zone = short_plan.entry_zone_low <= price <= short_plan.entry_zone_high
    short_near_zone = short_plan.entry_zone_low * 0.98 <= price <= short_plan.entry_zone_high * 1.02
    short_valid_rr = short_plan.risk_reward_t1 >= 1.5

    if long_in_zone and long_valid_rr and trend.score >= 0:
        return "Al", "🟢 AL", "#00b894"
    elif short_in_zone and short_valid_rr and trend.score <= 0:
        return "Sat", "🔴 SAT", "#d63031"
    elif (long_near_zone and long_valid_rr) or (short_near_zone and short_valid_rr):
        return "İzle", "🟡 İZLE", "#fdcb6e"
    elif trend.score >= 30 and long_valid_rr:
        return "Al", "🟢 AL", "#00b894"
    elif trend.score <= -30 and short_valid_rr:
        return "Sat", "🔴 SAT", "#d63031"
    elif abs(trend.score) >= 20:
        return "İzle", "🟡 İZLE", "#fdcb6e"
    else:
        return "Nötr", "⚪ NÖTR", "#636e72"


def score_opportunity(action_status: str, rr_t1: float, alignment_count: int, confidence: str, setup_completeness: float = 0.5) -> float:
    """Score an instrument for the 'Günün Fırsatları' ranking."""
    score = 0.0
    if action_status in ("Al", "Sat"):
        score += 40
    score += min(rr_t1 * 10, 30)
    score += alignment_count * 5

    confidence_scores = {"Yüksek": 20, "Orta": 10, "Düşük": 5}
    score += confidence_scores.get(confidence, 0)

    if action_status == "İzle" and setup_completeness > 0.8:
        score += 15

    return score


def generate_narrative(indicators: IndicatorResult, trend: TrendResult, alignment_info: dict | None = None) -> NarrativeResult:
    """Generate complete narrative analysis for a single instrument."""
    result = NarrativeResult()

    if indicators is None or indicators.current_price is None:
        result.summary_line = "Veri yetersiz — analiz yapılamıyor"
        return result

    # Short-term narrative
    short_narrative, short_conf, short_signals = _identify_short_term_narrative(indicators, trend)
    result.short_term_narrative = short_narrative
    result.short_term_confidence = short_conf

    # Long-term narrative
    long_narrative, long_conf, long_signals = _identify_long_term_narrative(indicators, trend)
    result.long_term_narrative = long_narrative
    result.long_term_confidence = long_conf

    # Generate action plans
    result.long_plan = _generate_long_plan(indicators, trend)
    result.short_plan = _generate_short_plan(indicators, trend)

    # Dominant direction
    result.dominant_direction = "LONG" if trend.score >= 0 else "SHORT"

    # Scenario tree
    result.scenario_tree = _generate_scenario_tree(indicators, result.long_plan, result.short_plan, trend)

    # Action status
    result.action_status, result.action_badge, result.action_color = _determine_action_status(
        result.long_plan, result.short_plan, indicators, trend
    )

    # Opportunity score
    alignment_count = alignment_info.get("bullish_count", 0) if alignment_info else 0
    if result.dominant_direction == "SHORT":
        alignment_count = alignment_info.get("bearish_count", 0) if alignment_info else 0
    rr_t1 = result.long_plan.risk_reward_t1 if result.dominant_direction == "LONG" else result.short_plan.risk_reward_t1
    result.opportunity_score = score_opportunity(
        result.action_status, rr_t1, alignment_count,
        result.short_term_confidence
    )

    # Summary line
    result.summary_line = _generate_summary_line(indicators, trend, result)

    return result


def _generate_summary_line(indicators: IndicatorResult, trend: TrendResult, narrative: NarrativeResult) -> str:
    """Generate a one-line plain Turkish summary."""
    price = indicators.current_price
    parts = []

    if narrative.action_status == "Al":
        plan = narrative.long_plan
        parts.append(f"{plan.entry_zone_low:.4g} – {plan.entry_zone_high:.4g} aralığında AL")
        parts.append(f"Hedef: {plan.target_1:.4g}")
        parts.append(f"R:R 1:{plan.risk_reward_t1}")
    elif narrative.action_status == "Sat":
        plan = narrative.short_plan
        parts.append(f"{plan.entry_zone_low:.4g} – {plan.entry_zone_high:.4g} aralığında SAT")
        parts.append(f"Hedef: {plan.target_1:.4g}")
        parts.append(f"R:R 1:{plan.risk_reward_t1}")
    elif narrative.action_status == "İzle":
        parts.append("Kurulum oluşuyor — giriş bölgesini bekle")
        if trend.score > 0:
            parts.append("yön yukarı")
        elif trend.score < 0:
            parts.append("yön aşağı")
    else:
        parts.append("Net sinyal yok — bekle")

    return " | ".join(parts)
