"""Seçilen cihazlar için UK-DALE'yi temizleyip data/processed/ altına yazar.

Çıktı: data/processed/{cihaz}.h5 (ortak biçim, tüm evler) ve
       data/processed/sample_{cihaz}.csv (Ersin/Kamil için küçük örnek, ev 1'den 1 gün).
Kullanım: python -m scripts.prepare_ukdale [--start 2014-01-01 --end 2014-12-31]
"""
import argparse
from pathlib import Path

import pandas as pd

from nilm import config
from nilm.data import prep, ukdale

OUT = Path(__file__).resolve().parents[1] / "data" / "processed"

ap = argparse.ArgumentParser()
ap.add_argument("--start"); ap.add_argument("--end")
args = ap.parse_args()

OUT.mkdir(parents=True, exist_ok=True)
houses = sorted(set(config.TRAIN_HOUSES + config.VAL_HOUSES + config.UNSEEN_HOUSES))
meters = ukdale.appliance_meters()
for app in config.APPLIANCES:
    parts = []
    for h in houses:
        if app not in meters.get(h, {}):
            print(f"{app}: ev {h} içinde yok, atlandı")
            continue
        df = prep.clean(ukdale.load(h, app, start=args.start, end=args.end))
        print(f"{app}: ev {h} -> {len(df):,} satır")
        parts.append(df)
    if not parts:
        continue
    df = pd.concat(parts, ignore_index=True)
    name = app.replace(" ", "_")
    df.to_hdf(OUT / f"{name}.h5", key="data", mode="w", complevel=5)
    first = df[df.house == df.house.min()]
    first[first.timestamp < first.timestamp.min() + pd.Timedelta("1D")].to_csv(
        OUT / f"sample_{name}.csv", index=False)
