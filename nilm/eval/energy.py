"""Dönemlik (günlük / haftalık) cihaz enerjisi ve TL: kullanıcının panelde gördüğü ölçek.

Modeller anlık güç (W) tahmin eder; kullanıcı ise cihaz başına günlük/haftalık kWh ve TL görür. Bu modül
tahmin tablosunu dönemlere toplar. Model eğitiminden bağımsızdır; hem sonuç tablosu hem panel aynı
fonksiyonu kullanabilsin diye saf (Streamlit'e ve dosyalara bağımlı değil) tutuldu.

Girdi: timestamp, appliance_w (gerçek) ve tahmin sütunu ('predicted_w' ya da 'pred_w') içeren tablo,
tek cihaz ve tek ev. Eksik (kayıt boşluğu olan) dönemler varsayılan olarak atılır, çünkü yarım günün
enerjisi gerçek günlük tüketimi temsil etmez; gerçek ve tahmin aynı satırlar üzerinden toplandığı için
karşılaştırma yine de adildir.
"""
import numpy as np
import pandas as pd

from nilm import config

PRED_COLUMNS = ("predicted_w", "pred_w")
OUT_COLUMNS = ["period_start", "n", "coverage", "true_kwh", "pred_kwh", "err_kwh", "abs_err_kwh",
               "true_tl", "pred_tl", "abs_err_tl"]


def _pred_col(df: pd.DataFrame) -> str:
    for c in PRED_COLUMNS:
        if c in df.columns:
            return c
    raise KeyError(f"tahmin sütunu yok (beklenen: {PRED_COLUMNS})")


def period_energy(df: pd.DataFrame, days: int = 1, price: float = config.TL_PER_KWH,
                  period_s: float = config.SAMPLE_PERIOD_S, min_coverage: float = 0.9) -> pd.DataFrame:
    """Her `days` günlük dönem için gerçek ve tahmin enerji (kWh) ile TL.

    Dönemler verinin ilk gününden itibaren ardışık `days` günlük bloklardır (haftalık için days=7).
    coverage = dönemdeki örnek sayısı / beklenen örnek sayısı; min_coverage altındaki dönemler atılır
    (0 verilirse hepsi tutulur). Hata = tahmin - gerçek (işaretli), abs_* mutlak.
    """
    if days < 1:
        raise ValueError("days >= 1 olmalı")
    if not 0 <= min_coverage <= 1:
        raise ValueError("min_coverage [0, 1] aralığında olmalı")
    pc = _pred_col(df)
    if df.empty:
        return pd.DataFrame(columns=OUT_COLUMNS)
    ts = pd.to_datetime(df["timestamp"])
    day = ts.dt.tz_localize(None).dt.normalize() if ts.dt.tz is not None else ts.dt.normalize()
    block = ((day - day.min()).dt.days // days).to_numpy()
    g = pd.DataFrame({"block": block, "y": df["appliance_w"].to_numpy(dtype="float64"),
                      "p": df[pc].to_numpy(dtype="float64")}).groupby("block").agg(
        n=("y", "size"), y=("y", "sum"), p=("p", "sum"))
    expected = days * 86400.0 / period_s
    k = period_s / 3.6e6  # W x adım -> kWh
    out = pd.DataFrame({
        "period_start": (day.min() + pd.to_timedelta(g.index * days, unit="D")).to_numpy(),
        "n": g["n"].to_numpy(), "coverage": (g["n"] / expected).to_numpy(),
        "true_kwh": (g["y"] * k).to_numpy(), "pred_kwh": (g["p"] * k).to_numpy()})
    out["err_kwh"] = out["pred_kwh"] - out["true_kwh"]
    out["abs_err_kwh"] = out["err_kwh"].abs()
    out["true_tl"], out["pred_tl"] = out["true_kwh"] * price, out["pred_kwh"] * price
    out["abs_err_tl"] = out["abs_err_kwh"] * price
    out = out[out["coverage"] >= min_coverage].reset_index(drop=True)
    return out[OUT_COLUMNS]


def daily_energy(df: pd.DataFrame, **kw) -> pd.DataFrame:
    return period_energy(df, days=1, **kw)


def weekly_energy(df: pd.DataFrame, **kw) -> pd.DataFrame:
    return period_energy(df, days=7, **kw)


def summarize(per_period: pd.DataFrame) -> dict:
    """Dönem tablosundan özet: dönem başına ortalama mutlak hata (kWh ve TL), gerçek ortalama, göreli hata.

    rel_err = ortalama mutlak hata / ortalama gerçek enerji (gerçek enerji 0 ise NaN).
    Boş tabloda n_periods=0 ve diğerleri NaN döner.
    """
    if per_period.empty:
        return dict(n_periods=0, mae_kwh=np.nan, mae_tl=np.nan, true_kwh_mean=np.nan, rel_err=np.nan)
    true_mean = float(per_period["true_kwh"].mean())
    mae_kwh = float(per_period["abs_err_kwh"].mean())
    return dict(n_periods=len(per_period), mae_kwh=mae_kwh, mae_tl=float(per_period["abs_err_tl"].mean()),
                true_kwh_mean=true_mean, rel_err=mae_kwh / true_mean if true_mean > 0 else float("nan"))
