import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

import streamlit as st

from panel import data

st.title("Cihaz bazlı tüketim ve fatura")
st.caption("Tek sayaçtan (toplam güç) cihaz bazında tüketimi tahmin eder, faturayı cihazlara böler.")

pred, res, demo = data.load()
model, house, price = data.sidebar(pred, demo)
bill = data.bill_table(pred, model, house, price)
if bill.empty:
    st.error("Bu model ve ev için veri yok.")
    st.stop()

c1, c2, c3, c4 = st.columns(4)
real, est = bill["Gerçek (TL)"].sum(), bill["Tahmin (TL)"].sum()
c1.metric("Gerçek toplam (TL)", f"{real:.2f}")
c2.metric("Tahmin toplam (TL)", f"{est:.2f}")
c3.metric("Toplam fark (TL)", f"{est - real:+.2f}")
c4.metric("Cihaz bazlı hata (TL)", f"{bill['Hata (TL)'].sum():.2f}",
          help="Her cihazın faturasındaki mutlak hataların toplamı. Fark eksi/artı birbirini götürür, bu götürmez.")

left, right = st.columns(2)
with left:
    st.subheader("Fatura: gerçek ve tahmin (TL)")
    st.bar_chart(bill[["Gerçek (TL)", "Tahmin (TL)"]])
with right:
    st.subheader("Tüketim: gerçek ve tahmin (kWh)")
    st.bar_chart(bill[["Gerçek (kWh)", "Tahmin (kWh)"]])

st.subheader("Ayrıntı")
st.dataframe(bill.round(3), width="stretch")
