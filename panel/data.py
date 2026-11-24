"""Panelin veri katmanı: tahmin dosyalarını ve results.csv'yi okur.
Dosyalar yoksa sahte veriyle demo moduna düşer (is_demo=True)."""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import numpy as np
import pandas as pd
import streamlit as st

from nilm import config
from nilm.eval import metrics, predictions, report
from nilm.eval.results import RESULTS


LABELS = {"mean": "Ortalama modeli"}  # ekranda gösterilen ad


def _finish(pred, res, demo):
    pred["model"] = pred["model"].replace(LABELS)
    res["model"] = res["model"].replace(LABELS)
    for c in ("model", "appliance"):
        pred[c] = pred[c].astype("category")  # bellek ve süzme hızı için
    return pred, res, demo


@st.cache_resource(show_spinner="Veri yükleniyor...")
def load():
    """-> (tahminler, sonuçlar, demo_mu). Önbellek kopya üretmez; dönen tablolar değiştirilmemeli."""
    return _finish(*_load())


def _load():
    pred = predictions.load_all()
    if not pred.empty:
        res = report.load(RESULTS) if Path(RESULTS).exists() else _results_from(pred)
        return pred, res, False
    from scripts import run_eval, synthetic
    df = synthetic.make(n=6000, n_test=200000)  # test evi ~14 gün
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
    pred = pd.concat(frames, ignore_index=True)
    pred = pd.concat([pred, *_demo_models(pred)], ignore_index=True)
    return pred, _results_from(pred), True


def _demo_models(base: pd.DataFrame):
    """Karşılaştırma ekranları dolu görünsün diye demo için iki sahte model üretir.
    Gerçek modeller (Ersin) gelince bunlar kullanılmaz; """
    out = []
    rng = np.random.default_rng(7)
    b = base[base["model"] == "mean"]
    sd = b.groupby(["house", "appliance"])["appliance_w"].transform("std").fillna(0).to_numpy()
    for name, skill, noise in (("Eşik modeli", 0.55, 0.45), ("Derin ağ", 0.85, 0.12)):
        f = b.copy()
        y, m = f["appliance_w"].to_numpy(), f["predicted_w"].to_numpy()
        p = skill * y + (1 - skill) * m + rng.normal(0, 1, len(f)) * noise * sd
        f["predicted_w"] = np.clip(p, 0, f["aggregate_w"].to_numpy())
        f["model"] = name
        out.append(f)
    return out


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
    """Ortak sol panel: modeller (birden fazla seçilebilir), ev, birim fiyat, seçili evin özeti.
    Giriş yapmış kullanıcı yalnızca kendi evini görür. -> (models, house, price)."""
    from panel import auth, theme
    all_models = sorted(pred["model"].unique())
    theme.register_models(all_models)
    user = auth.current()
    houses = sorted(int(h) for h in pred["house"].unique())
    if houses_only:
        houses = [h for h in houses if h in houses_only] or houses
    elif user and user.get("house") in houses:
        houses = [user["house"]]
    with st.sidebar:
        theme.side_label("Modeller")
        models = st.pills("Modeller", all_models, selection_mode="multi", default=all_models, key="sb_models",
                          format_func=theme.model_pill, label_visibility="collapsed") or all_models[:1]
        if len(houses) > 1:
            theme.side_label("Ev")
            house = st.selectbox("Ev", houses, key="sb_house_u" if houses_only else "sb_house",
                                 format_func=lambda h: f"Ev {h}", label_visibility="collapsed")
        else:
            house = houses[0]
        theme.side_label("Birim fiyat (TL/kWh)")
        price = st.number_input("Birim fiyat", 0.0, 50.0, float(config.TL_PER_KWH), 0.1, key="sb_price",
                                label_visibility="collapsed")
        bill = bill_table(pred, models[0], int(house), float(price))
        if not bill.empty:
            theme.side_card(f"Ev {house}", f"{bill['Gerçek (TL)'].sum():,.0f}", "TL",
                            f"{bill['Gerçek (kWh)'].sum():,.1f} kWh",
                            [(theme.color(a), v) for a, v in bill["Gerçek (TL)"].items()])
        if user:
            theme.side_user(user["name"], user.get("house"))
            if st.button("Çıkış yap", key="sb_logout", icon=":material/logout:", width="stretch"):
                auth.logout()
                st.rerun()
    return models, int(house), float(price)


