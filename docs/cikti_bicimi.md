# Çıktı biçimi (değerlendirme ↔ panel sözleşmesi)

Değerlendirme kodu ve panel yalnızca bu iki çıktıyı kullanır. Biçim değişirse panel bozulur,
bu yüzden değişiklik önce ekipçe konuşulur.

## 1) `results/results.csv` — metrikler (her model × cihaz × test evi için bir satır)
| sütun | anlamı |
|---|---|
| model | model adı (tahmin dosyasının adıyla aynı) |
| dataset | `<kaynak>:house<N>(<tür>)`, tür = `test` veya `unseen` |
| appliance | cihaz adı (`config.APPLIANCES`) |
| mae | ortalama mutlak hata (W) |
| sae | toplam enerji hatası (oran) |
| f1 | AÇIK/KAPALI F1 |
| tl_error | fatura hatası (TL) |
| predict_ms | tahmin süresi (ms) |

## 2) `results/predictions/<model>.csv.gz` — tahminler (model başına tek dosya)
| sütun | anlamı |
|---|---|
| timestamp | UTC zaman damgası |
| house | ev numarası |
| appliance | cihaz adı |
| aggregate_w | toplam (ana sayaç) güç, W |
| appliance_w | cihazın gerçek gücü, W |
| predicted_w | modelin tahmini, W |

Kurallar: yalnızca **test** edilen evler yazılır; güçler W cinsindendir; örnekleme aralığı
`config.SAMPLE_PERIOD_S`; her model kendi dosyasını yazar (`MeanModel` -> `mean.csv.gz`).
Dosyalar `scripts/run_eval.py` ile üretilir; Ersin'in modelleri de `MODELS` sözlüğüne
eklenince aynı yoldan yazılır.
