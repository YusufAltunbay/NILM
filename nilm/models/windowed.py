"""seq2point tarzı modeller için pencereli çıkarım.

NILMModel.predict, girişle AYNI uzunlukta çıktı vermek zorundadır. seq2point ise her pencere için
tek bir değer (pencere ortasındaki cihaz gücü) üretir, ham çıktı window-1 örnek kısa kalır.
Burada giriş dizisinin iki ucu kenar değerleriyle genişletilir; böylece her örnek için o örnek
merkezde olan bir pencere vardır ve çıktı girişle birebir hizalı olur.

Ersin'in modeli yalnızca predict_batch'i yazar:

    class Seq2Point(WindowedModel):
        name = "seq2point"
        def fit(self, train):
            self.fit_normalizer(train)
            ...  # nilm.data.dataset.WindowDataset ile eğit
            return self
        def predict_batch(self, x):          # x: (B, window) float32, normalleştirilmiş toplam güç
            with torch.no_grad():
                return self.net(torch.from_numpy(x)).squeeze(-1).numpy()   # (B,) normalleştirilmiş cihaz gücü
"""
from abc import abstractmethod

import numpy as np
import pandas as pd

from nilm.data.prep import Normalizer
from nilm.models.base import NILMModel


def sliding_predict(batch_fn, aggregate, norm: Normalizer, window=599, batch_size=4096) -> np.ndarray:
    """aggregate (W) -> aynı uzunlukta cihaz gücü (W).

    batch_fn: (B, window) float32 normalleştirilmiş toplam -> (B,) normalleştirilmiş cihaz gücü.
    Sonuç [0, toplam] aralığına kırpılır (cihaz toplamı aşamaz, negatif olamaz).
    """
    if window % 2 == 0:
        raise ValueError("window tek sayı olmalı")
    agg = np.asarray(aggregate, dtype="float64")
    n = len(agg)
    if n == 0:
        return np.empty(0, dtype="float32")
    half = window // 2
    padded = np.pad(norm.x(agg), half, mode="edge")
    view = np.lib.stride_tricks.sliding_window_view(padded, window)  # tam n pencere
    out = np.empty(n, dtype="float32")
    for i in range(0, n, batch_size):
        y = np.asarray(batch_fn(np.ascontiguousarray(view[i:i + batch_size]))).reshape(-1)
        if len(y) != len(view[i:i + batch_size]):
            raise ValueError(f"batch_fn {len(y)} değer döndürdü, {len(view[i:i + batch_size])} bekleniyordu")
        out[i:i + batch_size] = y
    return np.clip(norm.y_inverse(out), 0.0, agg).astype("float32")


class WindowedModel(NILMModel):
    """Pencereli modeller için taban sınıf: predict hazır, predict_batch ve fit modelin işi."""
    window = 599
    batch_size = 4096
    norm: Normalizer | None = None

    def fit_normalizer(self, train: pd.DataFrame) -> Normalizer:
        """Ölçekleme istatistiklerini yalnızca eğitim verisinden öğrenir."""
        self.norm = Normalizer().fit(train)
        return self.norm

    @abstractmethod
    def predict_batch(self, x: np.ndarray) -> np.ndarray:
        """(B, window) normalleştirilmiş toplam güç -> (B,) normalleştirilmiş cihaz gücü."""

    def predict(self, aggregate):
        if self.norm is None:
            raise RuntimeError("önce fit() çağır (norm yok)")
        return sliding_predict(self.predict_batch, aggregate, self.norm, self.window, self.batch_size)
