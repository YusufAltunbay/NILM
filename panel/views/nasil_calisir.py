import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

import html

import numpy as np
import pandas as pd
import streamlit as st

from nilm import config
from panel import charts, data, theme

pred, res, demo = data.load()
models, house, price = data.sidebar(pred, demo)
theme.page_header("Nasıl çalışır", "Evin tek sayacından ölçülen toplam tüketim, cihaz cihaz faturaya dönüşür.",
                  chips=[data.house_name(house)])

model = next((m for m in data.PREFERRED if m in models), models[0])
sub = pred[(pred["house"] == house) & (pred["model"] == model)]
apps = theme.ordered(sub["appliance"].unique())
bill = data.bill_table(pred, model, house, price, other=True, monthly=True)


# ---- 1. akış: dört adım (gerçek bir sıra olduğu için numaralı) ----
def _spark(values, w=220, h=54):
    v = np.asarray(values, dtype=float)
    v = (v - v.min()) / max(v.max() - v.min(), 1e-9)
    xs = np.linspace(0, w, len(v))
    pts = " ".join(f"{x:.1f},{h - 4 - y * (h - 8):.1f}" for x, y in zip(xs, v))
    return (f'<svg viewBox="0 0 {w} {h}" preserveAspectRatio="none"><polyline points="{pts}" fill="none" '
            f'stroke="#E8EEF6" stroke-width="1.6" stroke-linejoin="round"/></svg>')


