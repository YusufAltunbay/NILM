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


# ---- Panel için uzun biçimli okuma (docs: PROJE.md 5.4) -------------------------------------
COLUMNS = ["timestamp", "house", "appliance", "aggregate_w", "appliance_w", "predicted_w"]


def to_frame(test: pd.DataFrame, predicted) -> pd.DataFrame:
    """Test verisi + tahmin dizisi -> panelin kullandığı uzun tablo (COLUMNS)."""
    if len(test) != len(predicted):
        raise ValueError(f"Uzunluk uyuşmuyor: {len(test)} vs {len(predicted)}")
    df = test[["timestamp", "house", "appliance", "aggregate_w", "appliance_w"]].copy()
    df["predicted_w"] = np.asarray(predicted, dtype="float32")
    return df[COLUMNS]


def available(root: Path | None = None) -> list[tuple[str, str, int]]:
    """Diskteki (model, cihaz, ev) üçlüleri; cihaz adı boşluklu (config.APPLIANCES)."""
    out = []
    for f in sorted(Path(root or DIR).glob("*__*__house*.h5")):
        model, appliance, house = f.stem.split("__")
        out.append((model, appliance.replace("_", " "), int(house.removeprefix("house"))))
    return out


def load_all(root: Path | None = None, models=None, appliances=None, houses=None) -> pd.DataFrame:
    """Seçilen model/cihaz/ev tahminlerini tek tabloda birleştirir (COLUMNS + 'model').

    Hiç süzgeç verilmezse hepsi okunur (büyük olabilir); panel yalnızca gösterdiği
    model/cihaz/evi isteyerek bellekte az yer tutar. Klasör boşsa boş tablo döner.
    """
    frames = []
    for model, app, house in available(root):
        if (models and model not in models) or (appliances and app not in appliances)                 or (houses and house not in houses):
            continue
        d = load(model, app, house, root).rename(columns={"pred_w": "predicted_w"})
        d["house"], d["appliance"], d["model"] = house, app, model
        frames.append(d[COLUMNS + ["model"]])
    if not frames:
        return pd.DataFrame(columns=COLUMNS + ["model"])
    return pd.concat(frames, ignore_index=True)
