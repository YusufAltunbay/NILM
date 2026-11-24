import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

import streamlit as st

from panel import charts, data, insights, savings, theme

pred, res, demo = data.load()
models, house, price = data.sidebar(pred, demo)
theme.page_header("Tasarruf senaryosu", chips=[f"Ev {house}", f"{price:.2f} TL/kWh"])
model = data.one_model(models, "model_tasarruf")
bill = data.bill_table(pred, model, house, price)
if bill.empty:
    st.error("Bu ev için veri yok.")
    st.stop()

first = bill.index[0]
w = data.wide(pred, house, first, [model])
days = savings.span_days(w["timestamp"])
m = savings.monthly(bill, days)
apps = list(bill.index)
K = lambda a: f"ts_cut_{a}"  # noqa: E731
for a in apps:
    st.session_state.setdefault(K(a), 0)


def set_all(pct: int):
    for a in apps:
        st.session_state[K(a)] = pct


def apply_preset():
    p = st.session_state.get("ts_preset")
    if p:
        for a, pct in savings.preset_cuts(apps, p).items():
            st.session_state[K(a)] = pct


def add_one(a, pct):
    st.session_state[K(a)] = pct


def apply_plan(plan):
    for a in apps:
        st.session_state[K(a)] = plan.get(a, 0)


@st.fragment
def scenario_view():
    left, right = st.columns([0.9, 1.9], gap="large")
    with left:
        theme.section("Senaryo")
        st.segmented_control("Hazır senaryo", list(savings.PRESETS), key="ts_preset", on_change=apply_preset,
                             label_visibility="collapsed")
        for a in theme.ordered(apps):
            st.slider(theme.demoji(a), 0, savings.MAX_CUT, step=savings.STEP, key=K(a), format="%d%%", help=f"Bu cihaz için gerçekçi azaltma: %{savings.tip_range(a)[0]}-{savings.tip_range(a)[1]}")
        st.button("Sıfırla", on_click=set_all, args=(0,), icon=":material/restart_alt:")
    cuts = {a: st.session_state[K(a)] for a in apps}
    sc = savings.scenario(m, cuts)
    saved, total = sc["Tasarruf TL"].sum(), sc["TL"].sum()
    with right:
        theme.section("Önce ve sonra")
        theme.strip([
            dict(lab="Aylık tasarruf", num=f"{saved:,.2f}", unit="TL", sub=f"{sc['Tasarruf kWh'].sum():,.1f} kWh", tone="ok" if saved > 0 else "", small=True),
            dict(lab="Yıllık tasarruf", num=f"{saved * 12:,.0f}", unit="TL", sub=f"%{saved / total * 100 if total else 0:.1f} düşüş", small=True),
            dict(lab="Yeni aylık fatura", num=f"{sc['Yeni TL'].sum():,.2f}", unit="TL", sub=f"Şimdi {total:,.2f} TL", small=True),
        ])
        before = m.rename(columns={"TL": "Tahmin (TL)"})
        after = sc[["Yeni TL"]].rename(columns={"Yeni TL": "Tahmin (TL)"})
        theme.legend(apps)
        st.altair_chart(charts.stacked_multi({"Şimdi": before, "Senaryo": after}), width="stretch")
    if saved > 0:
        theme.section("Cihaz cihaz tasarruf")
        st.altair_chart(charts.savings_bars(sc), width="stretch")


scenario_view()

theme.section("Hedefe göre plan")
t1, t2 = st.columns([1, 2], vertical_alignment="bottom")
with t1:
    target = st.number_input("Faturayı yüzde kaç düşürmek istiyorsun?", 1, 50, 10, step=1, key="ts_target")
plan, ok, potential = savings.plan_for_target(m, target)
total_tl = m["TL"].sum()
with t2:
    if plan:
        txt = ", ".join(f"{theme.tr(a)} %{p}" for a, p in plan.items())
        done = savings.scenario(m, plan)["Tasarruf TL"].sum()
        st.markdown(f"**Plan:** {txt}. Aylık yaklaşık **{done:,.2f} TL** tasarruf."
                    + ("" if ok else f" Gerçekçi toplam potansiyel ayda {potential:,.0f} TL (%{potential / total_tl * 100:.0f}), hedef bunun üstünde."))
        st.button("Planı senaryoya uygula", on_click=apply_plan, args=(plan,), icon=":material/check:")

theme.section("Öncelikli öneriler", "Kazancı en yüksek olandan başlar. Azaltma oranları tahminidir.")
sug = savings.suggestions(m)
if sug:
    best = sug[0]
    theme.callout(f"En büyük fırsat: <b>{theme.tr(best['appliance'])}</b>. Ayda tahminen <b>{best['low']:,.0f}-{best['high']:,.0f} TL</b> tasarruf mümkün.")
cols = st.columns(len(sug)) if sug else []
for n, (col, sg) in enumerate(zip(cols, sug), 1):
    a = sg["appliance"]
    facts = insights.describe(data.usage_facts(house, model, a, price))
    rows = [(k, v, False) for k, v in facts] + [("Faturadaki payı", f"%{sg['share']:.0f}", False)]
    with col:
        theme.cards([dict(color=theme.color(a), name=theme.tr(a), rank=n, first=n == 1, tag="önce bunu dene" if n == 1 else "",
                          big=f"{sg['low']:,.0f}-{sg['high']:,.0f}", unit="TL/ay", sub=sg["tip"], rows=rows)], min_h=330)
        st.button(f"Senaryoya ekle (%{sg['mid_pct']})", key=f"add_{a}", on_click=add_one, args=(a, sg["mid_pct"]),
                  icon=":material/add:", width="stretch")
