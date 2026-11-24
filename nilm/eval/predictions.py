"""Tahmin dosyaları: panel ve değerlendirme aynı dosyaları okur.

Biçim (docs/cikti_bicimi.md): results/predictions/<model>.csv.gz, sütunlar
timestamp, house, appliance, aggregate_w, appliance_w (gerçek), predicted_w.
"""
from pathlib import Path

import pandas as pd

PRED_DIR = Path(__file__).resolve().parents[2] / "results" / "predictions"
COLUMNS = ["timestamp", "house", "appliance", "aggregate_w", "appliance_w", "predicted_w"]


def to_frame(test: pd.DataFrame, predicted) -> pd.DataFrame:
    """Şemaya uygun test verisi + tahmin dizisi -> tahmin tablosu."""
    if len(test) != len(predicted):
        raise ValueError(f"Uzunluk uyuşmuyor: {len(test)} vs {len(predicted)}")
    df = test[["timestamp", "house", "appliance", "aggregate_w", "appliance_w"]].copy()
    df["predicted_w"] = list(predicted)
    return df[COLUMNS]


def save(model_name: str, frame: pd.DataFrame, directory: Path | None = None):
    directory = Path(directory or PRED_DIR)
    directory.mkdir(parents=True, exist_ok=True)
    missing = set(COLUMNS) - set(frame.columns)
    if missing:
        raise ValueError(f"Eksik sütunlar: {missing}")
    frame[COLUMNS].to_csv(directory / f"{model_name}.csv.gz", index=False)


def load_all(directory: Path | None = None) -> pd.DataFrame:
    """Klasördeki tüm modellerin tahminleri; 'model' sütunu dosya adından gelir.
    Klasör yoksa ya da boşsa boş tablo döner."""
    directory = Path(directory or PRED_DIR)
    frames = []
    for f in sorted(directory.glob("*.csv.gz")):
        df = pd.read_csv(f, parse_dates=["timestamp"])
        missing = set(COLUMNS) - set(df.columns)
        if missing:
            raise ValueError(f"{f.name}: eksik sütunlar {missing}")
        df["model"] = f.name[: -len(".csv.gz")]
        frames.append(df)
    if not frames:
        return pd.DataFrame(columns=COLUMNS + ["model"])
    return pd.concat(frames, ignore_index=True)
