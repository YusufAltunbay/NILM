import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

import streamlit as st

from nilm.eval import report
from panel import data

st.title("Model karşılaştırma")

pred, res, demo = data.load()
if demo:
    st.warning("Demo modu: sahte veri.")

kinds = sorted(res["kind"].dropna().unique())
kind = st.radio("Test evleri", kinds, horizontal=True,
                format_func=lambda k: {"test": "Test", "unseen": "Hiç görülmeyen ev"}.get(k, k))
r = res[res["kind"] == kind]

metric = st.selectbox("Metrik", list(report.METRICS), format_func=report.METRICS.get)
st.bar_chart(r.pivot_table(index="appliance", columns="model", values=metric, aggfunc="mean"))

st.subheader("Model özeti (cihazlar üzerinden ortalama)")
cols = list(report.METRICS) + ["predict_ms"]
ozet = r.groupby("model")[cols].mean().rename(columns={
    "mae": "MAE (W)", "sae": "SAE", "f1": "F1", "tl_error": "Fatura hatası (TL)", "predict_ms": "Tahmin süresi (ms)"})
st.dataframe(ozet.round(3), width="stretch")

st.subheader("Cihaz bazında tüm sonuçlar")
st.dataframe(report.summary(r).round(3), width="stretch", hide_index=True)
