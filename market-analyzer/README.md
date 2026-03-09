# Market Analyzer

Python tabanlı, çok varlıklı piyasa analiz sistemi. BIST & ABD hisseleri, kripto paralar, forex ve emtialar için teknik analiz yaparak interaktif HTML raporları üretir.

## Özellikler

- **Çoklu varlık desteği**: BIST hisseleri, ABD hisseleri, kripto, forex, emtia
- **6 zaman dilimi**: Günlük, Haftalık, Aylık, 3 Aylık, Yıllık, 5 Yıllık
- **Teknik göstergeler**: RSI, MACD, Bollinger Bands, EMA 20/50/200
- **Destek/Direnç tespiti**: Otomatik pivot noktası algılama
- **Trend analizi**: -100 ile +100 arası puanlama sistemi
- **Aksiyon planları**: Long/Short giriş bölgeleri, hedefler, stop-loss, R:R oranları
- **Senaryo ağacı**: Sade Türkçe "ne yapmalısın?" önerileri
- **İnteraktif grafikler**: Plotly ile dark tema candlestick chartlar
- **Türkçe raporlama**: Tüm analizler Türkçe
- **Opsiyonel AI analizi**: Claude API ile zenginleştirilmiş analizler
- **Otomatik zamanlama**: APScheduler ile cron tabanlı çalıştırma

## Kurulum

```bash
cd market-analyzer
pip install -r requirements.txt
```

### .env Dosyası (Opsiyonel — AI analizi için)

```bash
cp .env.example .env
# .env dosyasını düzenleyip ANTHROPIC_API_KEY'inizi ekleyin
```

## Kullanım

### Temel Kullanım

```bash
# Tüm watchlist'i analiz et
python analyze.py

# AI destekli analiz (ANTHROPIC_API_KEY gerekli)
python analyze.py --ai

# Sadece belirli bir kategori
python analyze.py --category "Kripto Para"

# Sadece belirli bir sembol
python analyze.py --symbol THYAO.IS

# Çıktı dosyası belirle
python analyze.py --output ./my_report.html

# Yardım
python analyze.py --help
```

### Otomatik Zamanlama

```bash
# Zamanlanmış görevleri listele
python scheduler/run_scheduler.py --list-schedules

# Zamanlayıcıyı başlat
python scheduler/run_scheduler.py
```

Zamanlama ayarları: `scheduler/schedule_config.json`

## Watchlist Düzenleme

`config/watchlist.json` dosyasını düzenleyerek sembol ekleyip çıkarabilirsiniz.

### Ticker Formatları

| Varlık Türü | Format | Örnek |
|---|---|---|
| BIST Hisseleri | `SEMBOL.IS` | `THYAO.IS`, `GARAN.IS` |
| ABD Hisseleri | `SEMBOL` | `AAPL`, `NVDA` |
| Kripto | `SEMBOL-USD` | `BTC-USD`, `ETH-USD` |
| Forex | `PARITE=X` | `EURUSD=X`, `USDTRY=X` |
| Emtia (Futures) | `SEMBOL=F` | `GC=F` (Altın), `CL=F` (Petrol) |

### Yeni Kategori Ekleme

```json
{
  "Yeni Kategori": {
    "symbols": ["TICKER1", "TICKER2"],
    "currency": "USD",
    "display_names": {
      "TICKER1": "Görünen Ad 1"
    }
  }
}
```

## Proje Yapısı

```
market-analyzer/
├── config/watchlist.json       # Enstrüman listesi
├── src/
│   ├── data_fetcher.py         # yfinance veri çekme + cache
│   ├── indicators.py           # Teknik göstergeler
│   ├── trend_analyzer.py       # Trend puanlama
│   ├── narrative_engine.py     # Senaryo + aksiyon planları
│   ├── report_writer.py        # Türkçe yorum üreteci
│   ├── ai_analyst.py           # Claude API entegrasyonu
│   ├── chart_builder.py        # Plotly grafik üreteci
│   └── report_template.py      # HTML şablonu
├── outputs/                    # Üretilen raporlar
├── scheduler/
│   ├── run_scheduler.py        # Otomatik çalıştırıcı
│   └── schedule_config.json    # Zamanlama ayarları
├── analyze.py                  # Ana giriş noktası (CLI)
└── requirements.txt
```

## Rapor Yapısı

Rapor "sonuç önce" (conclusion-first) prensibine göre tasarlanmıştır:

1. **Günün Fırsatları** — En iyi 3-5 kurulum
2. **Özet Tablo** — Tüm enstrümanlar tek bakışta (sıralanabilir)
3. **Enstrüman Kartları** — Her biri 4 katmanlı:
   - Katman 1: Durum badge'i + fiyat (her zaman görünür)
   - Katman 2: Sade Türkçe özet + senaryo ağacı (her zaman görünür)
   - Katman 3: Grafik + narratif (tıkla-aç)
   - Katman 4: Detaylı aksiyon planları (tıkla-aç)

## Lisans

Bu proje kişisel kullanım içindir. Yatırım tavsiyesi niteliği taşımaz.
