import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

import streamlit as st

from nilm import config
from nilm.eval import report
from panel import data

st.title("Hiç görülmeyen ev sonuçları")
st.caption(f"Modelin eğitimde hiç görmediği ev(ler): {config.UNSEEN_HOUSES}. "
           "Genelleme başarısını bu sonuçlar gösterir.")

pred, res, demo = data.load()
if demo:
    st.warning("Demo modu: sahte veri.")

r = res[res["kind"] == "unseen"]
if r.empty:
    st.info("Henüz görülmeyen ev sonucu yok.")
    st.stop()

metric = st.selectbox("Metrik", list(report.METRICS), format_func=report.METRICS.get)
st.bar_chart(r.pivot_table(index="appliance", columns="model", values=metric, aggfunc="mean"))

st.subheader("Fatura doğruluğu")
model, house, price = data.sidebar(pred, demo, houses_only=config.UNSEEN_HOUSES)
bill = data.bill_table(pred, model, house, price)
if not bill.empty:
    st.bar_chart(bill[["Gerçek (TL)", "Tahmin (TL)"]])
    st.dataframe(bill.round(3), width="stretch")
