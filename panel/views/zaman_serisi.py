import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

import pandas as pd
import streamlit as st

from panel import blocks, charts, data, theme

pred, res, demo = data.load()
models, house, price = data.sidebar(pred, demo)
sub = pred[(pred["house"] == house) & pred["model"].isin(models)]

theme.page_header("Gerçek ve tahmin", chips=[f"Ev {house}", f"{len(models)} model"])
if sub.empty:
    st.error("Bu ev için veri yok.")
    st.stop()

devs = [a for a in theme.APPLIANCES if a in set(sub["appliance"].unique())] or sorted(sub["appliance"].unique())
WINDOWS = {"1 saat": pd.Timedelta(hours=1), "6 saat": pd.Timedelta(hours=6), "1 gün": pd.Timedelta(days=1),
           "3 gün": pd.Timedelta(days=3), "Tümü": None}


@st.fragment
def panel_body():
    """Bu bölümdeki bir ayar değişince yalnızca burası yenilenir (sayfanın geri kalanı yeniden hesaplanmaz)."""
    chosen = st.pills("Cihazlar", devs, selection_mode="multi", default=devs[:1], format_func=theme.demoji,
                      key="zs_devs", label_visibility="collapsed") or devs[:1]
    chosen = [d for d in devs if d in chosen]
    single = len(chosen) == 1
    ref = sub[sub["appliance"].isin(chosen)]
    lo, hi = ref["timestamp"].min().to_pydatetime(), ref["timestamp"].max().to_pydatetime()
    total = hi - lo

    d1, d2, d3 = st.columns([2.2, 3, 1.1], vertical_alignment="bottom")
    with d1:
        wname = st.segmented_control("Pencere", list(WINDOWS), default="6 saat", key="zs_win") or "6 saat"
    with d3:
        with st.popover("Ayarlar", icon=":material/tune:", width="stretch"):
            smooth = st.select_slider("Yumuşatma", list(blocks.SMOOTH), value="Orta")
            show_agg = st.toggle("Toplam gücü göster", value=False)
            show_on = st.toggle("AÇIK dönemleri işaretle", value=False)
            show_err = st.toggle("Hata grafiği", value=False)
    win = WINDOWS[wname]
    if win is None or win >= total:
        start, end = lo, hi
    else:
        best = data.busiest(house, chosen[0], models, win)
        best = min(max(best, lo), hi - win.to_pytimedelta())
        with d2:
            start = st.slider("Başlangıç", lo, hi - win.to_pytimedelta(), best, format="DD.MM HH:mm",
                              key=f"zs_start_{'-'.join(chosen)}_{wname}_{house}")
        end = start + win.to_pytimedelta()

    if single:
        dev = chosen[0]
        wfull = data.wide(pred, house, dev, models)
        g = blocks.compare_view(wfull, dev, models, start, end, price, smooth, show_agg, show_on, show_err)
        st.altair_chart(charts.overview(data.minimap(house, dev, models), dev, start, end), width="stretch")
        if g is not None:
            out = g.rename(columns={f"m{i}": m for i, m in enumerate(models)})
            st.download_button("Bu aralığı indir (CSV)", out.to_csv(index=False).encode("utf-8-sig"),
                               file_name=f"zaman_serisi_ev{house}_{dev.replace(' ', '_')}.csv", mime="text/csv")
        return
    theme.model_legend(models)
    frames, tiles = {}, []
    for a in chosen:
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
                              sub=f"{stt['real']['tl']:,.2f} TL",
                              rows=[("En yakın model", bm, False), ("MAE", f"{stt['models'][bm]['mae']:,.1f} W", False)]))
    if frames:
        theme.cards(tiles)
        st.altair_chart(charts.facets(frames, models), width="stretch")
    else:
        st.info("Bu aralıkta veri yok.")


panel_body()
