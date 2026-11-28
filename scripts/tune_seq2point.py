"""Tek cihaz için seq2point deneyi: ayarları ver, doğrulama + test metriklerini deney günlüğüne yaz.

Her çalıştırma results/experiments.csv'ye bir satır ekler (tarih, cihaz, ayarlar, en iyi doğrulama
kaybı, ev 5 / ev 2 MAE-SAE-F1, süre). Hiperparametre seçimi ev 5 (val) ile yapılır, ev 2 yalnızca rapor.

Örnek:
  python -m scripts.tune_seq2point --appliance fridge --dropout 0.5 --hidden 256 --weight-decay 1e-4
"""
import argparse
import time
from datetime import datetime
from pathlib import Path

import pandas as pd

from nilm import config
from nilm.eval import metrics
from nilm.models.seq2point import Seq2Point

LOG = Path(__file__).resolve().parents[1] / "results" / "experiments.csv"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--appliance", default="fridge", choices=config.APPLIANCES)
    ap.add_argument("--data", default="data/processed")
    ap.add_argument("--window", type=int, default=599)
    ap.add_argument("--stride", type=int, default=20)
    ap.add_argument("--lr", type=float, default=3e-4)
    ap.add_argument("--dropout", type=float, default=0.2)
    ap.add_argument("--hidden", type=int, default=1024)
    ap.add_argument("--weight-decay", type=float, default=0.0)
    ap.add_argument("--center", action=argparse.BooleanOptionalAction, default=True,
                    help="pencere medyanını çıkar (kapatmak için --no-center)")
    ap.add_argument("--on-frac", type=float, default=0.35)
    ap.add_argument("--epochs", type=int, default=30)
    ap.add_argument("--patience", type=int, default=3)
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--note", default="")
    a = ap.parse_args()

    df = pd.read_hdf(Path(a.data) / f"{a.appliance.replace(' ', '_')}.h5", "data")
    pick = lambda hs: df[df["house"].isin(hs)]
    train, val, unseen = pick(config.TRAIN_HOUSES), pick(config.VAL_HOUSES), pick(config.UNSEEN_HOUSES)

    t0 = time.perf_counter()
    m = Seq2Point(window=a.window, stride=a.stride, lr=a.lr, dropout=a.dropout, hidden=a.hidden,
                  weight_decay=a.weight_decay, center=a.center, on_frac=a.on_frac, epochs=a.epochs,
                  patience=a.patience, seed=a.seed).fit(train, val if len(val) else None)
    row = dict(tarih=datetime.now().strftime("%Y-%m-%d %H:%M"), cihaz=a.appliance, window=a.window,
               stride=a.stride, lr=a.lr, dropout=a.dropout, hidden=a.hidden, weight_decay=a.weight_decay,
               center=a.center, on_frac=a.on_frac, seed=a.seed, epoch=len(m.history),
               en_iyi_val_kayip=min(h["val_loss"] for h in m.history),
               egitim_sn=round(time.perf_counter() - t0), notlar=a.note)
    thr = config.ON_THRESHOLD_W.get(a.appliance, config.DEFAULT_ON_THRESHOLD_W)
    for tag, d in [("val5", val), ("ev2", unseen)]:
        if d.empty:
            continue
        y, p = d["appliance_w"].to_numpy(), m.predict(d["aggregate_w"].to_numpy())
        row.update({f"{tag}_mae": metrics.mae(y, p), f"{tag}_sae": metrics.sae(y, p),
                    f"{tag}_f1": metrics.f1_on_off(y, p, thr)})
    LOG.parent.mkdir(parents=True, exist_ok=True)
    out =pd.concat([pd.read_csv(LOG), pd.DataFrame([row])]) if LOG.exists() else pd.DataFrame([row])
    out.to_csv(LOG, index=False)
    print(pd.Series(row).to_string())
    print(f"\n-> {LOG}")


if __name__ == "__main__":
    main()
