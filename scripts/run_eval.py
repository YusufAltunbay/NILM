"""Toplu değerlendirme: her model x cihaz x test evi için bir satır results/results.csv'ye yazar.

Kullanım:
  python -m scripts.run_eval --synthetic            # sahte veriyle deneme
  python -m scripts.run_eval --data data/processed/ukdale.parquet
Modeller MODELS sözlüğüne eklenir (Ersin'in seq2point / BERT4NILM sınıfları buraya girer).
"""
import argparse
from pathlib import Path

import pandas as pd

from nilm import config
from nilm.data.schema import validate
from nilm.eval.evaluate import evaluate
from nilm.eval import results, predictions
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
    df = pd.read_parquet(path) if path.suffix == ".parquet" else pd.read_csv(path)
    return validate(df), path.stem


def run(df, source, model_names, log=True, save_preds=True):
    rows = []
    preds = {name: [] for name in model_names}
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
                row, p = evaluate(model, test, f"{source}:house{h}({kind})", appliance,
                                  log=log, return_pred=True)
                rows.append(row)
                preds[name].append(predictions.to_frame(test, p))
    if save_preds:
        for name, frames in preds.items():
            if frames:
                predictions.save(name, pd.concat(frames, ignore_index=True))
    return pd.DataFrame(rows)


def main():
    ap = argparse.ArgumentParser()
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--data", help="şemaya uygun .parquet/.csv")
    g.add_argument("--synthetic", action="store_true")
    ap.add_argument("--models", nargs="+", default=list(MODELS), choices=list(MODELS))
    ap.add_argument("--fresh", action="store_true", help="results.csv'yi sıfırdan yaz")
    args = ap.parse_args()
    if args.fresh:
        if results.RESULTS.exists():
            results.RESULTS.unlink()
        for f in predictions.PRED_DIR.glob("*.csv.gz"):
            f.unlink()
    df, source = load(args)
    out = run(df, source, args.models)
    print(out.round(3).to_string(index=False))
    print(f"\n{len(out)} satır -> {results.RESULTS}\nTahminler -> {predictions.PRED_DIR}")


if __name__ == "__main__":
    main()
