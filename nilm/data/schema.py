"""Ortak veri biçimi. Her kaynak (UK-DALE, kendi evimiz) bu biçimi üretir."""
import pandas as pd

COLUMNS = ["timestamp", "house", "appliance", "aggregate_w", "appliance_w"]


def validate(df: pd.DataFrame) -> pd.DataFrame:
    missing = set(COLUMNS) - set(df.columns)
    if missing:
        raise ValueError(f"Eksik sütunlar: {missing}")
    df = df[COLUMNS].copy()
    df["timestamp"] = pd.to_datetime(df["timestamp"], utc=True)
    if (df[["aggregate_w", "appliance_w"]] < 0).any().any():
        raise ValueError("Negatif güç değeri var")
    return df.sort_values(["house", "appliance", "timestamp"]).reset_index(drop=True)
