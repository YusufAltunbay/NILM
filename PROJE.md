# NILM Projesi — Proje Belgesi

> Tek bir sayaçtan ölçülen **toplam elektrik tüketimini** cihazlara ayırarak (Non-Intrusive Load Monitoring, NILM) her cihazın ne kadar enerji harcadığını ve faturaya ne kadar yansıdığını tahmin etmek.

Son güncelleme: 24 Kasım 2026 · Depo: https://github.com/YusufAltunbay/NILM (gizli)

---

## 1. Amaç

- Evin toplam güç sinyalinden (W) seçilen cihazların güç tüketimini tahmin etmek.
- Klasik bir temel model, **seq2point** (CNN) ve **Transformer (BERT4NILM)** modellerini aynı koşullarda karşılaştırmak.
- Hataları yalnızca teknik metriklerle değil, **TL cinsinden fatura hatası** olarak da göstermek.
- Modellerin daha önce hiç görmediği bir evde ne kadar iyi çalıştığını (genelleme) ölçmek.
- Sonuçları cihaz bazlı tüketim ve tahmini fatura gösteren bir **web panelinde** sunmak.

## 2. Kapsam

| Kapsamda | Kapsam dışı |
|---|---|
| Açık veri seti: **UK-DALE** | Kendi evimizde ölçüm (akıllı priz, enerji ölçer) — zaman yetmediği için çıkarıldı |
| 4–5 cihaz | Gerçek zamanlı canlı ölçüm |
| 3 model ailesi (temel, seq2point, Transformer) | Ticari ürünleşme |
| Streamlit web paneli | Mobil uygulama |

## 3. Ekip ve sorumluluklar

| Kişi | Alan | Ana işler |
|---|---|---|
| **Yusuf** | Veri ve değerlendirme | UK-DALE indirme/doğrulama, temizleme, pencereleme, ev bazlı ayırma; değerlendirmeyi gerçek veriyle çalıştırma, sonuç tablosu otomasyonu, görülmeyen ev testi |
| **Ersin** | Modeller | Ortam kurulumu, temel model, seq2point, BERT4NILM; hiperparametre denemeleri; tahmin çıktılarının ortak biçimde kaydı |
| **Kamil** | Frontend (panel) | Streamlit paneli: cihaz bazlı tüketim (kWh/TL), gerçek ve tahmin zaman serisi, model karşılaştırma, görülmeyen ev sonuçları; canlı gösteri |

Rapor: Yusuf → veri ve değerlendirme, Ersin → modeller, Kamil → panel ve sistem tasarımı; giriş ve sonuç birlikte.

## 4. Veri seti: UK-DALE

