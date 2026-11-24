"""Toplu değerlendirme: her model x cihaz x test evi için bir satır results/results.csv'ye yazar.

Kullanım:
  python -m scripts.run_eval --synthetic            # sahte veriyle deneme
  python -m scripts.run_eval --data data/processed/fridge.h5
Modeller MODELS sözlüğüne eklenir (Ersin'in seq2point / BERT4NILM sınıfları buraya girer).
"""
import argparse
from pathlib import Path

import pandas as pd

from nilm import config
from nilm.data.schema import validate
from nilm.eval.evaluate import evaluate
from nilm.eval import results
from nilm.models.base import MeanModel

# ad -> model üreten fonksiyon. Ersin'in modelleri hazır olunca buraya eklenecek.
MODELS = {
    "mean": MeanModel,
}


def load(args) -> tuple[pd.DataFrame, str]:
    if args.synthetic:
        from scripts import synthetic
        return synthetic.make(), "synthetic"
    path = Path(args.data)
    readers = {".parquet": pd.read_parquet, ".h5": lambda p: pd.read_hdf(p, "data")}
    df = readers.get(path.suffix, pd.read_csv)(path)
    return validate(df), path.stem


def run(df, source, model_names, log=True):
    rows = []
    # VAL_HOUSES şu an TRAIN_HOUSES'un içinde; eğitimde olmayan evler test edilir.
    test_houses = [h for h in sorted(df["house"].unique())
                   if h not in config.TRAIN_HOUSES or h in config.UNSEEN_HOUSES]
    for appliance in config.APPLIANCES:
        sub = df[df["appliance"] == appliance]
        train = sub[sub["house"].isin(config.TRAIN_HOUSES)]
        if train.empty:
            print(f"[uyarı] {appliance}: eğitim verisi yok, atlandı")
            continue
        for name in model_names:
            model = MODELS[name]().fit(train)
            for h in test_houses:
                test = sub[sub["house"] == h]
                if test.empty:
                    continue
                kind = "unseen" if h in config.UNSEEN_HOUSES else "test"
                rows.append(evaluate(model, test, f"{source}:house{h}({kind})", appliance, log=log))
    return pd.DataFrame(rows)


def main():
    ap = argparse.ArgumentParser()
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--data", help="şemaya uygun .parquet/.csv")
    g.add_argument("--synthetic", action="store_true")
    ap.add_argument("--models", nargs="+", default=list(MODELS), choices=list(MODELS))
    ap.add_argument("--fresh", action="store_true", help="results.csv'yi sıfırdan yaz")
    args = ap.parse_args()
    if args.fresh and results.RESULTS.exists():
        results.RESULTS.unlink()
    df, source = load(args)
    out = run(df, source, args.models)
    print(out.round(3).to_string(index=False))
    print(f"\n{len(out)} satır -> {results.RESULTS}")


if __name__ == "__main__":
    main()
