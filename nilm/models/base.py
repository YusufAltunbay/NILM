"""Ortak model arayüzü: değerlendirme kodu modelin türünü bilmeden çalışır."""
from abc import ABC, abstractmethod
import numpy as np
import pandas as pd


class NILMModel(ABC):
    name: str = "base"

    @abstractmethod
    def fit(self, train: pd.DataFrame) -> "NILMModel":
        """train: nilm.data.schema biçiminde, tek cihaz."""

    @abstractmethod
    def predict(self, aggregate: np.ndarray) -> np.ndarray:
        """aggregate: toplam güç (W) dizisi -> aynı uzunlukta cihaz gücü (W)."""


class MeanModel(NILMModel):
    """En basit referans: eğitimdeki ortalama cihaz gücünü tahmin eder."""
    name = "mean"

    def fit(self, train):
        self.mean_ = float(train["appliance_w"].mean())
        return self

    def predict(self, aggregate):
        return np.minimum(np.full(len(aggregate), self.mean_), aggregate)
