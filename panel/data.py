"""Panelin veri katmanı: tahmin dosyalarını ve results.csv'yi okur.

Gerçek tahminler 6 sn'lik ve büyük (~76 milyon satır). Panel bunları bir kez dakikalık
ortalamaya indirip .panel/ altına önbellek dosyası olarak yazar; sonraki açılışlar bu
küçük dosyadan okunur (~10 kat az satır, enerji/fatura değişmez çünkü ortalama korunur).
Tahmin dosyası yoksa sahte veriyle demo moduna düşer (is_demo=True)."""
import json
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


# Ekranda gösterilen adlar; sıra, seçicilerdeki sıradır. Bilinmeyen model ham adıyla görünür.
LABELS = {
    "mean": "Ortalama modeli",
    "threshold": "Eşik modeli",
    "seq2point": "seq2point (CNN)",
    "bert4nilm": "BERT4NILM (Transformer)",
}
# Tek modelli sayfalarda (fatura, tasarruf) ilk açılışta gösterilecek model: cihazları gerçekten
# ayırabilen bir model. Ortalama modeli sabit tahmin yaptığı için kullanım bilgisi üretemez.
PREFERRED = ["seq2point (CNN)", "BERT4NILM (Transformer)", "Eşik modeli"]
STEP_S = 60                          # panel önbelleğinin örnekleme aralığı (sn)
CACHE = ROOT / ".panel" / "tahmin_dakikalik.parquet"


def _finish(pred, res, demo, dt):
    for c in ("model", "appliance"):
        pred[c] = pred[c].astype("category")  # bellek ve süzme hızı için
    pred["model"] = pred["model"].cat.rename_categories(lambda m: LABELS.get(m, m))
    res["model"] = res["model"].replace(LABELS)
    pred.attrs["dt"] = dt
    return pred, res, demo


def model_order(models) -> list:
    """LABELS sırası önce, kalanlar alfabetik."""
    known = [v for v in LABELS.values() if v in set(models)]
    return known + sorted(m for m in models if m not in known)


def dt() -> int:
    """Yüklenen verinin örnekleme aralığı (sn): gerçek veride STEP_S, demoda config.SAMPLE_PERIOD_S."""
    return int(load()[0].attrs.get("dt", config.SAMPLE_PERIOD_S))


def house_name(h) -> str:
    """Giriş yapmış kullanıcıya kendi evi "Kamil'in evi" diye, misafire veri setindeki adıyla gösterilir."""
    if h is None:
        return "Tüm evler"
    h = int(h)
    from panel import auth
    user = auth.current() or {}
    if user.get("house") == h and user.get("name") and user.get("name") != "Misafir":
        return f"{auth.possessive(user['name'])} evi"
    if h in config.UNSEEN_HOUSES:
        return f"Ev {h} · görülmeyen"
    if h in getattr(config, "VAL_HOUSES", []):
        return f"Ev {h} · doğrulama"
    return f"Ev {h}"


@st.cache_resource(show_spinner="Veri yükleniyor... (ilk açılışta tahminler özetlenir, 1-2 dk sürebilir)")
def load():
    """-> (tahminler, sonuçlar, demo_mu). Önbellek kopya üretmez; dönen tablolar değiştirilmemeli."""
    return _finish(*_load())


def _signature(files) -> list:
    return [[f.name, f.stat().st_size, int(f.stat().st_mtime)] for f in files]


def _downsample(d: pd.DataFrame, step_s: int = STEP_S) -> pd.DataFrame:
    """6 sn'lik tahmin dosyasını step_s'lik ortalamaya indirir; boş aralıklar (kayıt boşlukları) atılır."""
    out = (d.set_index("timestamp")[["aggregate_w", "appliance_w", "pred_w"]]
             .resample(f"{step_s}s").mean().dropna().astype("float32").reset_index())
    return out.rename(columns={"pred_w": "predicted_w"})


