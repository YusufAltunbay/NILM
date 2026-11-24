import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

import streamlit as st

from nilm.eval import report
from panel import charts, data, theme

pred, res, demo = data.load()
theme.page_header("Model karşılaştırma",
                  "Hangi model faturayı cihazlara daha iyi bölüyor? Önce modellerin genel sıralaması, sonra hangi modelin hangi cihazda güçlü olduğu.",
                  demo=demo)

kinds = sorted(res["kind"].dropna().unique())
labels = {"test": "Test evleri", "unseen": "Hiç görülmeyen ev"}
c1, c2 = st.columns([1, 1])
with c1:
    kind = st.segmented_control("Veri", kinds, default=kinds[0], format_func=lambda k: labels.get(k, k)) or kinds[0]
with c2:
    metric = st.selectbox("Ölçüt", list(report.METRICS), format_func=report.METRICS.get)
r = res[res["kind"] == kind]
lower_better = metric != "f1"

cols = list(report.METRICS) + ["predict_ms"]
ozet = r.groupby("model")[cols].mean().reset_index().rename(columns={"model": "Model"})

LOWER = {"mae": ("En düşük MAE", "W", "{:.2f}"), "sae": ("En düşük SAE", "", "{:.3f}"),
         "tl_error": ("En düşük fatura hatası", "TL", "{:.3f}")}
cells = []
for m, (lab, unit, fmt) in LOWER.items():
    b = ozet.loc[ozet[m].idxmin()]
    cells.append(dict(lab=lab, num=fmt.format(b[m]), unit=unit, sub=f"Model: {b['Model']}", small=True))
b = ozet.loc[ozet["f1"].idxmax()]
cells.append(dict(lab="En yüksek F1", num=f"{b['f1']:.2f}", sub=f"Model: {b['Model']}", small=True))
theme.strip(cells)

theme.section("Genel sıralama", f"{report.METRICS[metric]}. Cihazlar üzerinden ortalama, en iyi model üstte.")
st.altair_chart(charts.rank_bars(ozet, metric, report.METRICS[metric], lower_better), width="stretch")

theme.section("Hangi model hangi cihazda iyi?",
              "Her cihaz kendi içinde değerlendirilir: koyu kutu, o cihazda daha iyi olan modeldir. Çerçeveli kutu en iyi modeli gösterir. Kutudaki sayı seçili ölçütün değeridir.")
st.altair_chart(charts.heatmap(r, metric, report.METRICS[metric], lower_better), width="stretch")

theme.section("Tüm ölçütler", "Cihazlar üzerinden ortalama.")
st.dataframe(ozet, width="stretch", hide_index=True, column_config={
    "mae": st.column_config.NumberColumn("MAE (W)", format="%.2f"),
    "sae": st.column_config.NumberColumn("SAE", format="%.3f"),
    "f1": st.column_config.ProgressColumn("F1", min_value=0.0, max_value=1.0, format="%.2f"),
    "tl_error": st.column_config.NumberColumn("Fatura hatası (TL)", format="%.3f"),
    "predict_ms": st.column_config.NumberColumn("Tahmin süresi (ms)", format="%.2f"),
})
