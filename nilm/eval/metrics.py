"""Değerlendirme metrikleri. Tüm girdiler W cinsinden, aynı uzunlukta dizilerdir."""
import numpy as np


def _check(y, p):
    y = np.asarray(y, dtype=float)
    p = np.asarray(p, dtype=float)
    if y.shape != p.shape or y.ndim != 1:
        raise ValueError(f"y ve p aynı uzunlukta 1B dizi olmalı: {y.shape} vs {p.shape}")
    if y.size == 0:
        raise ValueError("Boş dizi")
    if not (np.isfinite(y).all() and np.isfinite(p).all()):
        raise ValueError("NaN/sonsuz değer var")
    return y, p


def mae(y, p):
    """Ortalama mutlak hata (W)."""
    y, p = _check(y, p)
    return float(np.mean(np.abs(y - p)))


def sae(y, p):
    """Toplam enerji hatası: |toplam tahmin - toplam gerçek| / toplam gerçek.
    Gerçek enerji 0 ise tanımsızdır, NaN döner."""
    y, p = _check(y, p)
    if y.sum() <= 0:
        return float("nan")
    return float(abs(p.sum() - y.sum()) / y.sum())


def f1_on_off(y, p, threshold_w=15.0):
    """Cihaz AÇIK/KAPALI sınıflandırması için F1. Hiç AÇIK örnek yoksa ve
    tahmin de yoksa 1.0 (doğru bildi), tahmin varsa 0.0 döner."""
    y, p = _check(y, p)
    yt, pt = y > threshold_w, p > threshold_w
    tp = np.sum(yt & pt)
    fp = np.sum(~yt & pt)
    fn = np.sum(yt & ~pt)
    if tp + fp + fn == 0:
        return 1.0
    return float(2 * tp / (2 * tp + fp + fn))


def energy_kwh(x, sample_period_s):
    """W cinsinden güç dizisini kWh'a çevirir."""
    x = np.asarray(x, dtype=float)
    return float(x.sum() * sample_period_s / 3600 / 1000)


def bill_tl(x, sample_period_s, tl_per_kwh):
    """Güç dizisinin TL cinsinden tutarı."""
    return energy_kwh(x, sample_period_s) * tl_per_kwh


def tl_error(y, p, sample_period_s, tl_per_kwh):
    """Cihaz faturasındaki mutlak hata (TL)."""
    y, p = _check(y, p)
    return float(abs(bill_tl(p, sample_period_s, tl_per_kwh) - bill_tl(y, sample_period_s, tl_per_kwh)))
