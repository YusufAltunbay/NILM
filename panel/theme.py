"""Panelin görünümü: renkler, CSS ve ortak bileşenler."""
import html

import pandas as pd
import streamlit as st

INK = "#0E1B2E"
MUTED = "#5B6B82"
LINE = "#DDE3EC"

# Cihaz -> (Türkçe ad, renk). Yeni cihaz eklenirse buraya da eklenir.
APPLIANCES = {
    "fridge": ("Buzdolabı", "#2F80ED"),
    "washing machine": ("Çamaşır makinesi", "#7C5CFC"),
    "kettle": ("Su ısıtıcısı", "#FF9F1C"),
    "dish washer": ("Bulaşık makinesi", "#12B5A6"),
    "microwave": ("Mikrodalga", "#F0507A"),
}
_FALLBACK = ["#64748B", "#A16207", "#0F766E", "#9D174D"]
MODEL_COLORS = ["#0E1B2E", "#12B5A6", "#7C5CFC", "#FF9F1C", "#F0507A", "#2F80ED"]


def tr(appliance: str) -> str:
    return APPLIANCES.get(appliance, (appliance.capitalize(), ""))[0]


def color(appliance: str) -> str:
    if appliance in APPLIANCES:
        return APPLIANCES[appliance][1]
    return _FALLBACK[hash(appliance) % len(_FALLBACK)]


def palette(appliances):
    """Altair ölçeği için (Türkçe adlar, renkler)."""
    return [tr(a) for a in appliances], [color(a) for a in appliances]


_CSS = f"""
<style>
@import url('https://fonts.googleapis.com/css2?family=Bricolage+Grotesque:opsz,wght@12..96,500;12..96,700&family=Figtree:wght@400;500;600&display=swap');
.stApp, [data-testid="stSidebar"] {{ font-family: 'Figtree', 'Segoe UI', system-ui, sans-serif; }}
.stApp h1, .stApp h2, .stApp h3, .nilm-title, .num {{ font-family: 'Bricolage Grotesque', 'Segoe UI', system-ui, sans-serif; }}
.block-container {{ padding-top: 2.4rem; padding-bottom: 3rem; max-width: 1200px; }}
header[data-testid="stHeader"] {{ background: transparent; }}
.stDeployButton, [data-testid="stAppDeployButton"], [data-testid="stToolbar"], #MainMenu, footer {{ display: none !important; }}

.nilm-title {{ font-size: 2.3rem; font-weight: 700; letter-spacing: -0.02em; color: {INK}; margin: 0 0 .15rem 0; line-height: 1.15; }}
.nilm-sub {{ color: {MUTED}; max-width: 64ch; margin: 0 0 .9rem 0; font-size: 1.02rem; line-height: 1.55; }}
.chip {{ display: inline-block; padding: 3px 11px; border-radius: 999px; background: #E3EAF4; color: #27405F;
         font-size: .82rem; font-weight: 500; margin: 0 6px 6px 0; }}
.chip.demo {{ background: #FFF1D6; color: #8A5200; }}

.sec {{ font-family: 'Bricolage Grotesque', 'Segoe UI', sans-serif; font-size: 1.22rem; font-weight: 700; color: {INK};
        margin: 1.9rem 0 .15rem 0; letter-spacing: -0.01em; }}
.sec-note {{ color: {MUTED}; font-size: .92rem; margin: 0 0 .6rem 0; max-width: 70ch; }}

.strip {{ display: flex; flex-wrap: wrap; background: #fff; border: 1px solid {LINE}; border-radius: 8px; margin: 1.1rem 0 .4rem 0; }}
.strip .cell {{ flex: 1 1 220px; padding: 18px 26px; border-right: 1px solid {LINE}; }}
.strip .cell:last-child {{ border-right: none; }}
.strip .lab {{ font-size: .88rem; color: {MUTED}; margin-bottom: 2px; }}
.strip .num {{ font-size: 2.5rem; font-weight: 700; line-height: 1.1; color: {INK}; font-variant-numeric: tabular-nums; letter-spacing: -0.02em; }}
.strip .num small {{ font-family: 'Figtree', 'Segoe UI', sans-serif; font-size: 1rem; font-weight: 500; color: {MUTED}; margin-left: 6px; letter-spacing: 0; }}
.strip .sub {{ font-size: .88rem; color: {MUTED}; margin-top: 2px; }}
.over {{ color: #B45309 !important; }} .under {{ color: #1D4ED8 !important; }} .ok {{ color: #0F766E !important; }}

.legend {{ display: flex; flex-wrap: wrap; gap: 6px 18px; margin: .2rem 0 .3rem 0; font-size: .9rem; color: #27405F; }}
.legend i {{ display: inline-block; width: 11px; height: 11px; border-radius: 3px; margin-right: 7px; vertical-align: -1px; }}

table.ledger {{ width: 100%; border-collapse: collapse; background: #fff; border: 1px solid {LINE}; border-radius: 8px; overflow: hidden; font-variant-numeric: tabular-nums; }}
.ledger th {{ text-align: right; font-weight: 500; font-size: .86rem; color: {MUTED}; padding: 11px 16px; border-bottom: 1px solid {LINE}; background: #FAFBFD; }}
.ledger th:first-child, .ledger td:first-child {{ text-align: left; }}
.ledger td {{ text-align: right; padding: 12px 16px; border-bottom: 1px solid #EEF2F7; color: {INK}; font-size: .97rem; }}
.ledger tr:last-child td {{ border-bottom: none; }}
.ledger tfoot td {{ font-weight: 600; background: #FAFBFD; border-top: 1px solid {LINE}; }}
.ledger .dot {{ display: inline-block; width: 11px; height: 11px; border-radius: 3px; margin-right: 10px; vertical-align: -1px; }}
.ledger .errbar {{ display: inline-block; height: 7px; border-radius: 4px; background: #CBD5E3; margin-right: 10px; vertical-align: middle; }}

[data-testid="stSidebar"] {{ border-right: none; }}
[data-testid="stSidebar"] h2, [data-testid="stSidebar"] h3 {{ font-family: 'Bricolage Grotesque', sans-serif; font-weight: 600; font-size: 1.05rem; }}
.side-foot {{ color: #8FA3BF; font-size: .8rem; line-height: 1.5; margin-top: 2rem; padding-top: .9rem; border-top: 1px solid #243752; }}
.demo-note {{ background: #2A2411; color: #FFD58A; font-size: .84rem; line-height: 1.45; padding: 9px 12px; border-radius: 6px; margin: 0 0 1rem 0; }}

[data-testid="stVegaLiteChart"], [data-testid="stArrowVegaLiteChart"] {{ background: #fff; border: 1px solid {LINE}; border-radius: 8px; padding: 14px 10px 6px 10px; overflow: hidden; }}
[data-testid="stDataFrame"] {{ border: 1px solid {LINE}; border-radius: 8px; overflow: hidden; }}
@media (max-width: 720px) {{ .nilm-title {{ font-size: 1.7rem; }} .strip .num {{ font-size: 2rem; }} }}
</style>
"""


