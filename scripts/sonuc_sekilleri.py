"""Rapor için model sonuç şekilleri -> results/figures/sonuc/*.png

Girdi: results/results.csv (run_eval çıktısı), results/experiments.csv (seq2point deney günlüğü).
Kullanım: python -m scripts.sonuc_sekilleri
"""
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from nilm import config

ROOT = Path(__file__).resolve().parents[1]
RESULTS = ROOT / "results" / "results.csv"
EXPERIMENTS = ROOT / "results" / "experiments.csv"
OUT = ROOT / "results" / "figures" / "sonuc"

SURFACE, INK, INK2, GRID = "#fcfcfb", "#1a1a19", "#5b5a55", "#e1e0d9"
BLUE, ORANGE, AQUA = "#2a78d6", "#eb6834", "#1baf7a"
MODELS = ["mean", "threshold", "seq2point"]  # sabit sıra = sabit renk
MODEL_COLOR = dict(zip(MODELS, [BLUE, ORANGE, AQUA]))
MODEL_NAME = {"mean": "Ortalama", "threshold": "Eşik", "seq2point": "seq2point"}
NAMES = {"fridge": "Buzdolabı", "washing machine": "Çamaşır m.", "kettle": "Su ısıtıcısı",
         "dish washer": "Bulaşık m.", "microwave": "Mikrodalga"}
METRICS = [("f1", "F1 (yüksek iyi)"), ("mae", "MAE, W (düşük iyi)"), ("sae", "SAE (düşük iyi)")]

plt.rcParams.update({
    "figure.facecolor": SURFACE, "axes.facecolor": SURFACE, "savefig.facecolor": SURFACE,
    "text.color": INK, "axes.labelcolor": INK2, "xtick.color": INK2, "ytick.color": INK2,
    "axes.edgecolor": GRID, "axes.grid": True, "grid.color": GRID, "grid.linewidth": 0.6,
    "axes.spines.top": False, "axes.spines.right": False, "axes.axisbelow": True,
    "font.size": 10, "axes.titlesize": 11, "axes.titleweight": "bold", "axes.titlelocation": "left",
    "legend.frameon": False,
})


def load(path=RESULTS) -> pd.DataFrame:
    df = pd.read_csv(path)
    m = df["dataset"].str.extract(r"house(\d+)\((\w+)\)$")
    df["house"], df["kind"] = m[0].astype(int), m[1]
    return df


def save(fig, name):
    OUT.mkdir(parents=True, exist_ok=True)
    fig.savefig(OUT / name, dpi=170, bbox_inches="tight")
    plt.close(fig)
    print("yazıldı:", OUT / name)


def grouped_bars(df, kind, title, name):
    """Cihaz x model gruplu çubuklar; metrik başına bir panel."""
    d = df[df["kind"] == kind]
    apps = [a for a in config.APPLIANCES if a in set(d["appliance"])]
    models = [m for m in MODELS if m in set(d["model"])]
    fig, axes = plt.subplots(1, len(METRICS), figsize=(15, 4.3))
    w = 0.8 / len(models)
    for ax, (metric, label) in zip(axes, METRICS):
        for j, m in enumerate(models):
            v = [d[(d["model"] == m) & (d["appliance"] == a)][metric].mean() for a in apps]
            x = np.arange(len(apps)) + (j - (len(models) - 1) / 2) * w
            ax.bar(x, v, w * 0.92, color=MODEL_COLOR[m], label=MODEL_NAME[m])
        ax.set_xticks(range(len(apps)), [NAMES[a] for a in apps], rotation=20, ha="right")
        ax.set_title(label)
    axes[0].legend(ncol=len(models), loc="upper left", bbox_to_anchor=(0, 1.02 + 0.0))
    axes[0].set_ylim(0, 1.12)
    fig.suptitle(title, x=0.01, ha="left", fontweight="bold")
    fig.tight_layout(rect=(0, 0, 1, 0.94))
    save(fig, name)


