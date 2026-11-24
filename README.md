# NILM Projesi

Ekip: Yusuf (veri & donanım), Ersin (modeller), Kamil (değerlendirme & web paneli).

## Ortak kararlar
- **Veri biçimi** (`nilm/data/schema.py`): her kayıt `timestamp`, `aggregate_w`, `appliance_w` (+ `house`, `appliance`).
- **Model arayüzü** (`nilm/models/base.py`): her model `fit(train)` ve `predict(aggregate)` sağlar.
- **Sonuç tablosu** (`results/results.csv`): `model, dataset, appliance, mae, sae, f1, tl_error, predict_ms` — `nilm/eval/results.py` ile yazılır.
- **İzlenecek cihazlar**: `nilm/config.py` içindeki `APPLIANCES` (ekipçe kesinleştirilecek).

## Dallar
`main` korumalı; herkes `yusuf/...`, `ersin/...`, `kamil/...` dallarında çalışır, PR ile birleştirir.

## Klasörler
- `nilm/data` – yükleme, temizleme, pencereleme, ev bazlı ayırma (Yusuf)
- `nilm/models` – temel model, seq2point, BERT4NILM (Ersin)
- `nilm/eval` – metrikler ve sonuç tablosu (Kamil)
- `data/` – ham ve işlenmiş veri (git'e girmez)
