"""Toplu değerlendirme: her model x cihaz x test evi için bir satır results/results.csv'ye yazar.

Kullanım:
  python -m scripts.run_eval --synthetic            # sahte veriyle deneme
  python -m scripts.run_eval --data data/processed/fridge.h5
  python -m scripts.run_eval --data data/processed --save-preds   # tüm cihazlar, tahminleri de kaydet
Modeller MODELS sözlüğüne eklenir (Ersin'in seq2point / BERT4NILM sınıfları buraya girer).
"""
import argparse
import inspect
from pathlib import Path

import pandas as pd

from nilm import config
from nilm.data.schema import validate
from nilm.eval.evaluate import evaluate
from nilm.eval import results
from nilm.models import params
from nilm.models.base import MeanModel
from nilm.models.baseline import ThresholdModel
from nilm.models.bert4nilm import Bert4Nilm
from nilm.models.seq2point import Seq2Point

# ad -> model üreten fonksiyon.
MODELS = {
    "mean": MeanModel,
    "threshold": ThresholdModel,
    "seq2point": Seq2Point,
    "bert4nilm": Bert4Nilm,
}


def load(args) -> tuple[pd.DataFrame, str]:
    if args.synthetic:
        from scripts import synthetic
        return synthetic.make(), "synthetic"
    path = Path(args.data)
    readers = {".parquet": pd.read_parquet, ".h5": lambda p: pd.read_hdf(p, "data")}
    if path.is_dir():  # data/processed: cihaz başına bir .h5 (örnek CSV'ler atlanır)
        df = pd.concat([readers[".h5"](f) for f in sorted(path.glob("*.h5"))], ignore_index=True)
        return validate(df), path.name
    df = readers.get(path.suffix, pd.read_csv)(path)
    return validate(df), path.stem


def replace_rows(models, appliances, path=None):
    """results.csv'den (model, cihaz) satırlarını siler; yeniden çalıştırınca çift satır olmasın.

    Silmeden önce yedek alır (path + '.bak'), geri yüklemek için döndürür; yedek yoksa None.
    """
    import shutil
    path = Path(path or results.RESULTS)
    if not path.exists():
        return None
    bak = path.with_suffix(path.suffix + ".bak")
    shutil.copy2(path, bak)
    df = pd.read_csv(path)
    keep = ~(df["model"].isin(models) & df["appliance"].isin(appliances))
    print(f"[replace] {int((~keep).sum())} satır silindi: modeller={list(models)}, cihazlar={list(appliances)}")
    df[keep].to_csv(path, index=False)
    return bak


def run(df, source, model_names, log=True, save_preds=False, appliances=None):
    rows = []
    # Eğitimde olmayan evler değerlendirilir: doğrulama evi ("val") ve hiç görülmeyen ev ("unseen").
    test_houses = [h for h in sorted(df["house"].unique())
                   if h not in config.TRAIN_HOUSES or h in config.UNSEEN_HOUSES]
    for appliance in (appliances or config.APPLIANCES):
        sub = df[df["appliance"] == appliance]
        train = sub[sub["house"].isin(config.TRAIN_HOUSES)]
        if train.empty:
            print(f"[uyarı] {appliance}: eğitim verisi yok, atlandı")
            continue
        for name in model_names:
            kw = params.params(name, appliance)
            if kw:
                print(f"[{appliance}] {name} cihaz bazlı ayar: {kw}")
            model = MODELS[name](**kw)
            if "val" in inspect.signature(model.fit).parameters:  # erken durdurma için ev 5
                val = sub[sub["house"].isin(config.VAL_HOUSES)]
                model.fit(train, val if len(val) else None)
            else:
                model.fit(train)
            if hasattr(model, "save"):  # eğitilmiş ağırlıklar (models_ckpt/*.pt, git dışı)
                print(f"[{appliance}] ağırlıklar -> {model.save()}")
            for h in test_houses:
                test = sub[sub["house"] == h]
                if test.empty:
                    continue
                kind = "unseen" if h in config.UNSEEN_HOUSES else "val"
                rows.append(evaluate(model, test, f"{source}:house{h}({kind})", appliance,
                                     log=log, save_preds=save_preds))
    return pd.DataFrame(rows)


def main():
    ap = argparse.ArgumentParser()
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--data", help="şemaya uygun .parquet/.csv/.h5 dosyası ya da data/processed klasörü")
    g.add_argument("--synthetic", action="store_true")
    ap.add_argument("--models", nargs="+", default=list(MODELS), choices=list(MODELS))
    ap.add_argument("--save-preds", action="store_true",
                    help="tahminleri results/predictions/ altına kaydet (panel için)")
    ap.add_argument("--appliances", nargs="+", choices=config.APPLIANCES, metavar="CİHAZ",
                    help="yalnızca bu cihazlar (varsayılan: hepsi)")
    ap.add_argument("--replace", action="store_true",
                    help="seçilen model ve cihazların eski satırlarını silip yenilerini yaz (çift satır olmasın)")
    ap.add_argument("--fresh", action="store_true", help="results.csv'yi sıfırdan yaz")
    args = ap.parse_args()
    if args.fresh and results.RESULTS.exists():
        results.RESULTS.unlink()
    df, source = load(args)
    bak = None
    if args.replace and not args.fresh:
        bak = replace_rows(args.models, args.appliances or config.APPLIANCES)
    try:
        out = run(df, source, args.models, save_preds=args.save_preds, appliances=args.appliances)
    except BaseException:
        if bak is not None and bak.exists():  # yarım kalan çalıştırma: eski tabloyu geri yükle
            import shutil
            shutil.copy2(bak, results.RESULTS)
            print("[replace] hata: results.csv yedekten geri yüklendi")
        raise
    if bak is not None and bak.exists():
        bak.unlink()
    print(out.round(3).to_string(index=False))
    print(f"\n{len(out)} satır -> {results.RESULTS}")


if __name__ == "__main__":
    main()