def generalization(df, name="03_genelleme.png"):
    """Her model için doğrulama (ev 5) ve görülmeyen ev (ev 2) F1 farkı."""
    apps = [a for a in config.APPLIANCES if a in set(df["appliance"])]
    fig, axes = plt.subplots(1, 2, figsize=(11, 4.2), sharey=True)
    for ax, m in zip(axes, ["threshold", "seq2point"]):
        for i, a in enumerate(apps):
            s = df[(df["model"] == m) & (df["appliance"] == a)].set_index("kind")["f1"]
            if {"val", "unseen"} <= set(s.index):
                ax.plot([i, i], [s["val"], s["unseen"]], color=GRID, lw=2.5, zorder=1)
                ax.scatter(i, s["val"], s=55, color=ORANGE, zorder=2, label="Ev 5 (doğrulama)" if i == 0 else None)
                ax.scatter(i, s["unseen"], s=55, color=AQUA, zorder=2, label="Ev 2 (görülmeyen)" if i == 0 else None)
        ax.set_xticks(range(len(apps)), [NAMES[a] for a in apps], rotation=20, ha="right")
        ax.set_title(f"{MODEL_NAME[m]}: F1")
        ax.set_ylim(0, 1.05)
    axes[0].legend(loc="upper right")
    fig.tight_layout()
    save(fig, name)


def seed_spread(name="04_seed_oynakligi.png"):
    """Buzdolabı: nihai ayarın seed çalıştırmaları (ev 2). Aynı seed iki kez koşulduysa ikisi de görünür."""
    if not EXPERIMENTS.exists():
        return
    e = pd.read_csv(EXPERIMENTS)
    e = e[(e["cihaz"] == "fridge") & (e["center"] == True) & (e["lr"] == 3e-4)  # noqa: E712
          & (e["on_frac"] == 0.35) & (e["dropout"] == 0.2)].reset_index(drop=True)
    if e.empty:
        return
    seen, labels = {}, []
    for s_ in e["seed"]:
        seen[s_] = seen.get(s_, 0) + 1
        labels.append(f"seed {int(s_)}" + (" (tekrar)" if seen[s_] > 1 else ""))
    fig, axes = plt.subplots(1, 3, figsize=(12, 4))
    for ax, (col, label) in zip(axes, [("ev2_f1", "F1"), ("ev2_mae", "MAE (W)"), ("ev2_sae", "SAE")]):
        ax.scatter(range(len(e)), e[col], s=60, color=AQUA, zorder=2)
        for i, r in e.iterrows():
            ax.annotate(labels[i], (i, r[col]), textcoords="offset points",
                        xytext=(0, 8), ha="center", fontsize=8, color=INK2)
        lo, hi = e[col].min(), e[col].max()
        pad = max(hi - lo, 1e-9) * 0.35
        ax.set_ylim(lo - pad, hi + pad)
        ax.set_xticks([])
        ax.set_xlim(-0.6, len(e) - 0.4)
        ax.set_title(label)
    fig.suptitle("Buzdolabı, seq2point, ev 2: aynı ayarla ayrı çalıştırmalar (eksenler sıfırdan başlamaz)",
                 x=0.01, ha="left", fontweight="bold")
    fig.tight_layout(rect=(0, 0, 1, 0.93))
    save(fig, name)


def main():
    if not RESULTS.exists():
        raise SystemExit(f"{RESULTS} yok. Önce: python -m scripts.run_eval --data data/processed")
    df = load()
    grouped_bars(df, "unseen", "Görülmeyen ev (ev 2): modellerin karşılaştırması", "01_ev2_karsilastirma.png")
    grouped_bars(df, "val", "Doğrulama evi (ev 5): modellerin karşılaştırması", "02_ev5_karsilastirma.png")
    generalization(df)
    seed_spread()


if __name__ == "__main__":
    main()
