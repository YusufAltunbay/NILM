import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

import numpy as np
import pandas as pd
import streamlit as st

from nilm import config
from nilm.eval import metrics
from panel import charts, data, theme

pred, res, demo = data.load()
model, house, price = data.sidebar(pred, demo)
sub = pred[(pred["model"] == model) & (pred["house"] == house)]

theme.page_header("Gerçek ve tahmin edilen güç",
                  "Seçilen cihazın gerçek gücü (dolgulu alan) ile modelin tahmini (kesikli çizgi) aynı grafikte.",
                  chips=[f"Ev {house}", f"Model: {model}"], demo=demo)
if sub.empty:
    st.error("Bu model ve ev için veri yok. Kenar çubuğundan başka bir seçim yapın.")
    st.stop()

devs = [a for a in theme.APPLIANCES if a in set(sub["appliance"])] or sorted(sub["appliance"].unique())
dev = st.segmented_control("Cihaz", devs, default=devs[0], format_func=theme.tr, label_visibility="collapsed") or devs[0]

g_all = sub[sub["appliance"] == dev].sort_values("timestamp")
lo, hi = g_all["timestamp"].min().to_pydatetime(), g_all["timestamp"].max().to_pydatetime()
total = hi - lo

WINDOWS = {"1 saat": pd.Timedelta(hours=1), "6 saat": pd.Timedelta(hours=6), "1 gün": pd.Timedelta(days=1),
           "3 gün": pd.Timedelta(days=3), "Tümü": None}
c1, c2 = st.columns([2, 3], vertical_alignment="bottom")
with c1:
    wname = st.segmented_control("Pencere", list(WINDOWS), default="6 saat") or "6 saat"
win = WINDOWS[wname]
if win is None or win >= total:
    start, end = lo, hi
else:
    with c2:
        start = st.slider("Başlangıç", lo, hi - win.to_pytimedelta(), lo, format="DD.MM HH:mm")
    end = start + win.to_pytimedelta()

o1, o2, o3 = st.columns(3)
show_agg = o1.toggle("Toplam gücü göster", value=False)
show_on = o2.toggle("Cihazın AÇIK olduğu dönemleri işaretle", value=True)
show_err = o3.toggle("Hata grafiğini göster", value=False)

g = g_all[(g_all["timestamp"] >= start) & (g_all["timestamp"] <= end)]
if g.empty:
    st.info("Bu aralıkta veri yok. Pencereyi genişletin.")
    st.stop()

thr = config.ON_THRESHOLD_W.get(dev, config.DEFAULT_ON_THRESHOLD_W)
y, p = g["appliance_w"].to_numpy(), g["predicted_w"].to_numpy()
dt = config.SAMPLE_PERIOD_S
f1 = metrics.f1_on_off(y, p, thr)
strip_cells = [
    dict(lab="Gerçek enerji", num=f"{metrics.energy_kwh(y, dt):,.3f}", unit="kWh", sub=f"{metrics.bill_tl(y, dt, price):,.2f} TL", small=True),
    dict(lab="Tahmin edilen enerji", num=f"{metrics.energy_kwh(p, dt):,.3f}", unit="kWh", sub=f"{metrics.bill_tl(p, dt, price):,.2f} TL", small=True),
    dict(lab="Ortalama hata (MAE)", num=f"{metrics.mae(y, p):,.1f}", unit="W", sub="Düşük iyidir", small=True),
    dict(lab="AÇIK/KAPALI doğruluğu (F1)", num=f"{f1:.2f}", sub=f"Eşik: {thr:g} W", small=True,
         tone="ok" if f1 >= 0.8 else ("over" if f1 < 0.5 else "")),
]
theme.strip(strip_cells)

bands = None
if show_on:
    on = y > thr
    edges = np.flatnonzero(np.diff(np.r_[False, on, False].astype(int)))
    ts = g["timestamp"].to_numpy()
    if 0 < len(edges) // 2 <= 400:  # çok sayıda küçük dönem grafiği boğar
        bands = pd.DataFrame({"start": ts[edges[0::2]], "end": ts[np.minimum(edges[1::2], len(ts)) - 1]})

step = max(1, len(g) // 2500)  # grafiği hafif tut
view = g.rename(columns={"appliance_w": "Gerçek", "predicted_w": "Tahmin", "aggregate_w": "Toplam"})[
    ["timestamp", "Gerçek", "Tahmin", "Toplam"]].iloc[::step]
st.altair_chart(charts.series(view, dev, show_agg, bands), width="stretch")
if show_err:
    theme.section("Hata", "Tahmin eksi gerçek. Kehribar: fazla tahmin, mavi: eksik tahmin.")
    st.altair_chart(charts.residual(view), width="stretch")

note = f"{len(g):,} örnek" + (f", grafikte her {step}. örnek gösteriliyor." if step > 1 else ".")
st.caption(note + " Grafiği fare tekerleğiyle yakınlaştırabilir, sürükleyerek kaydırabilirsiniz.")
st.download_button("Bu aralığı indir (CSV)", g.to_csv(index=False).encode("utf-8-sig"),
                   file_name=f"zaman_serisi_ev{house}_{dev.replace(' ', '_')}_{model}.csv", mime="text/csv")
