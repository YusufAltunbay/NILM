import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

import numpy as np
import pandas as pd
import streamlit as st

from nilm import config
from nilm.eval import report
from panel import blocks, charts, data, theme

pred, res, demo = data.load()
models, house, price = data.sidebar(pred, demo)

theme.page_header("Model karşılaştırma", chips=[f"Ev {house}", f"{len(models)} model"])
if len(models) < 2:
    st.info("Karşılaştırma için sol panelden en az iki model seçin.")
    st.stop()

r = res[res["dataset"].str.contains(rf"house{house}\(") & res["model"].isin(models)]
if r.empty:
    st.error("Bu ev için sonuç yok. Sol panelden başka bir ev seçin.")
    st.stop()

METRICS = ["mae", "sae", "tl_error", "f1"]
LABEL = {"mae": "MAE", "sae": "SAE", "tl_error": "Fatura hatası", "f1": "F1"}
FMT = {"mae": "{:.2f} W", "sae": "{:.3f}", "tl_error": "{:.3f} TL", "f1": "{:.2f}"}
ozet = r.groupby("model")[METRICS].mean()
LOWER = {"mae": True, "sae": True, "tl_error": True, "f1": False}

# ortalama sıra: her ölçütte 1. en iyi
ranks = pd.DataFrame({m: ozet[m].rank(ascending=LOWER[m], method="min") for m in METRICS})
ozet["sira"] = ranks.mean(axis=1)
order = list(ozet.sort_values(["sira", "mae"]).index)

# ---- 1. podyum
theme.section("Genel sıralama")
best_in = {m: (ozet[m].min() if LOWER[m] else ozet[m].max()) for m in METRICS}
cards = []
for n, name in enumerate(order, 1):
    row = ozet.loc[name]
    cards.append(dict(color=theme.mcolor(name), name=name, rank=n, first=n == 1, tag="lider" if n == 1 else "",
                      big=f"{row['sira']:.1f}", unit="ortalama sıra", sub=f"{len(order)} model arasında",
                      rows=[(LABEL[m], FMT[m].format(row[m]), row[m] == best_in[m]) for m in METRICS]))
theme.cards(cards)

# ---- 2. karne
theme.section("Ölçüt karnesi")
rows = []
for m in METRICS:
    best = best_in[m]
    for name in order:
        v = ozet.loc[name, m]
        score = (100.0 if v == best else (best / v * 100 if LOWER[m] else v / best * 100)) if (best or not LOWER[m]) else 100.0
        rows.append({"Ölçüt": LABEL[m], "Model": name, "Skor": float(np.clip(score, 0, 100)), "Değer": FMT[m].format(v)})
st.altair_chart(charts.scorecard(pd.DataFrame(rows)), width="stretch")

# ---- 3. cihaz bazında
theme.section("Cihaz cihaz")


@st.fragment
def per_device():
    metric = st.segmented_control("Ölçüt", list(report.METRICS), default="mae", format_func=report.METRICS.get, key="km_metric") or "mae"
    t1, t2 = st.tabs(["Çubuk grafik", "Isı haritası"])
    with t1:
        st.altair_chart(charts.model_bars(r, metric, report.METRICS[metric]), width="stretch")
    with t2:
        st.altair_chart(charts.heatmap(r, metric, report.METRICS[metric], metric != "f1"), width="stretch")


per_device()

# ---- 4. fatura yan yana
theme.section("Fatura yan yana")
bills = {"Gerçek": data.bill_table(pred, order[0], house, price)}
for name in order:
    bills[name] = data.bill_table(pred, name, house, price)
if not bills["Gerçek"].empty:
    theme.legend(list(bills["Gerçek"].index))
    st.altair_chart(charts.stacked_multi(bills), width="stretch")
    real_tl = bills["Gerçek"]["Gerçek (TL)"].sum()
    st.caption(f"Gerçek fatura: {real_tl:,.2f} TL. " + " ".join(
        f"{n}: {bills[n]['Tahmin (TL)'].sum():,.2f} TL ({(bills[n]['Tahmin (TL)'].sum() - real_tl) / real_tl * 100:+.1f}%)." for n in order))

# ---- 5. aynı ana bakış
theme.section("En hareketli 6 saat")
devs = theme.ordered(pred.loc[pred["house"] == house, "appliance"].unique())


@st.fragment
def live():
    dev = st.pills("Cihaz", devs, default=devs[0], format_func=theme.demoji, key="km_dev", label_visibility="collapsed") or devs[0]
    wf = data.wide(pred, house, dev, order)
    win = pd.Timedelta(hours=6)
    if wf["timestamp"].max() - wf["timestamp"].min() > win:
        start = data.busiest(house, dev, order, win)
    else:
        start = wf["timestamp"].min().to_pydatetime()
    blocks.compare_view(wf, dev, order, start, start + win.to_pytimedelta(), price, height=340)


live()

# ---- 6. tablo
theme.section("Tüm ölçütler")
tab = ozet.reset_index().rename(columns={"model": "Model"})
tab = tab.loc[tab["Model"].map({n: i for i, n in enumerate(order)}).sort_values().index]
cfg = {"sira": st.column_config.NumberColumn("Ortalama sıra", format="%.1f"),
       "mae": st.column_config.NumberColumn("MAE (W)", format="%.2f"),
       "sae": st.column_config.NumberColumn("SAE", format="%.3f"),
       "f1": st.column_config.ProgressColumn("F1", min_value=0.0, max_value=1.0, format="%.2f"),
       "tl_error": st.column_config.NumberColumn("Fatura hatası (TL)", format="%.3f")}
st.dataframe(tab, width="stretch", hide_index=True, column_config=cfg)
