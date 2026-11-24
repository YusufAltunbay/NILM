import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

import streamlit as st

from panel import charts, data, theme

pred, res, demo = data.load()
model, house, price = data.sidebar(pred, demo)
bill = data.bill_table(pred, model, house, price)

theme.page_header("Faturanın cihazlara dağılımı",
                  "Tek bir ana sayaçtan okunan toplam güç, yapay zeka ile cihazlara bölünür. "
                  "Aşağıda tahmin edilen fatura, gerçek faturayla karşılaştırılıyor.",
                  chips=[f"Ev {house}", f"Model: {model}", f"{price:.2f} TL/kWh"], demo=demo)
if bill.empty:
    st.error("Bu model ve ev için veri yok. Kenar çubuğundan başka bir seçim yapın.")
    st.stop()

theme.bill_strip(bill["Gerçek (TL)"].sum(), bill["Tahmin (TL)"].sum(),
                 bill["Gerçek (kWh)"].sum(), bill["Tahmin (kWh)"].sum())

theme.section("Fatura şeridi", "Üst çubuk gerçek faturayı, alt çubuk modelin tahminini gösterir. "
                               "Dilimler aynı ölçekte olduğu için farklar doğrudan görülür.")
theme.legend(list(bill.index))
st.altair_chart(charts.ribbon(bill), width="stretch")

theme.section("Fatura kalemleri", "Mutlak hata, her cihazın faturasındaki sapmadır. Eksi ve artı hatalar birbirini götürmez.")
theme.ledger(bill)
