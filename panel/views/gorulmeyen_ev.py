import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

import streamlit as st

from nilm import config
from nilm.eval import report
from panel import blocks, charts, data, theme

pred, res, demo = data.load()
model, house, price = data.sidebar(pred, demo, houses_only=config.UNSEEN_HOUSES)
house_txt = ", ".join(str(h) for h in config.UNSEEN_HOUSES)

theme.page_header("Hiç görülmeyen evde başarı",
                  f"Model ev {house_txt} verisini eğitimde hiç görmedi. Yeni bir eve ne kadar iyi uyum sağladığını bu sonuçlar gösterir.",
                  chips=[f"Ev {house}", f"Model: {model}"], demo=demo)
theme.callout("<b>Bu test neden önemli?</b> Gerçek bir üründe müşterinin evi eğitim verisinde olmaz. "
              "Model eğitimde gördüğü evlerde iyi olup yeni bir evde başarısız olabilir (ezberleme). "
              f"Ev {house_txt} eğitimden tamamen ayrıldığı için buradaki sonuç, modelin yeni bir eve ek eğitim olmadan çalışıp çalışmadığını gösterir.")

r = res[res["kind"] == "unseen"]
if r.empty:
    st.info("Henüz görülmeyen ev sonucu yok. `python -m scripts.run_eval` ile üretilir.")
    st.stop()

bill = data.bill_table(pred, model, house, price)
if not bill.empty:
    theme.bill_strip(bill["Gerçek (TL)"].sum(), bill["Tahmin (TL)"].sum(),
                     bill["Gerçek (kWh)"].sum(), bill["Tahmin (kWh)"].sum())
    theme.section("Fatura dağılımı", "Modelin hiç görmediği evde faturayı cihazlara ne kadar doğru böldüğü.")
    blocks.bill_view(bill, key="view_unseen", default="Dikey şerit")

theme.section("Ölçütler")
metric = st.selectbox("Ölçüt", list(report.METRICS), format_func=report.METRICS.get)
st.altair_chart(charts.model_bars(r, metric, report.METRICS[metric]), width="stretch")

if "test" in set(res["kind"]):
    theme.section("Görülen ve görülmeyen evler", "Aradaki fark modelin ne kadar genelleştiğini gösterir.")
    cmp = res.pivot_table(index="model", columns="kind", values=metric, aggfunc="mean")
    cmp.columns = [{"test": "Test evleri", "unseen": "Görülmeyen ev"}.get(c, c) for c in cmp.columns]
    st.dataframe(cmp.reset_index().rename(columns={"model": "Model"}), width="stretch", hide_index=True)
