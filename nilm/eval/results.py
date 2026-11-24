"""Ortak sonuç tablosu: her deney tek satır ekler."""
import csv
from pathlib import Path

FIELDS = ["model", "dataset", "appliance", "mae", "sae", "f1", "tl_error", "predict_ms"]
RESULTS = Path(__file__).resolve().parents[2] / "results" / "results.csv"


def append(row: dict, path: Path = RESULTS):
    path.parent.mkdir(parents=True, exist_ok=True)
    new = not path.exists()
    with path.open("a", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=FIELDS)
        if new:
            w.writeheader()
        w.writerow({k: row[k] for k in FIELDS})