def one_model(models, key: str) -> str:
    """Tek modelli sayfalar için: birden fazla model seçiliyse sayfada küçük bir seçici çıkar."""
    if len(models) == 1:
        return models[0]
    return st.segmented_control("Gösterilen model", models, default=models[0], key=key) or models[0]


@st.cache_resource(max_entries=48)
def _wide(house: int, appliance: str, models: tuple) -> pd.DataFrame:
    pred = load()[0]
    sub = pred[(pred["house"] == house) & (pred["appliance"] == appliance) & pred["model"].isin(models)]
    first = sub[sub["model"] == models[0]].sort_values("timestamp")
    out = first[["timestamp", "appliance_w", "aggregate_w"]].rename(columns={"appliance_w": "Gerçek", "aggregate_w": "Toplam"})
    for i, m in enumerate(models):
        part = sub[sub["model"] == m].drop_duplicates("timestamp").set_index("timestamp")["predicted_w"].rename(f"m{i}")
        out = out.merge(part, left_on="timestamp", right_index=True, how="left")
    return out.reset_index(drop=True)


def wide(pred, house: int, appliance: str, models) -> pd.DataFrame:
    """Bir cihaz için zaman damgası başına tek satır: Gerçek, Toplam ve her modelin tahmini (m0, m1, ...). Önbellekli."""
    return _wide(int(house), str(appliance), tuple(models))


@st.cache_resource(max_entries=16)
def _minimap(house: int, appliance: str, models: tuple) -> pd.DataFrame:
    w = _wide(house, appliance, models)
    return w.set_index("timestamp")["Gerçek"].resample("10min").mean().reset_index()


def minimap(house, appliance, models):
    return _minimap(int(house), str(appliance), tuple(models))


@st.cache_resource(max_entries=256)
def _busiest(house: int, appliance: str, models: tuple, hours: float):
    w = _wide(house, appliance, models)
    return busiest_start(w["timestamp"], w["Gerçek"], pd.Timedelta(hours=hours))


def busiest(house, appliance, models, win: pd.Timedelta):
    return _busiest(int(house), str(appliance), tuple(models), win / pd.Timedelta(hours=1))


def busiest_start(ts: pd.Series, power: pd.Series, win: pd.Timedelta):
    """Cihazın en çok enerji harcadığı pencerenin başlangıcı (dakikalık özetten, hızlı)."""
    s = pd.Series(power.to_numpy(), index=pd.DatetimeIndex(ts)).resample("1min").mean().fillna(0)
    n = max(1, int(win / pd.Timedelta(minutes=1)))
    if len(s) <= n:
        return s.index[0].to_pydatetime()
    cs = np.r_[0, np.cumsum(s.to_numpy())]
    k = int(np.argmax(cs[n:] - cs[:-n]))
    return s.index[k].to_pydatetime()


@st.cache_resource(max_entries=256)
def _bill(model: str, house: int, price: float) -> pd.DataFrame:
    pred = load()[0]
    dt = config.SAMPLE_PERIOD_S
    sub = pred[(pred["model"] == model) & (pred["house"] == house)]
    rows = []
    from panel import theme
    for a in theme.ordered(sub["appliance"].unique()):
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


def bill_table(pred, model: str, house: int, price: float) -> pd.DataFrame:
    """Seçili model ve ev için cihaz bazlı kWh ve TL tablosu. Önbellekli."""
    return _bill(str(model), int(house), round(float(price), 6))


@st.cache_resource(max_entries=64)
def _facts(house: int, model: str, appliance: str, price: float) -> dict:
    from panel import insights
    w = _wide(house, appliance, (model,))
    return insights.usage_facts(w["timestamp"], w["m0"], appliance, price)


def usage_facts(house, model, appliance, price) -> dict:
    """Kullanım sayısı, bir kullanımın maliyeti, en yoğun saat, bekleme payı. Önbellekli."""
    return _facts(int(house), str(model), str(appliance), round(float(price), 6))
