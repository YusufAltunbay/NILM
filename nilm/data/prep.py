"""Temizleme, normalizasyon, pencereleme ve ev bazlı ayırma."""
from dataclasses import dataclass

import numpy as np
import pandas as pd

from nilm.data.schema import validate


def clean(df: pd.DataFrame, max_gap_steps=30, max_w=20_000) -> pd.DataFrame:
    """Kısa boşlukları ileri doldurur, uzun boşlukları ve aykırı değerleri atar.

    max_gap_steps: 6 sn'de 30 adım = 3 dakikaya kadar boşluk doldurulur.
    Cihaz gücü toplamı aşamaz (ölçüm zaman kayması), o yüzden kırpılır.
    """
    df = df.copy()
    for c in ["aggregate_w", "appliance_w"]:
        df[c] = df[c].where((df[c] >= 0) & (df[c] <= max_w))
        df[c] = df.groupby(["house", "appliance"])[c].ffill(limit=max_gap_steps)
    df = df.dropna(subset=["aggregate_w", "appliance_w"])
    df["appliance_w"] = np.minimum(df["appliance_w"], df["aggregate_w"])
    return validate(df)


def split_by_house(df, train, val, test):
    pick = lambda hs: df[df["house"].isin(hs)].reset_index(drop=True)
    return pick(train), pick(val), pick(test)


@dataclass
class Normalizer:
    """İstatistikler yalnızca eğitim verisinden öğrenilir (sızıntı olmasın)."""
    agg_mean: float = 0.0
    agg_std: float = 1.0
    app_max: float = 1.0

    def fit(self, train):
        self.agg_mean = float(train["aggregate_w"].mean())
        self.agg_std = float(train["aggregate_w"].std()) or 1.0
        self.app_max = float(train["appliance_w"].max()) or 1.0
        return self

    def x(self, w):
        return (np.asarray(w, dtype="float32") - self.agg_mean) / self.agg_std

    def y(self, w):
        return np.asarray(w, dtype="float32") / self.app_max

    def y_inverse(self, y):
        return np.asarray(y) * self.app_max


def _segments(ts: pd.Series, period_s):
    """Zamanda kesintisiz parçaların sınırları (atılan boşluklar pencereyi bölmesin)."""
    breaks = np.flatnonzero(ts.diff().dt.total_seconds().to_numpy()[1:] > period_s) + 1
    return np.split(np.arange(len(ts)), breaks)


def windows(df, window=599, period_s=6, norm: Normalizer | None = None, stride=1):
    """seq2point pencereleri: X (N, window) toplam, y (N,) pencere ortasındaki cihaz gücü.

    Pencereler ev/cihaz ve zaman boşlukları üzerinden atlamaz.
    """
    norm = norm or Normalizer()
    X, Y = [], []
    for _, g in df.groupby(["house", "appliance"]):
        for idx in _segments(g["timestamp"].reset_index(drop=True), period_s):
            if len(idx) < window:
                continue
            a = norm.x(g["aggregate_w"].to_numpy()[idx])
            t = norm.y(g["appliance_w"].to_numpy()[idx])
            v = np.lib.stride_tricks.sliding_window_view(a, window)[::stride]
            X.append(v)
            Y.append(t[window // 2: window // 2 + len(a) - window + 1][::stride])
    if not X:
        return np.empty((0, window), "float32"), np.empty(0, "float32")
    return np.concatenate(X), np.concatenate(Y)
