import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

import streamlit as st

from panel import blocks, data, theme

pred, res, demo = data.load()
models, house, price = data.sidebar(pred, demo)
model = data.one_model(models, "model_tuketim")
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
theme.callout(theme.summary_sentence(bill))

theme.section("Faturanın dağılımı", "Aynı veriyi dört farklı biçimde görebilirsiniz.")
blocks.bill_view(bill, key="view_tuketim", default="Şerit")

theme.section("Fatura kalemleri", "Mutlak hata, her cihazın faturasındaki sapmadır. Eksi ve artı hatalar birbirini götürmez.")
theme.ledger(bill)
out = bill.rename_axis("Cihaz").reset_index()
out["Cihaz"] = out["Cihaz"].map(theme.tr)
st.download_button("Tabloyu indir (CSV)", out.round(4).to_csv(index=False).encode("utf-8-sig"),
                   file_name=f"fatura_ev{house}_{model}.csv", mime="text/csv")
