# NILM Projesi

Ekip: Yusuf (veri), Ersin (modeller), Kamil (değerlendirme & web paneli).

Ayrıntılı proje belgesi: [PROJE.md](PROJE.md)

## Ortak kararlar
- **Veri biçimi** (`nilm/data/schema.py`): her kayıt `timestamp`, `aggregate_w`, `appliance_w` (+ `house`, `appliance`).
- **Model arayüzü** (`nilm/models/base.py`): her model `fit(train)` ve `predict(aggregate)` sağlar.
- **Sonuç tablosu** (`results/results.csv`): `model, dataset, appliance, mae, sae, f1, tl_error, predict_ms` — `nilm/eval/results.py` ile yazılır.
- **İzlenecek cihazlar**: `nilm/config.py` içindeki `APPLIANCES` (ekipçe kesinleştirilecek).

## Kapsam
Yalnızca açık veri seti (UK-DALE) kullanılır; kendi evimizde ölçüm yapılmaz. "Hiç görülmeyen ev" testi için UK-DALE ev 2 ayrılır.

## Veri
```
python -m scripts.download_ukdale   # data/raw/ukdale.h5
python -m scripts.inspect_ukdale    # evler, cihazlar, tarih aralıkları
python -m scripts.prepare_ukdale    # data/processed/{cihaz}.h5 + örnek CSV
python -m scripts.veri_sekilleri    # rapor şekilleri -> results/figures/veri/ (6 PNG)
```

## Model eğitimi için veri (Ersin)
`data/processed/{cihaz}.h5` dosyaları hazır olunca (USB ile alınır, git'te yok):
```python
from nilm.data.dataset import make_datasets
train, val, test, norm = make_datasets("fridge", window=599, stride=1)
loader = torch.utils.data.DataLoader(train, batch_size=256, shuffle=True)   # x: (B, 599), y: (B,)
watts = norm.y_inverse(pred)   # tahmini Watt'a çevirir
```
Pencereler eğitim sırasında kesilir (bellek ~0.1 GB; hepsini tutan `prep.windows` ev 1'de ~25 GB ister).
`stride=10` eğitimi hızlandırır; val/test için `val_stride` ile seyreltilebilir.

## seq2point modeli yazarken (Ersin)
`nilm/models/windowed.py` içindeki `WindowedModel`'den türet; yalnızca `fit` ve `predict_batch` yaz. `predict`
hazır: giriş dizisini kenarlardan genişletip her örnek için bir pencere üretir, çıktıyı girişle aynı
uzunlukta ve hizalı verir (değerlendirme bunu şart koşar). Eğitimde `nilm.data.dataset.WindowDataset`,
çıkarımda `predict_batch` aynı pencereleri görür (testle doğrulandı).

## Dallar
`main` korumalı; herkes `yusuf/...`, `ersin/...`, `kamil/...` dallarında çalışır, PR ile birleştirir.

## Klasörler
- `nilm/data` – yükleme, temizleme, pencereleme, ev bazlı ayırma (Yusuf)
- `nilm/models` – temel model, seq2point, BERT4NILM (Ersin)
- `nilm/eval` – metrikler ve sonuç tablosu (Kamil)
- `data/` – ham ve işlenmiş veri (git'e girmez)

## Değerlendirme ve panel (Kamil)
```bash
pip install -r requirements.txt
python -m pytest -q                         # metrik testleri
python -m scripts.run_eval --synthetic --fresh   # sahte veriyle deneme (gerçek veri: --data <dosya>)
python -m nilm.eval.report                  # results/summary.csv + results/figures/*.png
streamlit run panel/app.py                  # web paneli
```
- Yeni model eklemek için `scripts/run_eval.py` içindeki `MODELS` sözlüğüne sınıfı eklemek yeterli.
- F1 için cihaz bazlı AÇIK eşikleri `nilm/config.py` → `ON_THRESHOLD_W`.
