import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

import pandas as pd
import streamlit as st

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

g = sub[sub["appliance"] == dev].sort_values("timestamp")
lo, hi = g["timestamp"].min().to_pydatetime(), g["timestamp"].max().to_pydatetime()
c1, c2 = st.columns([3, 1], vertical_alignment="bottom")
with c1:
    start, end = st.slider("Zaman aralığı", lo, hi, (lo, min(hi, lo + pd.Timedelta(hours=6))), format="DD.MM HH:mm")
with c2:
    show_agg = st.toggle("Toplam gücü de göster", value=False)

g = g[(g["timestamp"] >= start) & (g["timestamp"] <= end)]
if g.empty:
    st.info("Bu aralıkta veri yok. Aralığı genişletin.")
    st.stop()

step = max(1, len(g) // 2500)  # grafiği hafif tut
view = g.rename(columns={"appliance_w": "Gerçek", "predicted_w": "Tahmin", "aggregate_w": "Toplam"})[
    ["timestamp", "Gerçek", "Tahmin", "Toplam"]].iloc[::step]
st.altair_chart(charts.series(view, dev, show_agg), width="stretch")
st.caption(f"{len(g):,} örnek" + (f", grafikte her {step}. örnek gösteriliyor." if step > 1 else "."))