- **Kaynak:** UK Domestic Appliance-Level Electricity (Kelly & Knottenbelt, 2015). Resmi UKERC EDC bağlantısı artık çalışmadığı için NILMTK biçimindeki `ukdale.h5` dosyası [Zenodo 13917372](https://zenodo.org/records/13917372) kaydından indiriliyor (~3.35 GB, MD5 ile doğrulanır).
- **Yapı:** `/building{n}/elec/meter{m}`; `meter1` evin toplam (ana) sayacı, diğerleri cihaz sayaçları. Cihaz–sayaç eşlemesi her binanın `metadata` özniteliğinde.
- **Biçim:** dosya pandas 0.15 ile yazılmış; güncel `pandas.HDFStore` açamadığı için okuyucu tabloları doğrudan PyTables ile okur. İndirilen dosya MD5 ile doğrulandı (3.345 GB).
- Ham veri `data/raw/`, işlenmiş veri `data/processed/` altında durur; ikisi de git'e girmez.

### Evler ve cihazlar (doğrulandı)

| Ev | Tarih aralığı | Buzdolabı | Çamaşır makinesi | Su ısıtıcısı | Bulaşık makinesi | Mikrodalga |
|---|---|---|---|---|---|---|
| 1 | 2012-11-09 → 2015-01-05 (786 gün) | ✅ (fridge freezer) | ✅ (washer dryer) | ✅ | ✅ | ✅ |
| 2 | 2013-02-17 → 2013-10-10 (234 gün) | ✅ | ✅ | ✅ | ✅ | ✅ |
| 3 | 2013-02-27 → 2013-04-08 (39 gün) | – | – | ✅ | – | – |
| 4 | 2013-03-09 → 2013-10-01 (205 gün) | – | ⚠️ | ✅ | – | ⚠️ |
| 5 | 2014-06-29 → 2014-11-13 (137 gün) | ✅ (fridge freezer) | ✅ (washer dryer) | ✅ | ✅ | ✅ |

- Aynı cihazın farklı adları `config.APPLIANCE_ALIASES` ile birleştirilir (`fridge freezer` → buzdolabı, `washer dryer` → çamaşır makinesi).
- ⚠️ Ev 4'te çamaşır makinesi ve mikrodalga **aynı sayaçta**; hangisinin çektiği ayrılamadığı için ikisi de bu evde kullanılmaz.
- Sonuç: su ısıtıcısı dışındaki dört cihaz için eğitim fiilen **yalnızca ev 1** ile yapılır (en uzun kayıt). Seçilen 5 cihaz literatürdeki standart UK-DALE kurulumuyla aynı; liste bu hâliyle kalabilir.

### Ev ayrımı

| Küme | Evler | Amaç |
|---|---|---|
| Eğitim | 1, 3, 4 | Model eğitimi, normalizasyon istatistikleri |
| Doğrulama | 5 | Hiperparametre seçimi, erken durdurma |
| Görülmeyen ev (test) | 2 | Genelleme ölçümü; eğitimde hiç kullanılmaz |

Ayrım ev bazlıdır: aynı evin verisi iki kümede birden bulunmaz, böylece zaman bazlı ayırmadaki sızıntı oluşmaz. Ev 3 ve 4 yalnızca su ısıtıcısı için eğitime katkı verir.

## 5. Ortak sözleşmeler

Herkesin kodu bu üç sözleşmeye uyar; böylece veri, model ve değerlendirme birbirinden bağımsız geliştirilebilir.

### 5.1 Veri biçimi — `nilm/data/schema.py`

| Sütun | Tür | Açıklama |
|---|---|---|
| `timestamp` | datetime (UTC) | Örnek zamanı (6 sn aralık) |
| `house` | int | UK-DALE ev numarası |
| `appliance` | str | Cihaz adı (UK-DALE etiketi) |
| `aggregate_w` | float | Evin toplam gücü (W) |
| `appliance_w` | float | Cihazın gerçek gücü (W) — "doğru cevap" |

`validate(df)` sütunları, türleri ve negatif değerleri kontrol eder.

### 5.2 Model arayüzü — `nilm/models/base.py`

```python
class NILMModel(ABC):
    name: str
    def fit(self, train: pd.DataFrame) -> "NILMModel": ...      # ortak biçim, tek cihaz
    def predict(self, aggregate: np.ndarray) -> np.ndarray: ...  # toplam W -> cihaz W, aynı uzunluk
```

Yeni model, `scripts/run_eval.py` içindeki `MODELS` sözlüğüne eklenince değerlendirmede ve panelde otomatik görünür.

### 5.3 Sonuç tablosu — `results/results.csv`

`model, dataset, appliance, mae, sae, f1, tl_error, predict_ms` — her deney bir satır. `nilm/eval/results.py` yazar, `nilm/eval/report.py` özet ve grafik üretir, panel okur.

### 5.4 Tahmin dosyaları — `nilm/eval/predictions.py`

Panel gerçek ve tahmin zaman serisini göstereceği için her deneyin tahminleri de kaydedilir:
`results/predictions/{model}__{cihaz}__house{n}.h5` (key `data`), sütunlar `timestamp, aggregate_w, appliance_w, pred_w` (W). Satır sayısı test verisiyle aynıdır (`predict` aynı uzunlukta dönmek zorunda; pencere kenarlarını 0 ile doldur).
Panel için `predictions.load_all(models=…, appliances=…, houses=…)` bu dosyaları sütunları `timestamp, house, appliance, aggregate_w, appliance_w, predicted_w, model` olan uzun bir tabloda birleştirir (`to_frame` aynı biçimi tek bir test verisi için üretir). Süzgeç verilirse yalnızca istenen dosyalar okunur: tek ev ve cihaz 1.7 M satır için ~1.6 sn, bir modelin tamamı (17.7 M satır) ~3 sn ve ~1 GB bellek.
Üretmek için: `python -m scripts.run_eval --data data/processed --save-preds`. Kaydetme `evaluate(..., save_preds=True)` ile yapılır, model tarafında ek bir şey gerekmez.

## 6. Sistem mimarisi

```
ukdale.h5 ──► ukdale.load() ──► prep.clean() ──► data/processed/{cihaz}.h5
                                                      │
                     ┌────────────────────────────────┤
                     ▼                                ▼
          prep.split_by_house()              sample_{cihaz}.csv (panel, hızlı deneme)
                     │
   Normalizer.fit(eğitim) ─► prep.windows() ─► model.fit()
                                                      │
          görülmeyen ev ─► model.predict() ─► evaluate() ─► results/results.csv
                                                                  │
                                       nilm/eval/report.py ◄──────┤
                                       panel/app.py        ◄──────┘
```

## 7. Veri hazırlama — `nilm/data/prep.py`

1. **Yeniden örnekleme:** toplam ve cihaz sinyalleri 6 sn'lik ortalamalara indirilir (`ukdale.load`).
2. **Temizleme (`clean`):** negatif ve 20 kW üstü değerler geçersiz sayılır; 3 dakikaya (30 adım) kadar boşluklar ileri doldurulur, daha uzunları atılır; cihaz gücü toplamı aşamaz (kırpılır). Ardından:
   - **Üst sınır (`config.MAX_POWER_W`):** buzdolabı 300 W, çamaşır/bulaşık makinesi 2500 W, su ısıtıcısı 3100 W, mikrodalga 3000 W. Buzdolabında kompresör kalkışında tek örneklik 1–2 kW tepeler var (günde 2–3 kez, ardından ~100 W); gerçek ama bilgi taşımıyor ve ölçeklemeyi bozuyordu.
   - **Bekleme eşiği (`config.STANDBY_W`):** mikrodalgada 100 W altı 0 sayılır. Ev 5 mikrodalga sayacı Temmuz 2014'ten itibaren zamanın %90'ında sabit 50 W gösteriyor (gerçek kullanım günde ~0.4 kez, ~1.3 kW).
3. **Ev bazlı ayırma (`split_by_house`).**
4. **Normalizasyon (`Normalizer`):** toplam güç z-skor ile, cihaz gücü eğitimdeki maksimuma bölünerek ölçeklenir. İstatistikler **yalnızca eğitim verisinden** öğrenilir; `y_inverse` tahmini Watt'a geri çevirir.
5. **Pencereleme (`windows`, `WindowDataset`):** küçük veride `prep.windows`, gerçek eğitimde bellek dostu `nilm/data/dataset.py` (`make_datasets`) kullanılır; ikisi birebir aynı pencereleri üretir.
   Pencere ayrıntısı: seq2point için 599 adımlık (~1 saat) pencere; hedef pencerenin ortasındaki cihaz gücü. Pencereler ev/cihaz sınırlarını ve atılan zaman boşluklarını aşmaz.

## 8. Modeller

| Model | Fikir | Durum |
|---|---|---|
| `MeanModel` | Eğitimdeki ortalama cihaz gücünü tahmin eder; alt sınır referansı | Hazır |
| Klasik temel model | Örn. eşik/kural tabanlı ya da kombinatoryal optimizasyon | Ersin — başlanacak |
| **seq2point** | Toplam güç penceresinden (CNN) pencere ortasındaki cihaz gücünü tahmin eder | Ersin — 2. aşama |
| **BERT4NILM** | Transformer tabanlı model; doğruluk/hız dengesi not edilecek | Ersin — 3. aşama |

Çerçeve: PyTorch. Hesaplama gücü yetmezse daha küçük model ya da ücretsiz bulut (Colab/Kaggle) kullanılır.

## 9. Değerlendirme — `nilm/eval/`

| Metrik | Tanım | Yorum |
|---|---|---|
| **MAE** | Ortalama mutlak hata (W) | Anlık güç tahmininin doğruluğu |
| **SAE** | \|Σtahmin − Σgerçek\| / Σgerçek | Toplam enerjideki sapma |
| **F1** | Açık/kapalı durum sınıflandırması | Cihaz bazlı eşik: `config.ON_THRESHOLD_W` (buzdolabı 50 W, su ısıtıcısı 2000 W, …) |
| **TL hatası** | Tahmin ve gerçek kWh farkı × birim fiyat | Kullanıcı için anlamlı hata ölçüsü |
| **Tahmin süresi** | `predict` süresi (ms) | Pratik kullanım, gerçek zamanlılık |

`scripts/run_eval.py` her model × cihaz × test evi için değerlendirme yapar; `tests/test_metrics.py` metriklerin birim testlerini içerir.

## 10. Web paneli — `panel/app.py` (Streamlit)

- Cihaz bazlı tüketim (kWh) ve tahmini fatura (TL)
- Gerçek ve tahmin edilen güç zaman serisi
- Model karşılaştırma tablosu ve grafikleri
- Görülmeyen ev sonuçları
- Veri: şimdilik sahte; gerçek veriden üretilen örnek CSV'ler hazır olunca bağlanacak

## 11. Klasör yapısı

```
NILM/
├── nilm/
│   ├── config.py          # cihazlar, ev ayrımı, birim fiyat, eşikler
│   ├── data/              # schema, UK-DALE okuyucu, prep
│   ├── models/            # NILMModel arayüzü ve modeller
│   └── eval/              # metrikler, değerlendirme, sonuç tablosu, rapor
├── panel/app.py           # Streamlit paneli
├── scripts/               # indirme, inceleme, işleme, değerlendirme, testler
├── tests/                 # birim testleri
├── data/raw, processed/   # git dışı
├── results/               # results.csv, summary.csv, figures/ (git dışı)
├── README.md
└── PROJE.md
```

## 12. Kurulum ve çalıştırma

```bash
git clone https://github.com/YusufAltunbay/NILM.git
cd NILM
pip install -r requirements.txt

# Veri
python -m scripts.download_ukdale     # data/raw/ukdale.h5 (~3.35 GB, MD5 doğrulamalı)
python -m scripts.inspect_ukdale      # ev, cihaz ve tarih aralıkları
python -m scripts.prepare_ukdale      # data/processed/{cihaz}.h5 + sample_{cihaz}.csv

# Testler
python -m pytest -q
python -m scripts.test_prep
python -m scripts.smoke_test

# Değerlendirme ve panel
python -m scripts.run_eval --data data/processed/fridge.h5
python -m nilm.eval.report
streamlit run panel/app.py
```

## 13. Git iş akışı

- `main` yalnızca PR ile güncellenir; her PR'a en az bir ekip arkadaşı bakar.
- Dal adları: `yusuf/...`, `ersin/...`, `kamil/...`.
- Büyük dosyalar (veri, `*.pt` model ağırlıkları) git'e girmez.
- Ortak dosyalar (`nilm/config.py`, sözleşmeler) değişince ekibe haber verilir.

## 14. Yol haritası (9 hafta)

| Hafta | Aşama | Yusuf | Ersin | Kamil | Çıktı |
|---|---|---|---|---|---|
| 1 | Ortak kararlar | Depo, sözleşmeler, UK-DALE indirme ✅ | Ortam kurulumu | Değerlendirme ilk sürüm ✅ | Ortak iskelet |
| 2–3 | Temel ve veri | Veri doğrulama, işleme, örnek CSV | Temel model | Panel iskeleti ✅ | İlk temel model sonucu |
| 4–5 | Derin öğrenme | Değerlendirmeyi gerçek veriyle çalıştırma, sonuç otomasyonu | seq2point | Paneli gerçek sonuçlara bağlama | Temel ve seq2point tek tabloda |
| 6–7 | Transformer ve genelleme | Görülmeyen ev (ev 2) testi | BERT4NILM | Karşılaştırma sayfası, fatura gösterimi | 3 model tek tabloda |
| 8 | Birleştirme | Sonuçların yorumu, veri belgeleri | Model analizi | Panelin son hâli, canlı gösteri hazırlığı | Bitmiş sistem |
| 9 | Rapor ve sunum | Veri ve değerlendirme bölümü | Modeller bölümü | Panel bölümü | Rapor, sunum, prova |

**Zaman daralırsa öncelik:** temel model + seq2point + TL hatası + panel; Transformer ve görülmeyen ev testi en sona.

## 15. Mevcut durum

| İş | Durum |
|---|---|
| Depo, ortak sözleşmeler | ✅ `main` |
| Değerlendirme, rapor, panel (PR #2) | ✅ `main`'e birleşti |
| UK-DALE indirme | ✅ İndirildi, MD5 doğrulandı |
| Veri hazırlama | ✅ Gerçek veriyle çalışıyor; tüm veri işleniyor |
| Modeller | ⏳ Ersin başlayacak |

## 16. Açık kararlar

- [x] Cihaz listesi — 5 cihaz tüm gerekli evlerde var (Bölüm 4)
- [x] Ev ayrımı — eğitim 1 (+3, 4 su ısıtıcısı için), doğrulama 5, test 2
- [x] ~~TL/kWh birim fiyatı~~ → 3.24 TL (Nisan 2026 mesken tarifesi, Kamil)
- [ ] Cihaz bazlı açık/kapalı eşiklerinin doğrulanması
- [x] Tahmin çıktı dosyalarının biçimi — Bölüm 5.4 (Ersin ve Kamil onaylayacak)

## 17. Riskler ve yedek planlar

| Risk | Önlem |
|---|---|
| Sayaç kaynaklı bozukluklar (ev 5 mikrodalga ofseti, buzdolabı kalkış tepeleri) | Cihaz bazlı üst sınır ve bekleme eşiği (Bölüm 7); yeni bir cihaz eklenirken dağılımı kontrol etmek |
| Eğitim fiilen tek evden (ev 1) | Görülmeyen ev sonuçlarını bu sınırlamayla yorumlamak; gerekirse ev 5'i eğitime alıp doğrulamayı ev 1'in son aylarından yapmak |
| Bazı cihazlar az evde var | Cihaz listesini veriye göre seçmek; görülmeyen ev testini cihaz bazında uyarlamak |
| Hesaplama gücü yetersiz | Daha küçük pencere/model, alt örneklenmiş veri, Colab/Kaggle GPU |
| Zaman darlığı | Bölüm 14'teki öncelik sırası |
| Panel ile model çıktısı uyumsuzluğu | Çıktı biçimini erken sabitlemek (Bölüm 16) |

## 18. Kaynaklar

- J. Kelly, W. Knottenbelt, *The UK-DALE dataset, domestic appliance-level electricity demand and whole-house demand from five UK homes*, Scientific Data, 2015. doi:10.1038/sdata.2015.7
- C. Zhang vd., *Sequence-to-point learning with neural networks for non-intrusive load monitoring*, AAAI 2018.
- Z. Yue vd., *BERT4NILM: A Bidirectional Transformer Model for Non-Intrusive Load Monitoring*, NILM Workshop 2020.
- NILMTK: https://github.com/nilmtk/nilmtk
