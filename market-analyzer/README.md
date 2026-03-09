# Market Analyzer

Python tabanlı çok varlıklı piyasa analiz sistemi. BIST hisseleri, ABD hisseleri, kripto para, forex ve emtialar için teknik analiz raporu üretir.

## Özellikler

- **6 Zaman Dilimi**: Günlük, Haftalık, Aylık, 3 Aylık, Yıllık, 5 Yıllık
- **Teknik Göstergeler**: RSI(14), MACD(12,26,9), Bollinger Bands(20,2), EMA 20/50/200
- **Destek/Direnç**: Otomatik pivot tespiti ve güç skorlaması
- **Aksiyon Durumu**: Al / Sat / İzle / Nötr — her enstrüman için
- **Günün Fırsatları**: En yüksek skorlu 4-5 kurulum
- **Long/Short Planları**: Giriş bölgesi, hedefler, stop-loss, R:R oranı
- **Senaryo Ağacı**: Yalın Türkçe ile 2-3 senaryo
- **AI Analiz**: İsteğe bağlı Claude API entegrasyonu
- **HTML Rapor**: Tek dosya, tarayıcıda açılır, Plotly grafikleri

---

## Kurulum

### 1. Bağımlılıkları yükle

```bash
cd market-analyzer
pip install -r requirements.txt
```

### 2. `.env` dosyası oluştur (AI analiz için)

```bash
cp .env.example .env
# .env dosyasını aç ve ANTHROPIC_API_KEY değerini gir
```

---

## Kullanım

### Temel kullanım (tüm enstrümanlar)

```bash
python analyze.py
```

### AI analizi etkin

```bash
python analyze.py --ai
```

### Tek kategori

```bash
python analyze.py --category "Kripto Para"
python analyze.py --category "BIST Hisseleri"
```

### Tek enstrüman

```bash
python analyze.py --symbol THYAO.IS
python analyze.py --symbol BTC-USD
```

### Çıktı dosyası belirt

```bash
python analyze.py --output ./raporlar/sabah.html
```

---

## Watchlist Düzenleme

`config/watchlist.json` dosyasını düzenleyerek enstrüman ekleyip çıkarabilirsin:

```json
{
  "categories": {
    "BIST Hisseleri": {
      "symbols": ["THYAO.IS", "GARAN.IS"],
      "currency": "TRY"
    },
    "Kripto Para": {
      "symbols": ["BTC-USD", "ETH-USD"],
      "currency": "USD"
    }
  }
}
```

### Ticker Formatları

| Varlık Türü | Format | Örnekler |
|---|---|---|
| BIST Hisseleri | `SEMBOL.IS` | `THYAO.IS`, `GARAN.IS`, `ASELS.IS` |
| ABD Hisseleri | `SEMBOL` | `AAPL`, `NVDA`, `TSLA` |
| Kripto Para | `SEMBOL-USD` | `BTC-USD`, `ETH-USD`, `SOL-USD` |
| Forex | `PARITE=X` | `EURUSD=X`, `USDTRY=X`, `GBPUSD=X` |
| Emtia | `KOD=F` | `GC=F` (Altın), `SI=F` (Gümüş), `CL=F` (Petrol), `NG=F` (Doğalgaz) |

---

## Otomatik Zamanlama

### APScheduler ile

```bash
python scheduler/run_scheduler.py
```

Zamanlamayı görüntüle:

```bash
python scheduler/run_scheduler.py --list-schedules
```

### Zamanlama yapılandırması

`scheduler/schedule_config.json` dosyasını düzenle:

```json
{
  "jobs": [
    {
      "name": "Sabah Raporu",
      "cron": "0 9 * * 1-5",
      "description": "Hafta içi 09:00'da çalışır",
      "ai_enabled": false,
      "output_dir": "./outputs"
    }
  ]
}
```

### Cron ile (Linux/macOS)

```bash
# Her sabah 09:00'da (crontab -e ile ekle)
0 9 * * 1-5 cd /path/to/market-analyzer && python analyze.py >> logs/cron.log 2>&1
```

### Windows Task Scheduler

- Görev Zamanlayıcı'yı aç
- Yeni görev oluştur
- Program: `python`
- Argümanlar: `C:\path\to\market-analyzer\analyze.py`
- Tetikleyici: Her gün 09:00

---

## Claude AI Analizi Etkinleştirme

1. [Anthropic Console](https://console.anthropic.com)'dan API anahtarı al
2. `.env` dosyasına ekle: `ANTHROPIC_API_KEY=sk-ant-...`
3. `--ai` flag ile çalıştır: `python analyze.py --ai`

AI analizi başarısız olursa sistem otomatik olarak kural tabanlı analize döner.

---

## Rapor Yapısı

Üretilen HTML raporu tarayıcıda açılır (sunucu gerekmez):

```
outputs/report_YYYYMMDD_HHMM.html
```

### Rapor Katmanları

1. **Header**: Aksiyon durumu rozeti, fiyat, değişim
2. **Özet**: "Ne yapmalısın?" — Giriş/Hedef/Stop
3. **Senaryo Ağacı**: 2-3 yalın Türkçe senaryo
4. **Teknik Detay** (tıklayarak açılır): Plotly grafikler + zaman dilimi sekmeleri
5. **Aksiyon Planları** (tıklayarak açılır): Long/Short kurulum detayı

---

## Proje Yapısı

```
market-analyzer/
├── config/
│   └── watchlist.json       # Enstrüman listesi
├── src/
│   ├── data_fetcher.py      # yfinance wrapper + önbellekleme
│   ├── indicators.py        # RSI, MACD, BB, EMA, Destek/Direnç
│   ├── trend_analyzer.py    # Trend skoru (-100 ile +100)
│   ├── narrative_engine.py  # Narratif + aksiyon planları
│   ├── report_writer.py     # Kural tabanlı Türkçe yorum
│   ├── ai_analyst.py        # Claude API entegrasyonu
│   ├── chart_builder.py     # Plotly grafik üretici
│   └── report_template.py  # Jinja2 HTML şablonu
├── outputs/                 # Üretilen raporlar
├── cache/                   # Veri önbelleği
├── logs/                    # Log dosyaları
├── scheduler/
│   ├── run_scheduler.py     # APScheduler çalıştırıcı
│   └── schedule_config.json # Zamanlama yapılandırması
├── analyze.py               # Ana giriş noktası (CLI)
└── requirements.txt
```

---

## Veri Kaynakları

Tüm fiyat verileri **yfinance** üzerinden Yahoo Finance API'sinden çekilir. Gerçek zamanlı değil, güncel gecikmeli verilerdir.

## Yasal Uyarı

Bu araç yalnızca teknik analiz amaçlıdır ve **yatırım tavsiyesi değildir**. Finansal kararlar için profesyonel danışmanlık alınız.
