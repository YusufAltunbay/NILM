"""Seed turu özeti: (model, cihaz) başına seed'ler arası ortalama ± std (ev 2 ve ev 5).

Kaynaklar (hepsi git'te takip edilen dosyalar):
  - results/results.csv       : resmi tur, seed 0
  - results/experiments.csv   : seed 1 ve 2 (notlar: 'seed-turu', 's2p-h256-seed*', 'center-lr3e-4-seed*')

Kullanım:
  python -m scripts.seed_ozeti
  python -m scripts.seed_ozeti --md results/seed_ozeti.md
"""
import argparse
from pathlib import Path

import numpy as np
import pandas as pd

from nilm import config

ROOT = Path(__file__).resolve().parents[1]
METRICS = ["mae", "f1", "tl"]
NAMES = {"fridge": "buzdolabı", "washing machine": "çamaşır mak.", "kettle": "su ısıtıcısı",
         "dish washer": "bulaşık mak.", "microwave": "mikrodalga"}


def _official(res: pd.DataFrame) -> pd.DataFrame:
    """results.csv (seed 0) -> deney günlüğüyle aynı sütunlu satırlar."""
    res = res[res["model"].isin(["seq2point", "bert4nilm"])].copy()
    res["ev"] = res["dataset"].str.extract(r"house(\d)")[0]
    rows = []
    for (m, a), g in res.groupby(["model", "appliance"]):
        r = dict(model=m, appliance=a, seed=0, kaynak="resmi")
        for _, x in g.iterrows():
            tag = "ev2" if x["ev"] == "2" else "val5"
            r[f"{tag}_mae"], r[f"{tag}_f1"], r[f"{tag}_tl"] = x["mae"], x["f1"], x["tl_error"]
        rows.append(r)
    return pd.DataFrame(rows)


def _from_experiments(exp: pd.DataFrame) -> pd.DataFrame:
    """seed >= 1 olan koşular. 'model' boş olan eski satırlar seq2point'tir."""
    exp = exp.copy()
    exp["model"] = exp["model"].fillna("seq2point")
    note = exp["notlar"].fillna("")
    use = (note.str.startswith(("seed-turu", "s2p-h256-seed", "center-lr3e-4-seed"))) & (exp["seed"] >= 1)
    exp = exp[use].rename(columns={"cihaz": "appliance"})
    exp["kaynak"] = np.where(exp["notlar"].fillna("").str.startswith("center-lr3e-4"), "eski örnekleme", "deney")
    return exp[["model", "appliance", "seed", "kaynak", *[f"{t}_{m}" for t in ("ev2", "val5") for m in METRICS]]]


def collect(res_path=None, exp_path=None) -> pd.DataFrame:
    res = pd.read_csv(res_path or ROOT / "results" / "results.csv")
    exp = pd.read_csv(exp_path or ROOT / "results" / "experiments.csv")
    runs = pd.concat([_official(res), _from_experiments(exp)], ignore_index=True)
    return runs.drop_duplicates(["model", "appliance", "seed"], keep="first").sort_values(
        ["model", "appliance", "seed"]).reset_index(drop=True)


def summarize_runs(runs: pd.DataFrame) -> pd.DataFrame:
    """(model, cihaz) başına: seed sayısı ve her ölçüt için ortalama ve std (ddof=1; tek seed'de std NaN)."""
    rows = []
    for (m, a), g in runs.groupby(["model", "appliance"]):
        r = dict(model=m, appliance=a, n_seed=g["seed"].nunique(),
                 not_=", ".join(sorted(set(g["kaynak"]) - {"resmi", "deney"})))
        for tag in ("ev2", "val5"):
            for met in METRICS:
                v = g[f"{tag}_{met}"].dropna().to_numpy(dtype=float)
                r[f"{tag}_{met}_ort"] = v.mean() if len(v) else np.nan
                r[f"{tag}_{met}_std"] = v.std(ddof=1) if len(v) > 1 else np.nan
        rows.append(r)
    return pd.DataFrame(rows)


def _fmt(mean, std, digits):
    if pd.isna(mean):
        return "-"
    return f"{mean:.{digits}f}" + ("" if pd.isna(std) else f" ± {std:.{digits}f}")


def markdown(summary: pd.DataFrame) -> str:
    head = ["Cihaz", "Model", "Seed", "Ev 2 MAE (W)", "Ev 2 F1", "Ev 2 TL", "Ev 5 MAE (W)", "Ev 5 F1", "Ev 5 TL"]
    lines = ["| " + " | ".join(head) + " |", "|" + "---|" * len(head)]
    for a in config.APPLIANCES:
        for m in ("seq2point", "bert4nilm"):
            s = summary[(summary.appliance == a) & (summary.model == m)]
            if s.empty:
                continue
            r = s.iloc[0]
            cells = [NAMES[a], m, f"{int(r.n_seed)}" + (f" ({r.not_})" if r.not_ else "")]
            for tag in ("ev2", "val5"):
                cells += [_fmt(r[f"{tag}_mae_ort"], r[f"{tag}_mae_std"], 1),
                          _fmt(r[f"{tag}_f1_ort"], r[f"{tag}_f1_std"], 2),
                          _fmt(r[f"{tag}_tl_ort"], r[f"{tag}_tl_std"], 0)]
            lines.append("| " + " | ".join(cells) + " |")
    return "\n".join(lines)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--md", help="Markdown çıktı dosyası")
    a = ap.parse_args()
    runs = collect()
    summary = summarize_runs(runs)
    text = markdown(summary)
    print(text)
    print(f"\n{len(runs)} koşu, {len(summary)} (model, cihaz) grubu")
    if a.md:
        Path(a.md).write_text(text + "\n", encoding="utf-8")
        print(f"-> {a.md}")


if __name__ == "__main__":
    main()
