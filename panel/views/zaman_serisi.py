import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

import pandas as pd
import streamlit as st

from nilm import config
from panel import blocks, charts, data, theme

pred, res, demo = data.load()
models, house, price = data.sidebar(pred, demo)
sub = pred[(pred["house"] == house) & pred["model"].isin(models)]

theme.page_header("Gerçek ve tahmin edilen güç",
                  "Renkli alan cihazın gerçek gücü, çizgiler seçili modellerin tahmini. Tüm modeller aynı grafikte üst üste, farkı gözle görebilirsiniz.",
                  chips=[f"Ev {house}", f"{len(models)} model"], demo=demo)
if sub.empty:
    st.error("Bu ev için veri yok. Sol panelden başka bir seçim yapın.")
    st.stop()

devs = [a for a in theme.APPLIANCES if a in set(sub["appliance"])] or sorted(sub["appliance"].unique())
mode = st.segmented_control("Görünüm", ["Cihaz detayı", "Tüm cihazlar"], default="Cihaz detayı", key="zs_mode",
                            label_visibility="collapsed") or "Cihaz detayı"
dev = devs[0]
if mode == "Cihaz detayı":
    dev = st.pills("Cihaz", devs, default=devs[0], format_func=theme.demoji, key="zs_dev", label_visibility="collapsed") or devs[0]

# zaman ekseni
ref = sub[sub["appliance"] == dev] if mode == "Cihaz detayı" else sub
lo, hi = ref["timestamp"].min().to_pydatetime(), ref["timestamp"].max().to_pydatetime()
total = hi - lo
WINDOWS = {"1 saat": pd.Timedelta(hours=1), "6 saat": pd.Timedelta(hours=6), "1 gün": pd.Timedelta(days=1),
           "3 gün": pd.Timedelta(days=3), "Tümü": None}
d1, d2, d3 = st.columns([2.2, 3, 1.1], vertical_alignment="bottom")
with d1:
    wname = st.segmented_control("Pencere", list(WINDOWS), default="6 saat", key="zs_win") or "6 saat"
with d3:
    with st.popover("Ayarlar", icon=":material/tune:", width="stretch"):
        smooth = st.select_slider("Yumuşatma", list(blocks.SMOOTH), value="Orta",
                                  help="Yalnızca grafiği sadeleştirir; kartlardaki ölçütler ham veriden hesaplanır.")
        show_agg = st.toggle("Toplam gücü göster", value=False)
        show_on = st.toggle("AÇIK dönemleri işaretle", value=False)
        show_err = st.toggle("Hata grafiği", value=False)
win = WINDOWS[wname]
if win is None or win >= total:
    start, end = lo, hi
else:
    if mode == "Cihaz detayı":
        w0 = wfull = data.wide(pred, house, dev, models)
        best = data.busiest_start(w0["timestamp"], w0["Gerçek"], win)
    else:
        tot = sub[sub["model"] == models[0]].groupby("timestamp")["appliance_w"].sum().reset_index()
        best = data.busiest_start(tot["timestamp"], tot["appliance_w"], win)
    best = min(max(best, lo), hi - win.to_pytimedelta())
    with d2:
        start = st.slider("Başlangıç (varsayılan: en hareketli an)", lo, hi - win.to_pytimedelta(), best,
                          format="DD.MM HH:mm", key=f"zs_start_{mode}_{dev}_{wname}_{house}")
    end = start + win.to_pytimedelta()

if mode == "Cihaz detayı":
    if "wfull" not in dir():
        wfull = data.wide(pred, house, dev, models)
    g = blocks.compare_view(wfull, dev, models, start, end, price, smooth, show_agg, show_on, show_err)
    mini = wfull.set_index("timestamp")["Gerçek"].resample("10min").mean().reset_index()
    st.caption("Tüm kayıt (renkli kutu: şu an baktığınız pencere)")
    st.altair_chart(charts.overview(mini, dev, start, end), width="stretch")
    if g is not None:
        out = g.rename(columns={f"m{i}": m for i, m in enumerate(models)})
        st.download_button("Bu aralığı indir (CSV)", out.to_csv(index=False).encode("utf-8-sig"),
                           file_name=f"zaman_serisi_ev{house}_{dev.replace(' ', '_')}.csv", mime="text/csv")
else:
    theme.model_legend(models, real_color="#94A3B8", real_label="Gerçek (renkli alan)")
    frames, tiles = {}, []
    for a in devs:
        wf = data.wide(pred, house, a, models)
        g = wf[(wf["timestamp"] >= start) & (wf["timestamp"] <= end)]
        if g.empty:
            continue
        view, _ = blocks.smooth_view(g, models, smooth, max_points=900)
        frames[a] = view
        stt = blocks.window_stats(g, a, models, price)
        if stt["models"]:
            bm = min(stt["models"], key=lambda m: stt["models"][m]["mae"])
            tiles.append(dict(color=theme.color(a), name=theme.tr(a), big=f"{stt['real']['kwh']:,.3f}", unit="kWh",
                              sub=f"{stt['real']['tl']:,.2f} TL gerçek",
                              rows=[("En yakın model", bm, False), ("Onun hatası (MAE)", f"{stt['models'][bm]['mae']:,.1f} W", False)]))
    if frames:
        theme.cards(tiles)
        st.altair_chart(charts.facets(frames, models), width="stretch")
        st.caption("Her cihazın ekseni kendi ölçeğindedir. Kartlar, seçili pencere içinde en düşük ortalama hataya sahip modeli gösterir.")
    else:
        st.info("Bu aralıkta veri yok.")