def page_header(title: str, sub: str = "", chips=(), demo: bool = False):
    chip_html = "".join(f'<span class="chip">{html.escape(c)}</span>' for c in chips)
    if demo:
        chip_html += '<span class="chip demo">Demo verisi</span>'
    st.markdown(_CSS + f'<h1 class="nilm-title">{html.escape(title)}</h1>'
                f'<p class="nilm-sub">{html.escape(sub)}</p><div>{chip_html}</div>',
                unsafe_allow_html=True)


def section(title: str, note: str = ""):
    note_html = f'<p class="sec-note">{html.escape(note)}</p>' if note else ""
    st.markdown(f'<div class="sec">{html.escape(title)}</div>{note_html}', unsafe_allow_html=True)


def legend(appliances):
    items = "".join(f'<span><i style="background:{color(a)}"></i>{html.escape(tr(a))}</span>' for a in appliances)
    st.markdown(f'<div class="legend">{items}</div>', unsafe_allow_html=True)


def bill_strip(real_tl, pred_tl, real_kwh, pred_kwh):
    diff = pred_tl - real_tl
    pct = (diff / real_tl * 100) if real_tl else 0.0
    tone = "ok" if abs(pct) < 5 else ("over" if diff > 0 else "under")
    word = "fazla tahmin" if diff > 0 else "eksik tahmin"
    st.markdown(f"""
<div class="strip">
  <div class="cell"><div class="lab">Gerçek fatura</div><div class="num">{real_tl:,.2f}<small>TL</small></div><div class="sub">{real_kwh:,.2f} kWh</div></div>
  <div class="cell"><div class="lab">Tahmin edilen fatura</div><div class="num">{pred_tl:,.2f}<small>TL</small></div><div class="sub">{pred_kwh:,.2f} kWh</div></div>
  <div class="cell"><div class="lab">Fark</div><div class="num {tone}">{diff:+,.2f}<small>TL</small></div><div class="sub">%{abs(pct):.1f} {word}</div></div>
</div>""", unsafe_allow_html=True)


def ledger(bill: pd.DataFrame):
    """Makbuz tarzı fatura kalemleri tablosu. bill: index=cihaz, bill_table sütunları."""
    peak = max(bill["Hata (TL)"].max(), 1e-9)
    rows = ""
    for a, r in bill.iterrows():
        w = max(2, int(r["Hata (TL)"] / peak * 60))
        rows += (f'<tr><td><span class="dot" style="background:{color(a)}"></span>{html.escape(tr(a))}</td>'
                 f'<td>{r["Gerçek (kWh)"]:,.2f}</td><td>{r["Gerçek (TL)"]:,.2f}</td><td>{r["Tahmin (TL)"]:,.2f}</td>'
                 f'<td><span class="errbar" style="width:{w}px"></span>{r["Hata (TL)"]:,.2f}</td></tr>')
    t = bill.sum(numeric_only=True)
    foot = (f'<tr><td>Toplam</td><td>{t["Gerçek (kWh)"]:,.2f}</td><td>{t["Gerçek (TL)"]:,.2f}</td>'
            f'<td>{t["Tahmin (TL)"]:,.2f}</td><td>{t["Hata (TL)"]:,.2f}</td></tr>')
    st.markdown(f"""
<table class="ledger"><thead><tr><th>Cihaz</th><th>Gerçek tüketim (kWh)</th><th>Gerçek (TL)</th><th>Tahmin (TL)</th><th>Mutlak hata (TL)</th></tr></thead>
<tbody>{rows}</tbody><tfoot>{foot}</tfoot></table>""", unsafe_allow_html=True)


def sidebar_footer():
    st.markdown('<div class="side-foot">Veri: UK-DALE<br>Disiplinler arası proje<br>Yusuf, Ersin, Kamil</div>',
                unsafe_allow_html=True)


def demo_note():
    st.markdown('<div class="demo-note">Sahte demo verisi gösteriliyor. Gerçek sonuçlar için '
                '<b>python -m scripts.run_eval --data ...</b> çalıştırın.</div>', unsafe_allow_html=True)
