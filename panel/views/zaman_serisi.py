import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

import pandas as pd
import streamlit as st

from panel import data

st.title("Gerçek ve tahmin zaman serisi")

pred, res, demo = data.load()
model, house, price = data.sidebar(pred, demo)
sub = pred[(pred["model"] == model) & (pred["house"] == house)]
if sub.empty:
    st.error("Bu model ve ev için veri yok.")
    st.stop()

dev = st.selectbox("Cihaz", sorted(sub["appliance"].unique()))
g = sub[sub["appliance"] == dev].sort_values("timestamp")
lo, hi = g["timestamp"].min().to_pydatetime(), g["timestamp"].max().to_pydatetime()
start, end = st.slider("Zaman aralığı", lo, hi, (lo, min(hi, lo + pd.Timedelta(hours=6))),
                       format="DD.MM HH:mm")
g = g[(g["timestamp"] >= start) & (g["timestamp"] <= end)]
if g.empty:
    st.info("Bu aralıkta veri yok.")
    st.stop()

show_agg = st.checkbox("Toplam (ana sayaç) gücünü de göster", value=False)
step = max(1, len(g) // 3000)  # grafiği hafif tut
cols = {"appliance_w": "Gerçek", "predicted_w": "Tahmin"}
if show_agg:
    cols["aggregate_w"] = "Toplam"
view = g.set_index("timestamp")[list(cols)].rename(columns=cols)[::step]
st.line_chart(view)
st.caption(f"{len(g)} örnek, grafikte her {step}. örnek gösteriliyor." if step > 1 else f"{len(g)} örnek.")