def build_cache(root: Path | None = None, cache: Path = CACHE, step_s: int = STEP_S) -> pd.DataFrame | None:
    """Tahmin dosyalarını dakikalık tek tabloya indirir ve diske yazar. Dosyalar değişmediyse diskten okur.
    Dosya yoksa None. Her dosya ayrı okunup küçültüldüğü için bellekte hiçbir zaman tamamı durmaz."""
    trip = predictions.available(root)
    if not trip:
        return None
    files = [predictions.path(m, a, h, root) for m, a, h in trip]
    sig = {"step_s": step_s, "files": _signature(files)}
    meta = cache.with_suffix(".json")
    if cache.exists() and meta.exists() and json.loads(meta.read_text(encoding="utf-8")) == sig:
        return pd.read_parquet(cache)
    frames = []
    for (model, app, house), f in zip(trip, files):
        d = _downsample(pd.read_hdf(f, "data"), step_s)
        d["house"], d["appliance"], d["model"] = house, app, model
        frames.append(d)
    pred = pd.concat(frames, ignore_index=True)
    for c in ("model", "appliance"):
        pred[c] = pred[c].astype("category")
    pred["house"] = pred["house"].astype("int16")
    cache.parent.mkdir(parents=True, exist_ok=True)
    pred.to_parquet(cache, index=False)
    meta.write_text(json.dumps(sig), encoding="utf-8")
    return pred


def _load():
    pred = build_cache()
    if pred is not None:
        res = report.load(RESULTS) if Path(RESULTS).exists() else _results_from(pred, STEP_S)
        return pred, res, False, STEP_S
    from scripts import run_eval, synthetic
    df = synthetic.make(n=6000, n_test=200000)  # test evi ~14 gün
    frames = []
    test_houses = [h for h in sorted(df["house"].unique()) if h not in config.TRAIN_HOUSES]
    light = {k: v for k, v in run_eval.MODELS.items() if k in ("mean", "threshold")}  # demo için eğitim gerektirmeyenler
    for name, make in light.items():
        for a in config.APPLIANCES:
            sub = df[df["appliance"] == a]
            model = make().fit(sub[sub["house"].isin(config.TRAIN_HOUSES)])
            for h in test_houses:
                t = sub[sub["house"] == h]
                f = predictions.to_frame(t, model.predict(t["aggregate_w"].to_numpy()))
                f["model"] = name
                frames.append(f)
    pred = pd.concat(frames, ignore_index=True)
    return pred, _results_from(pred, config.SAMPLE_PERIOD_S), True, config.SAMPLE_PERIOD_S


def _results_from(pred: pd.DataFrame, step_s: int) -> pd.DataFrame:
    """results.csv yoksa tahminlerden metrikleri hesapla."""
    rows = []
    for (m, h, a), g in pred.groupby(["model", "house", "appliance"]):
        y, p = g["appliance_w"].to_numpy(), g["predicted_w"].to_numpy()
        kind = "unseen" if h in config.UNSEEN_HOUSES else "test"
        rows.append(dict(model=m, dataset=f"house{h}({kind})", appliance=a, kind=kind,
                         mae=metrics.mae(y, p), sae=metrics.sae(y, p),
                         f1=metrics.f1_on_off(y, p, config.ON_THRESHOLD_W.get(
                             a, config.DEFAULT_ON_THRESHOLD_W)),
                         tl_error=metrics.tl_error(y, p, step_s, config.TL_PER_KWH),
                         predict_ms=float("nan")))
    return pd.DataFrame(rows)


def sidebar(pred: pd.DataFrame, demo: bool, houses_only=None):
    """Ortak sol panel: modeller (birden fazla seçilebilir), ev, birim fiyat, seçili evin özeti.
    Giriş yapmış kullanıcı yalnızca kendi evini görür. -> (models, house, price)."""
    from panel import auth, theme
    all_models = model_order(pred["model"].unique())
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
                                 format_func=house_name, label_visibility="collapsed")
        else:
            house = houses[0]
        theme.side_label("Birim fiyat (TL/kWh)")
        price = st.number_input("Birim fiyat", 0.0, 50.0, float(config.TL_PER_KWH), 0.1, key="sb_price",
                                label_visibility="collapsed")
        bill = bill_table(pred, models[0], int(house), float(price), other=True, monthly=True)
        if not bill.empty:
            theme.side_card(house_name(house), f"{bill['Gerçek (TL)'].sum():,.0f}", "TL / ay",
                            f"{bill['Gerçek (kWh)'].sum():,.0f} kWh, aylık ortalama",
                            [(theme.color(a), v) for a, v in bill["Gerçek (TL)"].items()])
        if user:
            theme.side_user(user["name"], house_name(user.get("house")) if user.get("house") is not None else "Tüm evler")
            if st.button("Çıkış yap", key="sb_logout", icon=":material/logout:", width="stretch"):
                auth.logout()
                st.rerun()
    return models, int(house), float(price)


