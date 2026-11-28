import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

import html

import pandas as pd
import streamlit as st

from panel import blocks, charts, data, theme

pred, res, demo = data.load()
models, house, price = data.sidebar(pred, demo)

theme.page_header("Fatura dağılımı", chips=[data.house_name(house), "Aylık ortalama", f"{price:.2f} TL/kWh"])
model = data.one_model(models, "model_tuketim")
bill = data.bill_table(pred, model, house, price, other=True, monthly=True)
if bill.empty:
    st.error("Bu model ve ev için veri yok. Kenar çubuğundan başka bir seçim yapın.")
    st.stop()

MINE, SAMPLE = "Benim faturam", "Model doğruluğu (örnek ev ölçümü)"
b1, b2 = st.columns([1.3, 2], vertical_alignment="bottom")
with b1:
    blocks.bill_form("tk_bill")
mine = data.my_split(model, house, price)
with b2:
    if mine is None:
        theme.callout("Faturanı girersen bu sayfa <b>senin evine</b> göre hesaplanır. Şimdilik örnek evin ölçümü gösteriliyor.")
        mode = SAMPLE
    else:
        mode = st.segmented_control("Görünüm", [MINE, SAMPLE], default=MINE, key="tk_mode", label_visibility="collapsed") or MINE

if mode == MINE:
    dev, other = mine
    total = data.my_bill()
    tl = pd.concat([dev["TL"], pd.Series({"other": other})])
    kwh = pd.concat([dev["kWh"], pd.Series({"other": other / max(price, 1e-9)})])
    top = dev["TL"].idxmax()
    theme.strip([dict(lab="Aylık faturan", num=f"{total:,.2f}", unit="TL", sub=f"{total / max(price, 1e-9):,.0f} kWh"),
                 dict(lab=f"{len(dev)} cihazın tahmini payı", num=f"{dev['TL'].sum():,.2f}", unit="TL",
                      sub=f"faturanın %{dev['TL'].sum() / total * 100:.0f}'i"),
                 dict(lab="En büyük kalem", num=f"{dev.loc[top, 'TL']:,.2f}", unit="TL", sub=theme.tr(top))])
    theme.callout(f"Faturanın yaklaşık <b>%{dev['TL'].sum() / total * 100:.0f}</b>'i bu {len(dev)} cihazdan, en büyük kalem "
                  f"<b>{html.escape(theme.tr(top))}</b>. Kalan <b>{other:,.0f} TL</b> aydınlatma, TV, ısıtma gibi diğer cihazlar. "
                  f"Paylar <b>{html.escape(model)}</b> modelinin örnek evdeki ayrımından tahmin edildi.")
    theme.section("Dağılım")
    view = st.segmented_control("Görünüm", ["Halka", "Şerit", "Dikey şerit", "Çubuk"], default="Halka", key="view_mine",
                                label_visibility="collapsed") or "Halka"
    if view == "Halka":   # halka solda, kalemler sağda
        with st.container(key="mine_split"):   # halka kutusu tablo ile aynı yükseklikte (CSS: theme)
            c1, c2 = st.columns([1, 1.35], gap="large")
            with c1:
                st.altair_chart(charts.share_donut(tl), width="content")
            with c2:
                theme.share_table(tl, kwh)
    else:
        theme.legend(list(tl.index))
        chart = {"Şerit": charts.ribbon, "Dikey şerit": charts.stacked, "Çubuk": charts.bars}[view]
        st.altair_chart(chart(pd.DataFrame({"Tahmin (TL)": tl}), (("Senin faturan", "Tahmin (TL)"),)), width="stretch")
        theme.section("Fatura kalemleri")
        theme.share_table(tl, kwh)
    st.stop()

theme.bill_strip(bill)
theme.callout(theme.summary_sentence(bill))

theme.section("Dağılım")
blocks.bill_view(bill, key="view_tuketim", default="Şerit")

theme.section("Fatura kalemleri")
theme.ledger(bill)
out = bill.drop(columns="Gün").rename_axis("Cihaz").reset_index()
out["Cihaz"] = out["Cihaz"].map(theme.tr)
st.download_button("Tabloyu indir (CSV)", out.round(4).to_csv(index=False).encode("utf-8-sig"),
                   file_name=f"fatura_ev{house}_{model}.csv", mime="text/csv")
