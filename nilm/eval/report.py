"""results/results.csv'den özet tablo ve karşılaştırma grafikleri üretir.

Kullanım: python -m nilm.eval.report
Çıktı: results/summary.csv ve results/figures/*.png
"""
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd

from nilm.eval.results import RESULTS

METRICS = {
    "mae": "MAE (W) – düşük iyi",
    "sae": "SAE – düşük iyi",
    "f1": "F1 – yüksek iyi",
    "tl_error": "Fatura hatası (TL) – düşük iyi",
}


def load(path: Path = RESULTS) -> pd.DataFrame:
    df = pd.read_csv(path)
    # dataset: "<kaynak>:house<N>(<tür>)" -> tür sütunu (test / unseen)
    df["kind"] = df["dataset"].str.extract(r"\((\w+)\)$")[0].fillna("test")
    return df


def summary(df: pd.DataFrame) -> pd.DataFrame:
    """Model x cihaz x tür bazında metriklerin ortalaması."""
    cols = list(METRICS) + ["predict_ms"]
    return df.groupby(["model", "appliance", "kind"], as_index=False)[cols].mean()


def plot_metric(df: pd.DataFrame, metric: str, out: Path):
    pv = df.pivot_table(index="appliance", columns="model", values=metric, aggfunc="mean")
    ax = pv.plot(kind="bar", figsize=(8, 4.5), width=0.8)
    ax.set_title(METRICS[metric])
    ax.set_xlabel("")
    ax.set_ylabel(metric)
    plt.xticks(rotation=20, ha="right")
    plt.legend(title="model")
    plt.tight_layout()
    plt.savefig(out, dpi=150)
    plt.close()


def main(path: Path = RESULTS):
    if not Path(path).exists():
        raise SystemExit(f"{path} yok. Önce: python -m scripts.run_eval ...")
    df = load(path)
    out_dir = Path(path).parent
    fig_dir = out_dir / "figures"
    fig_dir.mkdir(exist_ok=True)
    s = summary(df)
    s.to_csv(out_dir / "summary.csv", index=False)
    for m in METRICS:
        plot_metric(df, m, fig_dir / f"{m}.png")
    print(s.round(3).to_string(index=False))
    print(f"\nGrafikler: {fig_dir}")


if __name__ == "__main__":
    main()
