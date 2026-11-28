"""İki sayfada ortak kullanılan arayüz blokları."""
import numpy as np
import pandas as pd
import streamlit as st

from nilm import config
from nilm.eval import metrics
from panel import charts, theme

_VIEWS = {
    "Şerit": "Üst çubuk gerçek faturayı, alt çubuk tahmini gösterir. Dilimler aynı ölçekte olduğu için farklar doğrudan görülür.",
    "Dikey şerit": "Sol sütun gerçek, sağ sütun tahmin edilen fatura. Dilimlerin yüksekliği her cihazın tutarıdır (TL).",
    "Halka": "Her halka, faturanın cihazlar arasındaki payını gösterir. Ortadaki sayı toplam tutardır (TL).",
    "Çubuk": "Her cihaz için gerçek (dolu çubuk) ve tahmin edilen (açık dolgulu çubuk) fatura yan yana.",
}


def bill_view(bill, key: str, default: str = "Şerit"):
    """Fatura için Şerit / Dikey şerit / Halka / Çubuk seçicisi ve seçilen grafik."""
    view = st.segmented_control("Görünüm", list(_VIEWS), default=default, key=key, label_visibility="collapsed") or default
    theme.legend(list(bill.index))
    chart = {"Şerit": charts.ribbon, "Dikey şerit": charts.stacked, "Halka": charts.donut, "Çubuk": charts.bars}[view]
    st.altair_chart(chart(bill), width="stretch")


SMOOTH = {"Yok": 1, "Hafif": 5, "Orta": 15, "Güçlü": 60}


def on_bands(ts, y, thr):
    """Cihazın AÇIK olduğu dönemler (çok fazlaysa çizilmez)."""
    on = y > thr
    edges = np.flatnonzero(np.diff(np.r_[False, on, False].astype(int)))
    if 0 < len(edges) // 2 <= 400:
        t = np.asarray(ts)
        return pd.DataFrame({"start": t[edges[0::2]], "end": t[np.minimum(edges[1::2], len(t)) - 1]})
    return None


def smooth_view(g: pd.DataFrame, models, smooth: str, max_points: int = 2500):
    """Grafik için yumuşatılmış ve seyreltilmiş kopya (metrikler ham veriden hesaplanır)."""
    cols = ["Gerçek", "Toplam"] + [f"m{i}" for i in range(len(models))]
    view = g[["timestamp"] + cols].copy()
    if SMOOTH[smooth] > 1:
        view[cols] = view[cols].rolling(SMOOTH[smooth], min_periods=1, center=True).mean()
    step = max(1, len(view) // max_points)
    return view.iloc[::step], step


def window_stats(g: pd.DataFrame, dev: str, models, price: float):
    """Pencere için gerçek ve her model için kWh, TL, MAE, F1."""
    from panel import data
    dt = data.dt()
    thr = config.ON_THRESHOLD_W.get(dev, config.DEFAULT_ON_THRESHOLD_W)
    y = g["Gerçek"].to_numpy()
    out = {"real": dict(kwh=metrics.energy_kwh(y, dt), tl=metrics.bill_tl(y, dt, price)), "models": {}}
    for i, m in enumerate(models):
        p = g[f"m{i}"].to_numpy()
        ok = ~np.isnan(p)
        if not ok.any():
            continue
        out["models"][m] = dict(kwh=metrics.energy_kwh(p[ok], dt), tl=metrics.bill_tl(p[ok], dt, price),
                                mae=metrics.mae(y[ok], p[ok]), f1=metrics.f1_on_off(y[ok], p[ok], thr))
    return out


def window_cards(g: pd.DataFrame, dev: str, models, price: float):
    """Gerçek + her model için bir kart; her ölçütte en iyi olan işaretlenir."""
    st_ = window_stats(g, dev, models, price)
    real, ms = st_["real"], st_["models"]
    multi = len(ms) > 1
    best_mae = min((v["mae"] for v in ms.values()), default=None)
    best_f1 = max((v["f1"] for v in ms.values()), default=None)
    best_kwh = min((abs(v["kwh"] - real["kwh"]) for v in ms.values()), default=None)
    items = [dict(color=theme.color(dev), name=f"Gerçek: {theme.tr(dev)}", big=f"{real['kwh']:,.3f}", unit="kWh",
                  sub=f"{real['tl']:,.2f} TL (pencere içinde)")]
    for m, v in ms.items():
        diff = (v["kwh"] - real["kwh"]) / real["kwh"] * 100 if real["kwh"] else 0.0
        items.append(dict(
            color=theme.mcolor(m), name=m, big=f"{v['kwh']:,.3f}", unit="kWh", sub=f"gerçeğe göre %{diff:+.1f}",
            tag="en yakın enerji" if multi and abs(v["kwh"] - real["kwh"]) == best_kwh else "",
            rows=[("Ortalama hata (MAE)", f"{v['mae']:,.1f} W", multi and v["mae"] == best_mae),
                  ("AÇIK/KAPALI (F1)", f"{v['f1']:.2f}", multi and v["f1"] == best_f1),
                  ("Fatura farkı", f"{v['tl'] - real['tl']:+,.2f} TL", False)]))
    theme.cards(items)
    return st_


def compare_view(wfull: pd.DataFrame, dev: str, models, start, end, price: float, smooth="Hafif",
                 show_agg=False, show_on=False, show_err=False, height=400):
    """Seçili pencerede gerçek + tüm modeller tek grafikte, altında model kartları."""
    g = wfull[(wfull["timestamp"] >= start) & (wfull["timestamp"] <= end)]
    if g.empty:
        st.info("Bu aralıkta veri yok. Pencereyi genişletin.")
        return None
    thr = config.ON_THRESHOLD_W.get(dev, config.DEFAULT_ON_THRESHOLD_W)
    bands = on_bands(g["timestamp"], g["Gerçek"].to_numpy(), thr) if show_on else None
    view, step = smooth_view(g, models, smooth)
    theme.model_legend(models, real_color=theme.color(dev), real_label=f"Gerçek: {theme.tr(dev)}")
    st.altair_chart(charts.series_multi(view, dev, models, show_agg, bands, height), width="stretch")
    if show_err:
        theme.section("Hata")
        for i, m in enumerate(models):
            st.caption(m)
            st.altair_chart(charts.residual(view.assign(Tahmin=view[f"m{i}"])), width="stretch")
    window_cards(g, dev, models, price)
    return g
