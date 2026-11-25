"""Modellenmeyen cihazlar için TAHMİNİ enerji dağılımı (ölçüm değil).

Model 5 cihazı tahmin eder. Toplamdan bu tahminler çıkınca kalan enerji ("diğer")
aydınlatmayı, bekleme yüklerini, seçilmeyen cihazları ve modellerin hatalarını birlikte
içerir. Kullanıcının seçtiği ek cihazlara kalan enerjiden, beklenen enerjileriyle orantılı
pay verilir. Hiçbir zaman ölçülen 5 cihazın üzerine eklenmez.
"""
from dataclasses import dataclass

import numpy as np

# Kullanıcı değiştirir; yalnızca başlangıç değerleridir (ad: (nominal W, günde saat)).
DEFAULT_EXTRA_DEVICES = {
    "aydınlatma": (150.0, 5.0),
    "televizyon": (100.0, 4.0),
    "bilgisayar": (80.0, 5.0),
    "ütü": (1800.0, 0.3),
}

UNDEFINED = "tanımsız diğer"


def other_energy_kwh(aggregate_w, predictions, period_s: float) -> float:
    """Σ max(0, toplam − Σ tahmin) -> kWh. predictions: aynı uzunlukta diziler listesi."""
    agg = np.asarray(aggregate_w, dtype=float)
    pred = np.sum([np.asarray(p, dtype=float) for p in predictions], axis=0) if predictions else 0.0
    return float(np.maximum(0.0, agg - pred).sum() * period_s / 3600 / 1000)


@dataclass
class Allocation:
    kwh: dict            # cihaz -> payı (kWh); UNDEFINED anahtarı dağıtılmayan artık
    scaled: bool         # True: beklenen toplam artıktan büyüktü, paylar küçültüldü

    def tl(self, tl_per_kwh: float) -> dict:
        return {k: v * tl_per_kwh for k, v in self.kwh.items()}


def allocate_other(e_other_kwh: float, devices: dict, days: float) -> Allocation:
    """devices: {ad: (nominal_w, günde_saat)}. days: ölçüm süresi (gün).

    Σ beklenen <= artık : her cihaza beklenen enerjisi, kalan UNDEFINED'a.
    Σ beklenen >  artık : paylar orantılı küçültülür, UNDEFINED = 0.
    """
    if e_other_kwh < 0 or days < 0:
        raise ValueError("artık enerji ve gün sayısı negatif olamaz")
    expected = {n: max(0.0, w) * max(0.0, h) * days / 1000 for n, (w, h) in devices.items()}
    total = sum(expected.values())
    if total <= e_other_kwh:
        out = dict(expected)
        out[UNDEFINED] = e_other_kwh - total
        return Allocation(out, scaled=False)
    scale = e_other_kwh / total
    out = {n: e * scale for n, e in expected.items()}
    out[UNDEFINED] = 0.0
    return Allocation(out, scaled=True)
