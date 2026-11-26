"""Klasik (öğrenmesiz) temel model: eşik / seviye eşleşmesi.

Fikir: cihaz açılınca toplam güç yaklaşık cihazın tipik gücü kadar sıçrar, kapanınca
o kadar düşer. Sıçramayı "açıldı", düşüşü "kapandı" sayar; açıkken tipik gücü tahmin eder.
"""
import numpy as np
import pandas as pd

from nilm import config
from nilm.models.base import NILMModel


def _run_lengths(mask: np.ndarray) -> np.ndarray:
    """True değerlerin ardışık uzunlukları."""
    m = np.concatenate([[0], mask.astype(np.int8), [0]])
    d = np.diff(m)
    starts, ends = np.flatnonzero(d == 1), np.flatnonzero(d == -1)
    return ends - starts


class ThresholdModel(NILMModel):
    """Eğitimden öğrenilenler: açık seviye (W), en uzun makul açık kalma süresi (adım).

    edge_frac: toplamdaki sıçrama, cihaz seviyesinin bu kadarı kadarsa kenar sayılır.
    """
    name = "threshold"

    def __init__(self, edge_frac=0.6, max_jump=1.6, match_tol=0.5, keep_unmatched=None):
        self.edge_frac = edge_frac        # sıçrama >= edge_frac * seviye
        self.max_jump = max_jump          # sıçrama <= max_jump * seviye (çok büyük = başka cihaz)
        self.match_tol = match_tol        # düşüş, sıçramadan en fazla %50 farklı olabilir
        self.keep_unmatched = keep_unmatched  # None: kısa çalışan cihazda (kettle) at, uzunda (fridge) süre sınırıyla yaz

    def fit(self, train: pd.DataFrame, val: pd.DataFrame | None = None):
        app = train["appliance"].iloc[0]
        self.threshold_ = config.ON_THRESHOLD_W.get(app, config.DEFAULT_ON_THRESHOLD_W)
        w = train["appliance_w"].to_numpy()
        on = w > self.threshold_
        self.level_ = float(w[on].mean()) if on.any() else 0.0
        runs = _run_lengths(on)
        self.max_len_ = int(np.quantile(runs, 0.99)) if len(runs) else 1
        median_run = float(np.median(runs)) if len(runs) else 0.0
        self.keep_unmatched_ = (median_run >= 100 if self.keep_unmatched is None
                                else self.keep_unmatched)  # 100 adım = 10 dk
        return self

    def predict(self, aggregate: np.ndarray) -> np.ndarray:
        agg = np.asarray(aggregate, dtype=float)
        out = np.zeros(len(agg))
        if self.level_ <= 0 or len(agg) < 2:
            return out
        d = np.diff(agg, prepend=agg[0])
        step = self.edge_frac * self.level_
        up = (d >= step) & (d <= self.max_jump * self.level_)
        down = d <= -step
        on_at, rise = None, 0.0
        for i in np.flatnonzero(up | down):
            if on_at is None:
                if up[i]:
                    on_at, rise = i, d[i]
            elif i - on_at > self.max_len_:  # kapanış bulunamadı: takılı kalma
                if self.keep_unmatched_:
                    out[on_at:on_at + self.max_len_] = self.level_
                on_at, rise = (i, d[i]) if up[i] else (None, 0.0)
            elif down[i] and abs(abs(d[i]) - rise) <= self.match_tol * rise:
                out[on_at:i] = self.level_  # sıçrama ile düşüş büyüklükçe eşleşti
                on_at = None
        if on_at is not None and self.keep_unmatched_:
            out[on_at:on_at + self.max_len_] = self.level_
        return np.clip(np.minimum(out, agg), 0, None)
