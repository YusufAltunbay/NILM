import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

import streamlit as st

from panel import blocks, data, theme

pred, res, demo = data.load()
models, house, price = data.sidebar(pred, demo)
model = data.one_model(models, "model_tuketim")
bill = data.bill_table(pred, model, house, price)

theme.page_header("Fatura dağılımı", chips=[f"Ev {house}", model, f"{price:.2f} TL/kWh"])
if bill.empty:
    st.error("Bu model ve ev için veri yok. Kenar çubuğundan başka bir seçim yapın.")
    st.stop()

theme.bill_strip(bill["Gerçek (TL)"].sum(), bill["Tahmin (TL)"].sum(),
                 bill["Gerçek (kWh)"].sum(), bill["Tahmin (kWh)"].sum())
theme.callout(theme.summary_sentence(bill))

theme.section("Dağılım")
blocks.bill_view(bill, key="view_tuketim", default="Şerit")

theme.section("Fatura kalemleri")
theme.ledger(bill)
out = bill.rename_axis("Cihaz").reset_index()
out["Cihaz"] = out["Cihaz"].map(theme.tr)
st.download_button("Tabloyu indir (CSV)", out.round(4).to_csv(index=False).encode("utf-8-sig"),
                   file_name=f"fatura_ev{house}_{model}.csv", mime="text/csv")
