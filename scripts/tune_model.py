"""Herhangi bir derin model için tek cihaz deneyi: ayarları ver, ev 5 ve ev 2 metriklerini günlüğe yaz.

Her çalıştırma results/experiments.csv'ye bir satır ekler. Ayarlar --param ile verilir (model
yapıcısının argümanları); verilmeyenler modelin varsayılanıdır.

Örnek:
  python -m scripts.tune_model --model bert4nilm --appliance fridge --param hidden=128 --param layers=3
  python -m scripts.tune_model --model seq2point --appliance kettle --seed 1
"""
import argparse
import ast
import json
import time
from datetime import datetime
from pathlib import Path

import pandas as pd

from nilm import config
from nilm.eval import metrics
from scripts.run_eval import MODELS

LOG = Path(__file__).resolve().parents[1] / "results" / "experiments.csv"
DEEP = [m for m in MODELS if m not in ("mean", "threshold")]


def parse_params(items) -> dict:
    out = {}
    for it in items or []:
        key, _, val = it.partition("=")
        if not key or not _:
            raise SystemExit(f"--param anahtar=değer biçiminde olmalı: {it!r}")
        try:
            out[key] = ast.literal_eval(val)
        except (ValueError, SyntaxError):
            out[key] = val  # düz metin
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", required=True, choices=DEEP)
    ap.add_argument("--appliance", default="fridge", choices=config.APPLIANCES)
    ap.add_argument("--data", default="data/processed")
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--param", action="append", metavar="ANAHTAR=DEĞER")
    ap.add_argument("--note", default="")
    a = ap.parse_args()
    params = parse_params(a.param)

    df = pd.read_hdf(Path(a.data) / f"{a.appliance.replace(' ', '_')}.h5", "data")
    pick = lambda hs: df[df["house"].isin(hs)]
    train, val, unseen = pick(config.TRAIN_HOUSES), pick(config.VAL_HOUSES), pick(config.UNSEEN_HOUSES)

    t0 = time.perf_counter()
    m = MODELS[a.model](seed=a.seed, **params).fit(train, val if len(val) else None)
    train_s = round(time.perf_counter() - t0)
    row = dict(tarih=datetime.now().strftime("%Y-%m-%d %H:%M"), model=a.model, cihaz=a.appliance,
               seed=a.seed, epoch=len(m.history), en_iyi_val_kayip=min(h["val_loss"] for h in m.history),
               egitim_sn=train_s, params=json.dumps(params, sort_keys=True), notlar=a.note)
    thr = config.ON_THRESHOLD_W.get(a.appliance, config.DEFAULT_ON_THRESHOLD_W)
    for tag, d in [("val5", val), ("ev2", unseen)]:
        if d.empty:
            continue
        y = d["appliance_w"].to_numpy()
        t1 = time.perf_counter()
        p = m.predict(d["aggregate_w"].to_numpy())
        row[f"{tag}_predict_sn"] = round(time.perf_counter() - t1, 1)
        row.update({f"{tag}_mae": metrics.mae(y, p), f"{tag}_sae": metrics.sae(y, p),
                    f"{tag}_f1": metrics.f1_on_off(y, p, thr),
                    f"{tag}_tl": metrics.tl_error(y, p, config.SAMPLE_PERIOD_S, config.TL_PER_KWH)})
    LOG.parent.mkdir(parents=True, exist_ok=True)
    out = pd.concat([pd.read_csv(LOG), pd.DataFrame([row])]) if LOG.exists() else pd.DataFrame([row])
    out.to_csv(LOG, index=False)
    print(pd.Series(row).to_string())
    print(f"\n-> {LOG}")


if __name__ == "__main__":
    main()