one = sub[sub["appliance"] == apps[0]].sort_values("timestamp")
day0 = one["timestamp"].iloc[len(one) // 2].floor("D")
agg_day = one[(one["timestamp"] >= day0) & (one["timestamp"] < day0 + pd.Timedelta(days=1))]
agg_s = agg_day.set_index("timestamp")["aggregate_w"].resample("10min").mean().dropna()
dev = bill.drop(index="other", errors="ignore")
stack = "".join(f'<i style="background:{theme.color(a)};height:{max(6, v / max(bill["Tahmin (TL)"].max(), 1e-9) * 100):.0f}%"></i>'
                for a, v in bill["Tahmin (TL)"].items())
steps = [
    ("Sayaç", "Evin girişindeki tek sayaç toplam gücü ölçer.", f"{config.SAMPLE_PERIOD_S} saniyede bir ölçüm",
     f'<div class="hw-spark">{_spark(agg_s.to_numpy() if len(agg_s) > 3 else [0, 1, 0])}</div>'),
    ("Model", "Toplam güç penceresine bakıp her cihazın o anki gücünü tahmin eder.", f"{pred['model'].nunique()} model karşılaştırıldı",
     '<div class="hw-model">' + "".join(f'<span style="--d:{k * .12:.2f}s"></span>' for k in range(12)) + '</div>'),
    ("Cihazlar", "Toplam, cihazlara ayrılır; ayrılamayan kısım 'Diğer cihazlar' olur.", f"{len(dev)} cihaz + diğerleri",
     f'<div class="hw-stack">{stack}</div>'),
    ("Fatura", "Her cihazın enerjisi birim fiyatla çarpılır.", f"{price:.2f} TL/kWh",
     f'<div class="hw-bill"><b>{bill["Gerçek (TL)"].sum():,.0f}</b><small>TL / ay</small></div>'),
]
flow = "".join(f'<div class="hw-step" style="--d:{k * .14:.2f}s"><div class="hw-n">{k + 1}</div><div class="hw-vis">{vis}</div>'
               f'<div class="hw-t">{html.escape(t)}</div><div class="hw-x">{html.escape(x)}</div><div class="hw-f">{html.escape(f)}</div></div>'
               for k, (t, x, f, vis) in enumerate(steps))
st.markdown(f'<div class="hw-flow">{flow}</div>', unsafe_allow_html=True)

# ---- 2. bir günü ayıralım ----
theme.section("Bir günü ayıralım", "Üstte sayacın gördüğü tek çizgi, altta aynı günün cihazlara ayrılmış hali.")


@st.cache_resource(max_entries=16)
def _day(house: int, model: str):
    p = data.load()[0]
    s = p[(p["house"] == house) & (p["model"] == model)]
    w = s.set_index(["timestamp", "appliance"])[["appliance_w", "predicted_w", "aggregate_w"]].unstack("appliance").dropna()
    if w.empty:
        return None
    daily = w["appliance_w"].sum(axis=1).groupby(w.index.floor("D")).agg(["sum", "count"])
    daily = daily[daily["count"] >= daily["count"].max() * 0.95]          # tam kayıtlı günler
    day = daily["sum"].idxmax()                                           # cihazların en çok çalıştığı gün
    d = w[(w.index >= day) & (w.index < day + pd.Timedelta(days=1))].resample("5min").mean().dropna()
    return day, d


got = _day(int(house), model)
if got:
    day, d = got
    c1, c2 = st.columns([2, 3], vertical_alignment="center")
    with c1:
        src = st.segmented_control("Ayrım", ["Gerçek ölçüm", f"{model} tahmini"], default="Gerçek ölçüm", key="hw_src",
                                   label_visibility="collapsed") or "Gerçek ölçüm"
    with c2:
        st.markdown(f'<div class="hw-day">{day:%d.%m.%Y}, cihazların en yoğun çalıştığı tam gün</div>', unsafe_allow_html=True)
    col = "appliance_w" if src == "Gerçek ölçüm" else "predicted_w"
    agg = d["aggregate_w"].mean(axis=1)
    parts = d[col].copy()
    parts["other"] = (agg - parts.sum(axis=1)).clip(lower=0)
    long = parts.reset_index().melt(id_vars="timestamp", var_name="Cihaz", value_name="W")
    theme.legend(theme.ordered(long["Cihaz"].unique()))
    st.altair_chart(charts.day_split(pd.DataFrame({"timestamp": agg.index, "W": agg.to_numpy()}), long), width="stretch")

# ---- 3. modeller ----
theme.section("Dört model", "Basitten karmaşığa; hepsi aynı veriyle eğitildi ve aynı evde ölçüldü.")
DESC = {
    "Ortalama modeli": ("Hep aynı değeri söyler", "Cihazın eğitimdeki ortalama gücünü her an tahmin eder. Diğerlerinin geçmesi gereken çıta."),
    "Eşik modeli": ("Kural tabanlı", "Toplam güç belirli bir eşiği aşınca cihazı açık sayar."),
    "seq2point (CNN)": ("Evrişimli sinir ağı", "Toplam gücün bir penceresine bakar, pencerenin ortasındaki anı tahmin eder."),
    "BERT4NILM (Transformer)": ("Dikkat mekanizması", "Pencerenin tamamındaki ilişkileri birlikte değerlendirir."),
}
r = res[res["dataset"].str.contains(rf"house{house}\(")]
items = []
for m in data.model_order(pred["model"].unique()):
    kind, text = DESC.get(m, ("Model", ""))
    rm = r[r["model"] == m]
    rows = [("Ortalama hata (MAE)", f"{rm['mae'].mean():.1f} W", False), ("Fatura hatası", f"{rm['tl_error'].mean():.1f} TL", False)] if not rm.empty else []
    items.append(dict(color=theme.mcolor(m), name=m, tag=kind, sub=text, big=" ", rows=rows))
theme.cards(items, min_h=210)

# ---- 4. veri ----
theme.section("Veri", "UK-DALE: İngiltere'de 5 evin elektrik tüketimi, toplam ve cihaz cihaz.")
roles = [(h, "Eğitim", "Model bu evlerden öğrendi.") for h in config.TRAIN_HOUSES]
roles += [(h, "Doğrulama", "Ayarlar bu eve bakılarak seçildi.") for h in getattr(config, "VAL_HOUSES", [])]
roles += [(h, "Görülmeyen", "Model bu evi hiç görmedi; asıl sınav.") for h in config.UNSEEN_HOUSES]
have = set(int(h) for h in pred["house"].unique())
tiles = "".join(f'<div class="hw-house {"on" if h in have else ""} {k.lower()}"><b>Ev {h}</b><span>{k}</span><small>{html.escape(t)}</small></div>'
                for h, k, t in sorted(roles))
span = sub["timestamp"]
st.markdown(f'<div class="hw-houses">{tiles}</div>'
            f'<div class="hw-note">Panelde sonuçları gösterilen evler vurgulu. Ev {house} kaydı {span.min():%m.%Y} ile {span.max():%m.%Y} arası.</div>',
            unsafe_allow_html=True)
