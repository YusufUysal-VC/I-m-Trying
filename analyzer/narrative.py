from dataclasses import dataclass, asdict
from typing import List
import math


SHORT_TERM_NARRATIVES = {
    "breakout_yukari": {
        "baslik": "Direnç Kırılımı",
        "ozet": "Fiyat kritik direnci yukarı kırdı, hacim destekli",
        "yon": "LONG",
        "guven": "Yüksek"
    },
    "rsi_donus_alim": {
        "baslik": "RSI Aşırı Satım + MACD Dönüşü",
        "ozet": "Aşırı satım bölgesinde MACD pozitife döndü, teknik toparlanma bekleniyor",
        "yon": "LONG",
        "guven": "Orta"
    },
    "ema_golden_cross": {
        "baslik": "EMA Golden Cross",
        "ozet": "EMA20 EMA50'yi yukarı kesti, yükseliş trendi başlıyor olabilir",
        "yon": "LONG",
        "guven": "Yüksek"
    },
    "bollinger_sikisma": {
        "baslik": "Bollinger Sıkışması",
        "ozet": "Volatilite tarihi düşük seviyede, büyük hareket yaklaşıyor olabilir — yönü bekle",
        "yon": "BEKLE",
        "guven": "Orta"
    },
    "dusus_trendi": {
        "baslik": "Düşüş Trendi",
        "ozet": "Fiyat EMA'ların altında, RSI baskı altında — short fırsatı",
        "yon": "SHORT",
        "guven": "Orta"
    }
}


def _safe(val, default=0):
    if val is None or (isinstance(val, float) and math.isnan(val)):
        return default
    return val


def detect_narrative(indicators):
    """Detect the most relevant short-term narrative based on indicators."""
    price = _safe(indicators.get('price', 0))
    rsi = _safe(indicators.get('rsi', 50))
    macd_hist = _safe(indicators.get('macd_hist', 0))
    prev_macd_hist = _safe(indicators.get('prev_macd_hist', 0))
    ema20 = _safe(indicators.get('ema20', price))
    ema50 = _safe(indicators.get('ema50', price))
    prev_ema20 = _safe(indicators.get('prev_ema20', 0))
    prev_ema50 = _safe(indicators.get('prev_ema50', 0))
    bb_upper = _safe(indicators.get('bb_upper', 0))
    bb_lower = _safe(indicators.get('bb_lower', 0))
    bb_mid = _safe(indicators.get('bb_mid', 0))
    volume_ratio = _safe(indicators.get('volume_ratio', 1))
    resistance_1 = _safe(indicators.get('resistance_1', price * 1.1))

    # Check conditions in order of priority
    if resistance_1 > 0 and price > resistance_1 * 1.005 and volume_ratio > 1.3:
        return SHORT_TERM_NARRATIVES["breakout_yukari"]

    if rsi < 35 and macd_hist > prev_macd_hist:
        return SHORT_TERM_NARRATIVES["rsi_donus_alim"]

    if ema20 > ema50 and prev_ema20 > 0 and prev_ema50 > 0 and prev_ema20 <= prev_ema50:
        return SHORT_TERM_NARRATIVES["ema_golden_cross"]

    if bb_mid > 0 and (bb_upper - bb_lower) / bb_mid < 0.05:
        return SHORT_TERM_NARRATIVES["bollinger_sikisma"]

    if price < ema20 < ema50 and rsi < 45:
        return SHORT_TERM_NARRATIVES["dusus_trendi"]

    # Default narrative based on trend
    if rsi > 50:
        return {
            "baslik": "Normal Yükseliş Trendi",
            "ozet": "Fiyat genel olarak yükseliş eğiliminde",
            "yon": "LONG",
            "guven": "Düşük"
        }
    else:
        return {
            "baslik": "Normal Düşüş Trendi",
            "ozet": "Fiyat genel olarak düşüş eğiliminde",
            "yon": "SHORT",
            "guven": "Düşük"
        }


@dataclass
class ActionPlan:
    yon: str
    giris_bolgesi: tuple
    hedef_1: float
    hedef_2: float
    hedef_3: float
    stop_loss: float
    rr_orani: float
    zaman_ufku: str
    senaryo_metni: str

    def to_dict(self):
        return {
            'yon': self.yon,
            'giris_bolgesi': list(self.giris_bolgesi),
            'hedef_1': round(self.hedef_1, 2),
            'hedef_2': round(self.hedef_2, 2),
            'hedef_3': round(self.hedef_3, 2),
            'stop_loss': round(self.stop_loss, 2),
            'rr_orani': self.rr_orani,
            'zaman_ufku': self.zaman_ufku,
            'senaryo_metni': self.senaryo_metni
        }


def create_action_plan(signal_data, support_levels, resistance_levels, current_price, narrative):
    """Create a rule-based action plan from S/R levels."""
    yon = narrative.get('yon', 'LONG')

    if yon in ('LONG', 'BEKLE'):
        entry_low = support_levels[0] * 0.998 if support_levels else current_price * 0.99
        entry_high = support_levels[0] * 1.005 if support_levels else current_price * 1.01
        stop = support_levels[1] * 0.995 if len(support_levels) > 1 else entry_low * 0.97

        targets = []
        for r in resistance_levels[:3]:
            if r > entry_high:
                targets.append(r)
        while len(targets) < 3:
            last = targets[-1] if targets else entry_high
            targets.append(last * 1.03)

        risk = entry_high - stop
        reward = targets[0] - entry_high
        rr = reward / risk if risk > 0 else 0

        senaryo = (
            f"Fiyat {entry_low:.2f}–{entry_high:.2f} bandına çekilirse giriş yap. "
            f"İlk hedef {targets[0]:.2f}, ikinci hedef {targets[1]:.2f}. "
            f"Stop: {stop:.2f} altında kapat."
        )

        if rr < 1.5:
            senaryo += " ⚠️ Düşük Kaliteli Kurulum (R:R < 1.5)"

        return ActionPlan(
            yon='LONG',
            giris_bolgesi=(round(entry_low, 2), round(entry_high, 2)),
            hedef_1=targets[0], hedef_2=targets[1], hedef_3=targets[2],
            stop_loss=stop, rr_orani=round(rr, 2),
            zaman_ufku='1-3 gün',
            senaryo_metni=senaryo
        )

    else:  # SHORT
        entry_low = resistance_levels[0] * 0.995 if resistance_levels else current_price * 0.99
        entry_high = resistance_levels[0] * 1.002 if resistance_levels else current_price * 1.01
        stop = resistance_levels[0] * 1.01 if resistance_levels else entry_high * 1.02

        targets = []
        for s in support_levels[:3]:
            if s < entry_low:
                targets.append(s)
        while len(targets) < 3:
            last = targets[-1] if targets else entry_low
            targets.append(last * 0.97)

        risk = stop - entry_high
        reward = entry_low - targets[0] if targets else 0
        rr = reward / risk if risk > 0 else 0

        senaryo = (
            f"Fiyat {entry_high:.2f} direncine yaklaştığında short gir. "
            f"İlk hedef {targets[0]:.2f}. Stop: {stop:.2f} üstünde kapat."
        )

        return ActionPlan(
            yon='SHORT',
            giris_bolgesi=(round(entry_low, 2), round(entry_high, 2)),
            hedef_1=targets[0], hedef_2=targets[1], hedef_3=targets[2],
            stop_loss=stop, rr_orani=round(rr, 2),
            zaman_ufku='1-3 gün',
            senaryo_metni=senaryo
        )