def one_model(models, key: str) -> str:
    """Tek modelli sayfalar için: birden fazla model seçiliyse sayfada küçük bir seçici çıkar."""
    if len(models) == 1:
        return models[0]
    default = next((m for m in PREFERRED if m in models), models[0])
    return st.segmented_control("Gösterilen model", models, default=default, key=key) or default


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


def _row(name, y, p, dt, price):
    return {"Cihaz": name,
            "Gerçek (kWh)": metrics.energy_kwh(y, dt), "Tahmin (kWh)": metrics.energy_kwh(p, dt),
            "Gerçek (TL)": metrics.bill_tl(y, dt, price), "Tahmin (TL)": metrics.bill_tl(p, dt, price),
            "Hata (TL)": metrics.tl_error(y, p, dt, price),
            "Gün": len(y) * dt / 86400}  # kayıtlı süre; boşluklar sayılmaz (aylık ölçek için)


def bill_from(sub: pd.DataFrame, dt: int, price: float, other: bool = False) -> pd.DataFrame:
    """Tek model ve tek evin satırlarından cihaz bazlı fatura tablosu.
    other=True: yalnızca bütün cihazların kaydı olan anlar alınır ve sayaç toplamından kalan enerji
    'other' (Diğer cihazlar) satırı olur; böylece satırlar sayaç faturasına eşit toplanır."""
    from panel import theme
    apps = theme.ordered(sub["appliance"].unique())
    if not other:
        rows = [_row(a, g["appliance_w"].to_numpy(), g["predicted_w"].to_numpy(), dt, price)
                for a in apps if not (g := sub[sub["appliance"] == a]).empty]
        return pd.DataFrame(rows).set_index("Cihaz") if rows else pd.DataFrame()
    w = sub.set_index(["timestamp", "appliance"])[["appliance_w", "predicted_w", "aggregate_w"]].unstack("appliance").dropna()
    if w.empty:
        return pd.DataFrame()
    y, p = w["appliance_w"], w["predicted_w"]
    agg = w["aggregate_w"].mean(axis=1).to_numpy()  # aynı sayaç; dakikalık ortalamalar cihaz dosyaları arasında çok az farklı olabilir
    rows = [_row(a, y[a].to_numpy(), p[a].to_numpy(), dt, price) for a in apps if a in y.columns]
    rows.append(_row("other", np.clip(agg - y.sum(axis=1).to_numpy(), 0, None),
                     np.clip(agg - p.sum(axis=1).to_numpy(), 0, None), dt, price))
    return pd.DataFrame(rows).set_index("Cihaz")


def to_month(bill: pd.DataFrame) -> pd.DataFrame:
    """Tutarları 30 günlük ortalamaya çevirir (her satır kendi kayıtlı süresine göre)."""
    if bill.empty:
        return bill
    out = bill.copy()
    k = 30.0 / out["Gün"].clip(lower=1.0)
    for c in out.columns:
        if c != "Gün":
            out[c] = out[c] * k
    out["Gün"] = 30.0
    return out


@st.cache_resource(max_entries=256)
def _bill(model: str, house: int, price: float, other: bool, monthly: bool) -> pd.DataFrame:
    pred = load()[0]
    dt = int(pred.attrs.get("dt", config.SAMPLE_PERIOD_S))
    b = bill_from(pred[(pred["model"] == model) & (pred["house"] == house)], dt, price, other)
    return to_month(b) if monthly else b


def bill_table(pred, model: str, house: int, price: float, other: bool = False, monthly: bool = False) -> pd.DataFrame:
    """Seçili model ve ev için cihaz bazlı kWh ve TL tablosu. Önbellekli.
    other: sayaçtan kalan 'Diğer cihazlar' satırı; monthly: 30 günlük ortalama."""
    return _bill(str(model), int(house), round(float(price), 6), bool(other), bool(monthly))


@st.cache_resource(max_entries=64)
def _facts(house: int, model: str, appliance: str, price: float) -> dict:
    from panel import insights
    w = _wide(house, appliance, (model,))
    return insights.usage_facts(w["timestamp"], w["m0"], appliance, price, dt=dt())


def usage_facts(house, model, appliance, price) -> dict:
    """Kullanım sayısı, bir kullanımın maliyeti, en yoğun saat, bekleme payı. Önbellekli."""
    return _facts(int(house), str(model), str(appliance), round(float(price), 6))
