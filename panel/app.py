"""NILM web paneli (Streamlit). Çalıştırma: streamlit run panel/app.py"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import pandas as pd
import streamlit as st

from nilm import config
from nilm.data.schema import validate
from nilm.eval import metrics
from nilm.eval.results import RESULTS
from scripts.run_eval import MODELS

st.set_page_config(page_title="NILM Paneli", layout="wide")
st.title("Cihaz bazlı elektrik tüketimi ve tahmini fatura")
st.caption("Tek sayaçtan (toplam güç) cihaz bazında tüketimi tahmin eder, faturayı cihazlara böler.")


@st.cache_data
def synthetic():
    from scripts import synthetic as syn
    return syn.make()


def read_upload(f) -> pd.DataFrame:
    df = pd.read_parquet(f) if f.name.endswith(".parquet") else pd.read_csv(f)
    return validate(df)


# ---- Kenar çubuğu ----
with st.sidebar:
    st.header("Ayarlar")
    src = st.radio("Veri kaynağı", ["Sahte veri (demo)", "Dosya yükle"])
    if src == "Dosya yükle":
        up = st.file_uploader("Şemaya uygun .csv / .parquet", type=["csv", "parquet"])
        if up is None:
            st.info("Dosya yükleyin ya da demo veriyi seçin.")
            st.stop()
        df = read_upload(up)
    else:
        df = synthetic()
    model_name = st.selectbox("Model", list(MODELS))
    houses = sorted(df["house"].unique())
    default_h = next((h for h in houses if h in config.UNSEEN_HOUSES), houses[0])
    house = st.selectbox("Ev", houses, index=houses.index(default_h))
    price = st.number_input("Birim fiyat (TL/kWh)", 0.0, 50.0, float(config.TL_PER_KWH), 0.1)

if house in config.TRAIN_HOUSES:
    st.warning(f"Ev {house} eğitimde kullanıldı; sonuçlar iyimser olabilir. "
               f"Hiç görülmeyen ev: {config.UNSEEN_HOUSES}.")


@st.cache_data
def predict_all(df, model_name, house):
    out = {}
    for a in config.APPLIANCES:
        sub = df[df["appliance"] == a]
        train = sub[sub["house"].isin(config.TRAIN_HOUSES)]
        test = sub[sub["house"] == house]
        if train.empty or test.empty:
            continue
        model = MODELS[model_name]().fit(train)
        out[a] = (test["timestamp"].to_numpy(), test["aggregate_w"].to_numpy(),
                  test["appliance_w"].to_numpy(), model.predict(test["aggregate_w"].to_numpy()))
    return out


preds = predict_all(df, model_name, house)
if not preds:
    st.error("Bu ev/model için gösterilecek veri yok.")
    st.stop()

# ---- Fatura tablosu ----
dt = config.SAMPLE_PERIOD_S
rows = []
for a, (_, _, y, p) in preds.items():
    rows.append({
        "Cihaz": a,
        "Gerçek (kWh)": metrics.energy_kwh(y, dt),
        "Tahmin (kWh)": metrics.energy_kwh(p, dt),
        "Gerçek (TL)": metrics.bill_tl(y, dt, price),
        "Tahmin (TL)": metrics.bill_tl(p, dt, price),
        "Hata (TL)": metrics.tl_error(y, p, dt, price),
        "F1": metrics.f1_on_off(y, p, config.ON_THRESHOLD_W.get(a, config.DEFAULT_ON_THRESHOLD_W)),
    })
bill = pd.DataFrame(rows).set_index("Cihaz")

c1, c2, c3 = st.columns(3)
c1.metric("Gerçek toplam (TL)", f"{bill['Gerçek (TL)'].sum():.2f}")
c2.metric("Tahmin toplam (TL)", f"{bill['Tahmin (TL)'].sum():.2f}")
c3.metric("Toplam hata (TL)", f"{bill['Hata (TL)'].sum():.2f}")

st.subheader("Cihaz bazlı fatura: gerçek ve tahmin")
st.bar_chart(bill[["Gerçek (TL)", "Tahmin (TL)"]])
st.dataframe(bill.round(3), width="stretch")

# ---- Zaman serisi ----
st.subheader("Zaman serisi")
dev = st.selectbox("Cihaz", list(preds))
ts, agg, y, p = preds[dev]
step = max(1, len(ts) // 3000)  # grafiği hafif tut
ts_df = pd.DataFrame({"Toplam": agg, "Gerçek": y, "Tahmin": p}, index=pd.to_datetime(ts))[::step]
st.line_chart(ts_df)

# ---- Model karşılaştırması ----
st.subheader("Model karşılaştırması (results.csv)")
if Path(RESULTS).exists():
    from nilm.eval import report
    res = report.load(RESULTS)
    metric = st.selectbox("Metrik", list(report.METRICS), format_func=report.METRICS.get)
    pv = res.pivot_table(index="appliance", columns="model", values=metric, aggfunc="mean")
    st.bar_chart(pv)
    st.dataframe(report.summary(res).round(3), width="stretch")
else:
    st.info("results/results.csv yok. Önce: python -m scripts.run_eval ...")
