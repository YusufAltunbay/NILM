"""Tahmin çıktıları için ortak biçim (Ersin yazar, Kamil'in paneli okur).

Dosya: results/predictions/{model}__{cihaz}__house{n}.h5, key="data"
Sütunlar: timestamp (UTC), aggregate_w, appliance_w (gerçek), pred_w (tahmin) — hepsi W.
Satır sayısı test verisiyle aynıdır; modelin ilk/son window//2 örnek için tahmini
yoksa 0 ile doldurulur (predict zaten aynı uzunlukta dönmek zorunda).
"""
from pathlib import Path

import numpy as np
import pandas as pd

DIR = Path(__file__).resolve().parents[2] / "results" / "predictions"


def path(model: str, appliance: str, house: int, root: Path | None = None) -> Path:
    return Path(root or DIR) / f"{model}__{appliance.replace(' ', '_')}__house{house}.h5"


def save(model: str, appliance: str, house: int, test: pd.DataFrame, pred: np.ndarray,
         root: Path | None = None) -> Path:
    if len(pred) != len(test):
        raise ValueError(f"tahmin uzunluğu {len(pred)} != test uzunluğu {len(test)}")
    out = pd.DataFrame({"timestamp": test["timestamp"].to_numpy(),
                        "aggregate_w": test["aggregate_w"].to_numpy(dtype="float32"),
                        "appliance_w": test["appliance_w"].to_numpy(dtype="float32"),
                        "pred_w": np.asarray(pred, dtype="float32")})
    p = path(model, appliance, house, root)
    p.parent.mkdir(parents=True, exist_ok=True)
    out.to_hdf(p, key="data", mode="w", complevel=5)
    return p


def load(model: str, appliance: str, house: int, root: Path | None = None) -> pd.DataFrame:
    return pd.read_hdf(path(model, appliance, house, root), "data")
