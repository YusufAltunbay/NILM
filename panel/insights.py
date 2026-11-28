"""Kullanım verisinden cihaz bazında gerçek bilgiler (öneri kartlarında gösterilir).
Tahminler gürültülüdür; eşiği titreyerek geçen noktaları ayrı 'kullanım' saymamak için
kısa boşluklar birleştirilir ve çok kısa tetiklemeler sayılmaz."""
import numpy as np
import pandas as pd

from nilm import config

SMOOTH_S = 30      # güç önce bu süre boyunca ortalanır
GAP_S = 120        # bundan kısa kesintiler aynı kullanımın parçası sayılır
MIN_S = 30         # bundan kısa tetiklemeler kullanım sayılmaz


def _events(on: np.ndarray, gap: int, min_len: int):
    """Bool dizisinden (başlangıç, bitiş) çiftleri: boşluklar birleştirilir, kısalar atılır."""
    idx = np.flatnonzero(np.diff(np.r_[0, on.astype(np.int8), 0]))
    merged = []
    for s, e in zip(idx[0::2], idx[1::2]):
        if merged and s - merged[-1][1] <= gap:
            merged[-1][1] = e
        else:
            merged.append([s, e])
    return [(s, e) for s, e in merged if e - s >= min_len]


def usage_facts(ts: pd.Series, power: pd.Series, appliance: str, price: float, dt: int | None = None) -> dict:
    """Kullanım sayısı, bir kullanımın enerjisi/maliyeti, günlük çalışma süresi, en yoğun başlangıç saati."""
    thr = config.ON_THRESHOLD_W.get(appliance, config.DEFAULT_ON_THRESHOLD_W)
    dt = int(dt or config.SAMPLE_PERIOD_S)
    t = pd.DatetimeIndex(ts)
    p = np.nan_to_num(power.to_numpy(dtype=float))
    k = max(1, SMOOTH_S // dt)
    ps = pd.Series(p).rolling(k, min_periods=1, center=True).mean().to_numpy() if k > 1 else p
    ev = _events(ps > thr, gap=max(1, GAP_S // dt), min_len=max(1, MIN_S // dt))
    days = max(1.0, len(p) * dt / 86400)  # kayıtlı süre (boşluklar sayılmaz)
    n = len(ev)
    pad = k // 2  # yumuşatma olayın kenarlarını kısaltır; enerji ve süre hesabında geri eklenir
    spans = [(max(0, s - pad), min(len(p), e + pad)) for s, e in ev]
    on_wh = sum(p[s:e].sum() for s, e in spans) * dt / 3600
    on_min = sum(e - s for s, e in spans) * dt / 60
    peak = int(pd.Series(t[[s for s, _ in ev]].hour).value_counts().idxmax()) if n else None
    kwh_use = on_wh / 1000 / n if n else 0.0
    return dict(per_day=n / days, uses=n, kwh_per_use=kwh_use, tl_per_use=kwh_use * price,
                minutes_per_day=on_min / days, peak_hour=peak)


def describe(f: dict) -> list:
    """(etiket, değer) satırları. Günde çok sık açılıp kapanan cihazlarda (ör. buzdolabı) 'kullanım' yerine çevrim denir."""
    if f["uses"] == 0:
        return [("Kullanım", "bu dönemde yok")]
    if f["minutes_per_day"] > 0.9 * 1440:  # neredeyse hiç kapanmıyor: model açma/kapamayı ayırt edemiyor (ör. sabit tahmin)
        return [("Kullanım", "bu model ayırt edemiyor")]
    rows = []
    if f["per_day"] > 12:
        rows.append(("Çalışma çevrimi", f"günde ~{f['per_day']:.0f}"))
    else:
        rows.append(("Kullanım", f"günde {f['per_day']:.1f} kez"))
        rows.append(("Bir kullanım", f"{f['kwh_per_use']:.2f} kWh, {f['tl_per_use']:.2f} TL"))
    m = f["minutes_per_day"]
    rows.append(("Günlük çalışma", f"{m / 60:.1f} saat" if m >= 90 else f"{m:.0f} dk"))
    if f["peak_hour"] is not None:
        rows.append(("En yoğun saat", f"{f['peak_hour']:02d}:00-{(f['peak_hour'] + 1) % 24:02d}:00"))
    return rows
