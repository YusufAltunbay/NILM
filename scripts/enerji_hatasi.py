"""Kayıtlı tahminlerden günlük ve haftalık enerji (kWh/TL) hatası tablosu (model eğitimi gerekmez).

Kullanıcının panelde gördüğü ölçek: her gün (hafta) için |tahmin - gerçek| enerji, dönemlerin ortalaması.
Çıktı: ekrana Markdown tablolar, results/enerji_hatasi.csv (git dışı) ve istenirse --md ile dosyaya.

  python -m scripts.enerji_hatasi
  python -m scripts.enerji_hatasi --models mean seq2point bert4nilm --md results/enerji_hatasi.md
"""
import argparse
from pathlib import Path

import pandas as pd

from nilm import config
from nilm.eval import energy, predictions

NAMES = {"fridge": "buzdolabı", "washing machine": "çamaşır mak.", "kettle": "su ısıtıcısı",
         "dish washer": "bulaşık mak.", "microwave": "mikrodalga"}
MODEL_ORDER = ["mean", "threshold", "seq2point", "bert4nilm"]
OUT = Path(__file__).resolve().parents[1] / "results" / "enerji_hatasi.csv"


def collect(models=None, root=None) -> pd.DataFrame:
    """Her (model, cihaz, ev) için günlük ve haftalık özet satırı."""
    rows = []
    for model, app, house in predictions.available(root):
        if models and model not in models:
            continue
        d = predictions.load(model, app, house, root)
        for label, days in (("gun", 1), ("hafta", 7)):
            s = energy.summarize(energy.period_energy(d, days=days))
            rows.append(dict(model=model, appliance=app, house=house, period=label, **s))
    return pd.DataFrame(rows)


def best_counts(tab: pd.DataFrame, col: str) -> dict:
    idx = tab.pivot_table(index=["appliance", "house"], columns="model", values=col)
    return idx.idxmin(axis=1).value_counts().to_dict()


def markdown(tab: pd.DataFrame, period: str, col: str = "mae_tl", fmt: str = ".2f") -> str:
    t = tab[tab.period == period].pivot_table(index=["appliance", "house"], columns="model", values=col)
    cols = [m for m in MODEL_ORDER if m in t.columns]
    t = t[cols]
    lines = ["| Cihaz | Ev | " + " | ".join(cols) + " |", "|---|---|" + "---|" * len(cols)]
    for app in config.APPLIANCES:
        for house in sorted({h for a, h in t.index if a == app}):
            r = t.loc[(app, house)]
            best = r.idxmin()
            cells = [f"**{format(r[c], fmt)}**" if c == best else format(r[c], fmt) for c in cols]
            lines.append(f"| {NAMES[app]} | {house} | " + " | ".join(cells) + " |")
    return "\n".join(lines)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--models", nargs="+", choices=MODEL_ORDER)
    ap.add_argument("--root", help="tahmin klasörü (varsayılan results/predictions)")
    ap.add_argument("--md", help="Markdown çıktı dosyası")
    a = ap.parse_args()
    tab = collect(a.models, Path(a.root) if a.root else None)
    if tab.empty:
        raise SystemExit("tahmin dosyası bulunamadı (önce run_eval --save-preds)")
    OUT.parent.mkdir(parents=True, exist_ok=True)
    tab.to_csv(OUT, index=False)
    parts = []
    for period, title in (("gun", "Günlük"), ("hafta", "Haftalık")):
        parts += [f"### {title} TL hatası (dönem başına |tahmin - gerçek| × {config.TL_PER_KWH} TL, ortalama; küçük = iyi)",
                  markdown(tab, period), "",
                  f"En iyi model sayısı ({title.lower()}): {best_counts(tab[tab.period == period], 'mae_tl')}", ""]
    text = "\n".join(parts)
    print(text)
    if a.md:
        Path(a.md).write_text(text + "\n", encoding="utf-8")
        print(f"-> {a.md}")
    print(f"-> {OUT}")


if __name__ == "__main__":
    main()
