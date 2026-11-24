"""Panelin veri katmanı: tahmin dosyalarını ve results.csv'yi okur.
Dosyalar yoksa sahte veriyle demo moduna düşer (is_demo=True)."""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import pandas as pd
import streamlit as st

from nilm import config
from nilm.eval import metrics, predictions, report
from nilm.eval.results import RESULTS


@st.cache_data(show_spinner="Veri yükleniyor...")
def load():
    """-> (tahminler, sonuçlar, demo_mu). Tahminler: predictions.COLUMNS + model."""
    pred = predictions.load_all()
    if not pred.empty:
        res = report.load(RESULTS) if Path(RESULTS).exists() else _results_from(pred)
        return pred, res, False
    from scripts import run_eval, synthetic
    df = synthetic.make()
    res = run_eval.run(df, "synthetic", list(run_eval.MODELS), log=False, save_preds=False)
    res["kind"] = res["dataset"].str.extract(r"\((\w+)\)$")[0]
    # demo tahminleri bellekte üret
    frames = []
    test_houses = [h for h in sorted(df["house"].unique()) if h not in config.TRAIN_HOUSES]
    for name, make in run_eval.MODELS.items():
        for a in config.APPLIANCES:
            sub = df[df["appliance"] == a]
            model = make().fit(sub[sub["house"].isin(config.TRAIN_HOUSES)])
            for h in test_houses:
                t = sub[sub["house"] == h]
                f = predictions.to_frame(t, model.predict(t["aggregate_w"].to_numpy()))
                f["model"] = name
                frames.append(f)
    return pd.concat(frames, ignore_index=True), res, True


def _results_from(pred: pd.DataFrame) -> pd.DataFrame:
    """results.csv yoksa tahminlerden metrikleri hesapla."""
    rows = []
    for (m, h, a), g in pred.groupby(["model", "house", "appliance"]):
        y, p = g["appliance_w"].to_numpy(), g["predicted_w"].to_numpy()
        kind = "unseen" if h in config.UNSEEN_HOUSES else "test"
        rows.append(dict(model=m, dataset=f"house{h}({kind})", appliance=a, kind=kind,
                         mae=metrics.mae(y, p), sae=metrics.sae(y, p),
                         f1=metrics.f1_on_off(y, p, config.ON_THRESHOLD_W.get(
                             a, config.DEFAULT_ON_THRESHOLD_W)),
                         tl_error=metrics.tl_error(y, p, config.SAMPLE_PERIOD_S, config.TL_PER_KWH),
                         predict_ms=float("nan")))
    return pd.DataFrame(rows)


def sidebar(pred: pd.DataFrame, demo: bool, houses_only=None):
    """Ortak kenar çubuğu: model, ev, birim fiyat. -> (model, house, price)."""
    with st.sidebar:
        st.header("Ayarlar")
        if demo:
            st.warning("Demo modu: sahte veri. Gerçek sonuçlar için `python -m scripts.run_eval --data ...` çalıştırın.")
        models = sorted(pred["model"].unique())
        model = st.selectbox("Model", models)
        houses = sorted(pred["house"].unique())
        if houses_only:
            houses = [h for h in houses if h in houses_only] or houses
        house = st.selectbox("Ev", houses)
        price = st.number_input("Birim fiyat (TL/kWh)", 0.0, 50.0, float(config.TL_PER_KWH), 0.1)
    return model, int(house), float(price)


def bill_table(pred: pd.DataFrame, model: str, house: int, price: float) -> pd.DataFrame:
    """Seçili model ve ev için cihaz bazlı kWh ve TL tablosu."""
    dt = config.SAMPLE_PERIOD_S
    sub = pred[(pred["model"] == model) & (pred["house"] == house)]
    rows = []
    for a in config.APPLIANCES:
        g = sub[sub["appliance"] == a]
        if g.empty:
            continue
        y, p = g["appliance_w"].to_numpy(), g["predicted_w"].to_numpy()
        rows.append({
            "Cihaz": a,
            "Gerçek (kWh)": metrics.energy_kwh(y, dt),
            "Tahmin (kWh)": metrics.energy_kwh(p, dt),
            "Gerçek (TL)": metrics.bill_tl(y, dt, price),
            "Tahmin (TL)": metrics.bill_tl(p, dt, price),
            "Hata (TL)": metrics.tl_error(y, p, dt, price),
        })
    return pd.DataFrame(rows).set_index("Cihaz") if rows else pd.DataFrame()
