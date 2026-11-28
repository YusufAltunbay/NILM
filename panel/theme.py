"""Panelin görünümü: renkler, CSS ve ortak bileşenler."""
import html
import zlib

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
_FALLBACK = ["#64748B", "#A16207", "#0F766E", "#9D174D", "#4F46E5", "#BE185D", "#15803D", "#B45309"]
# Model renkleri cihaz renklerinden (mavi, mor, turuncu, turkuaz, pembe) ayrışsın diye ayrı bir set.
MODEL_COLORS = ["#E11D48", "#16A34A", "#0891B2", "#CA8A04", "#9333EA", "#0E1B2E"]
EMOJI = {"fridge": "\U0001F7E6", "washing machine": "\U0001F7EA", "kettle": "\U0001F7E7",
         "dish washer": "\U0001F7E9", "microwave": "\U0001F7E5"}
_MODELS: list = []


def register_models(models):
    """Tüm sayfalarda aynı modelin aynı rengi alması için model listesini bir kez kaydeder."""
    _MODELS[:] = sorted(models)


def mcolor(model: str) -> str:
    i = _MODELS.index(model) if model in _MODELS else zlib.crc32(model.encode())
    return MODEL_COLORS[i % len(MODEL_COLORS)]


def demoji(appliance: str) -> str:
    return f"{EMOJI.get(appliance, chr(0x2B1C))} {tr(appliance)}"


def tr(appliance: str) -> str:
    return APPLIANCES.get(appliance, (appliance.capitalize(), ""))[0]


def ordered(appliances):
    """Bilinen cihazlar tanımlı sırayla, yeni gelenler (veride olup burada tanımsız) alfabetik sırayla sonda."""
    present = set(appliances)
    return [a for a in APPLIANCES if a in present] + sorted(a for a in present if a not in APPLIANCES)


def color(appliance: str) -> str:
    if appliance in APPLIANCES:
        return APPLIANCES[appliance][1]
    return _FALLBACK[zlib.crc32(appliance.encode()) % len(_FALLBACK)]


def palette(appliances):
    """Altair ölçeği için (Türkçe adlar, renkler)."""
    return [tr(a) for a in appliances], [color(a) for a in appliances]


_CSS = f"""
<style>
.stApp, [data-testid="stSidebar"] {{ font-family: 'Segoe UI Variable Text', 'Segoe UI', system-ui, sans-serif; }}
.stApp h1, .stApp h2, .stApp h3, .nilm-title, .num {{ font-family: 'Segoe UI Variable Display', 'Segoe UI', system-ui, sans-serif; }}
.block-container {{ padding-top: 2.4rem; padding-bottom: 3rem; max-width: 1200px; }}
header[data-testid="stHeader"] {{ background: transparent; }}
.stDeployButton, [data-testid="stAppDeployButton"], [data-testid="stToolbarActions"], [data-testid="stMainMenu"], #MainMenu, footer {{ display: none !important; }}

.nilm-title {{ font-size: 2.3rem; font-weight: 700; letter-spacing: -0.02em; color: {INK}; margin: 0 0 .15rem 0; line-height: 1.15; }}
.nilm-sub {{ color: {MUTED}; max-width: 64ch; margin: 0 0 .9rem 0; font-size: 1.02rem; line-height: 1.55; }}
.chip {{ display: inline-block; padding: 3px 11px; border-radius: 999px; background: #E3EAF4; color: #27405F;
         font-size: .82rem; font-weight: 500; margin: 0 6px 6px 0; }}
.chip.demo {{ background: #FFF1D6; color: #8A5200; }}

.sec {{ font-family: 'Segoe UI Variable Display', 'Segoe UI', sans-serif; font-size: 1.22rem; font-weight: 700; color: {INK};
        margin: 1.9rem 0 .15rem 0; letter-spacing: -0.01em; }}
.sec-note {{ color: {MUTED}; font-size: .92rem; margin: 0 0 .6rem 0; max-width: 70ch; }}

.strip {{ display: flex; flex-wrap: wrap; background: #fff; border: 1px solid {LINE}; border-radius: 8px; margin: 1.1rem 0 .4rem 0; }}
.strip .cell {{ flex: 1 1 170px; padding: 18px 26px; border-right: 1px solid {LINE}; }}
.strip .cell:last-child {{ border-right: none; }}
.strip .lab {{ font-size: .88rem; color: {MUTED}; margin-bottom: 2px; }}
.strip .num {{ font-size: 2.5rem; font-weight: 700; line-height: 1.1; color: {INK}; font-variant-numeric: tabular-nums; letter-spacing: -0.02em; }}
.strip .num small {{ font-family: 'Segoe UI Variable Text', 'Segoe UI', sans-serif; font-size: 1rem; font-weight: 500; color: {MUTED}; margin-left: 6px; letter-spacing: 0; }}
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
[data-testid="stSidebar"] h2, [data-testid="stSidebar"] h3 {{ font-family: 'Segoe UI Variable Display', 'Segoe UI', sans-serif; font-weight: 600; font-size: 1.05rem; }}
.side-foot {{ color: #8FA3BF; font-size: .8rem; line-height: 1.5; margin-top: 2rem; padding-top: .9rem; border-top: 1px solid #243752; }}
.demo-note {{ background: #2A2411; color: #FFD58A; font-size: .84rem; line-height: 1.45; padding: 9px 12px; border-radius: 6px; margin: 0 0 1rem 0; }}

[data-testid="stVegaLiteChart"], [data-testid="stArrowVegaLiteChart"] {{ background: #fff; border: 1px solid {LINE}; border-radius: 8px; padding: 14px 10px 6px 10px; overflow: hidden; }}
[data-testid="stDataFrame"] {{ border: 1px solid {LINE}; border-radius: 8px; overflow: hidden; }}
img[data-testid="stSidebarLogo"] {{ height: 54px !important; width: auto !important; max-width: 100% !important; }}
[data-testid="stSidebarHeader"] {{ height: auto !important; padding: 1.4rem 1rem .6rem 1.1rem !important; }}
.callout {{ border-left: 3px solid #12B5A6; background: #fff; padding: 12px 18px; color: #27405F; margin: .9rem 0 .2rem 0; max-width: 84ch; line-height: 1.55; }}
.callout b {{ color: {INK}; font-weight: 600; }}
.ledger .share {{ display: inline-block; height: 7px; border-radius: 4px; margin-right: 8px; vertical-align: middle; }}
.strip .num.sm {{ font-size: 1.9rem; }}

/* ---- sol panel ---- */
[data-testid="stSidebar"] {{ background: linear-gradient(185deg, #0E1B2E 0%, #0F2A42 55%, #0B3B45 100%) !important; }}
[data-testid="stSidebarNavLink"] {{ border-radius: 10px !important; margin: 2px 0 !important; padding: .55rem .8rem !important; transition: background .15s; }}
[data-testid="stSidebarNavLink"]:hover {{ background: rgba(255,255,255,.08) !important; }}
[data-testid="stSidebarNavLink"][aria-current="page"] {{ background: linear-gradient(90deg, rgba(18,181,166,.34), rgba(18,181,166,.06)) !important;
        box-shadow: inset 3px 0 0 #12B5A6; font-weight: 600; }}
[data-testid="stSidebar"] [data-baseweb="tag"] {{ background: #12B5A6 !important; border-radius: 999px !important; color: #fff !important; }}
[data-testid="stSidebar"] [data-baseweb="tag"] span {{ color: #fff !important; }}
[data-testid="stSidebar"] [data-baseweb="select"] > div, [data-testid="stSidebar"] [data-testid="stNumberInputContainer"] {{ border-radius: 10px !important; }}
.side-label {{ color: #8FA3BF; font-size: .82rem; margin: 1.05rem 0 .15rem 0; font-weight: 500; }}
.sidecard {{ background: rgba(255,255,255,.06); border: 1px solid rgba(255,255,255,.10); border-radius: 14px; padding: 14px 15px 13px 15px; margin: 1.1rem 0 .4rem 0; }}
.sidecard .t {{ color: #8FA3BF; font-size: .8rem; }}
.sidecard .v {{ font-family: 'Segoe UI Variable Display', 'Segoe UI', sans-serif; color: #fff; font-size: 1.75rem; font-weight: 700; line-height: 1.15; }}
.sidecard .v small {{ font-size: .85rem; font-weight: 500; color: #8FA3BF; margin-left: 4px; font-family: 'Segoe UI Variable Text', 'Segoe UI', sans-serif; }}
.sidecard .s {{ color: #B9C7DA; font-size: .8rem; margin-top: 1px; }}
.sidecard .bar {{ display: flex; height: 9px; border-radius: 6px; overflow: hidden; margin-top: 11px; gap: 2px; }}
.sidecard .bar i {{ display: block; height: 100%; }}
.sidepill {{ display: inline-block; background: rgba(255,255,255,.08); color: #D5E0EE; border-radius: 999px; padding: 2px 10px; font-size: .78rem; margin: 0 5px 5px 0; }}
/* kapalı panelin açma düğmesi: görünür, turkuaz */
[data-testid="stExpandSidebarButton"], [data-testid="stSidebarCollapsedControl"] button {{ background: #12B5A6 !important; color: #fff !important; border-radius: 12px !important;
        box-shadow: 0 6px 18px -6px rgba(18,181,166,.7); }}
[data-testid="stExpandSidebarButton"] svg, [data-testid="stSidebarCollapsedControl"] svg {{ color: #fff !important; fill: #fff !important; }}
[data-testid="stSidebarCollapseButton"] button {{ color: #B9C7DA !important; }}


[data-testid="stSidebar"] [data-testid="stButtonGroup"] button {{ border-radius: 999px !important; background: rgba(255,255,255,.06) !important;
        border: 1px solid rgba(255,255,255,.16) !important; color: #D5E0EE !important; padding: 4px 12px !important; transition: all .15s; }}
[data-testid="stSidebar"] [data-testid="stButtonGroup"] button:hover {{ background: rgba(255,255,255,.12) !important; }}
[data-testid="stSidebar"] [data-testid="stButtonGroup"] button[aria-checked="true"], [data-testid="stSidebar"] [data-testid="stButtonGroup"] button[kind="pillsActive"] {{
        background: rgba(18,181,166,.28) !important; border-color: #12B5A6 !important; color: #fff !important; font-weight: 600; }}
.sideuser {{ display: flex; align-items: center; gap: 11px; margin: 1.2rem 0 .5rem 0; color: #E6ECF5; font-size: .92rem; line-height: 1.25; }}
.sideuser small {{ color: #8FA3BF; }}
.sideuser .av {{ width: 36px; height: 36px; border-radius: 50%; background: linear-gradient(135deg, #12B5A6, #2F80ED); color: #fff; display: inline-flex;
        align-items: center; justify-content: center; font-weight: 700; flex: none; }}

/* grafik araç çubuğu: yalnızca PNG indir ve tam ekran kalsın ("Show data" geri dönüşsüz, "Copy spec" teknik) */
[data-testid="stElementToolbarButton"]:has(button[aria-label="Show data"]),
[data-testid="stElementToolbarButton"]:has(button[aria-label="Copy Vega-Lite spec"]) {{ display: none !important; }}
/* ---- kartlar ---- */
.cards {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(180px, 1fr)); gap: 14px; margin: .7rem 0 .4rem 0; }}
.card {{ background: #fff; border: 1px solid {LINE}; border-top: 4px solid var(--c); border-radius: 14px; padding: 15px 18px 14px 18px;
        box-shadow: 0 1px 2px rgba(14,27,46,.04), 0 10px 24px -14px rgba(14,27,46,.22); }}
.card.first {{ background: linear-gradient(180deg, color-mix(in srgb, var(--c) 9%, #fff) 0%, #fff 70%); border-color: color-mix(in srgb, var(--c) 40%, {LINE}); }}
.card .nm {{ display: flex; align-items: center; gap: 9px; font-weight: 600; color: {INK}; font-size: 1.02rem; margin-bottom: 8px; }}
.card .rk {{ width: 28px; height: 28px; flex: none; border-radius: 50%; background: var(--c); color: #fff; display: inline-flex; align-items: center; justify-content: center;
        font-family: 'Segoe UI Variable Display', 'Segoe UI', sans-serif; font-weight: 700; font-size: .95rem; }}
.card .tag {{ margin-left: auto; background: #E0F7F4; color: #0B6B61; border-radius: 999px; padding: 2px 10px; font-size: .74rem; font-weight: 600; }}
.card .big {{ font-family: 'Segoe UI Variable Display', 'Segoe UI', sans-serif; font-size: 1.85rem; font-weight: 700; color: {INK}; line-height: 1.1; letter-spacing: -0.02em; }}
.card .big small {{ font-size: .9rem; color: {MUTED}; font-weight: 500; margin-left: 5px; font-family: 'Segoe UI Variable Text', 'Segoe UI', sans-serif; letter-spacing: 0; }}
.card .big-sub {{ color: {MUTED}; font-size: .84rem; margin-bottom: 8px; }}
.card .kv {{ display: flex; justify-content: space-between; align-items: center; font-size: .88rem; color: {MUTED}; padding: 3px 0; }}
.card .kv b {{ color: {INK}; font-weight: 600; font-variant-numeric: tabular-nums; }}
.card .kv b.win {{ color: #0F766E; }}
.card .kv b.win::before {{ content: ""; display: inline-block; width: 7px; height: 7px; border-radius: 50%; background: #12B5A6; margin-right: 6px; vertical-align: 1px; }}
.mleg {{ display: inline-flex; align-items: center; gap: 7px; background: #fff; border: 1px solid {LINE}; border-radius: 999px; padding: 3px 12px 3px 9px; font-size: .88rem; color: {INK}; margin: 0 8px 6px 0; }}
.mleg i {{ display: inline-block; width: 18px; height: 4px; border-radius: 3px; }}
.mleg i.real {{ height: 10px; width: 14px; border-radius: 3px; opacity: .5; }}
[data-testid="stPopover"] button, [data-testid="stPopoverButton"] {{ border-radius: 10px; }}
@media (max-width: 720px) {{ .nilm-title {{ font-size: 1.7rem; }} .strip .num {{ font-size: 2rem; }} }}
</style>
"""


def inject():
    """Tüm sayfalar için CSS (app.py bir kez çağırır)."""
    st.markdown(_CSS, unsafe_allow_html=True)


def page_header(title: str, sub: str = "", chips=(), demo: bool = False):
    chip_html = "".join(f'<span class="chip">{html.escape(c)}</span>' for c in chips)
    st.markdown(f'<h1 class="nilm-title">{html.escape(title)}</h1>'
                f'{f"<p class=nilm-sub>{html.escape(sub)}</p>" if sub else ""}<div>{chip_html}</div>',
                unsafe_allow_html=True)


def section(title: str, note: str = ""):
    note_html = f'<p class="sec-note">{html.escape(note)}</p>' if note else ""
    st.markdown(f'<div class="sec">{html.escape(title)}</div>{note_html}', unsafe_allow_html=True)


def legend(appliances):
    items = "".join(f'<span><i style="background:{color(a)}"></i>{html.escape(tr(a))}</span>' for a in appliances)
    st.markdown(f'<div class="legend">{items}</div>', unsafe_allow_html=True)


def strip(cells):
    """Tek bantta birkaç büyük rakam. cells: dict(lab, num, unit='', sub='', tone='', small=False)."""
    out = ""
    for c in cells:
        unit = f"<small>{html.escape(c.get('unit', ''))}</small>" if c.get("unit") else ""
        cls = " ".join(x for x in ("num", c.get("tone", ""), "sm" if c.get("small") else "") if x)
        out += (f'<div class="cell"><div class="lab">{html.escape(c["lab"])}</div>'
                f'<div class="{cls}">{c["num"]}{unit}</div><div class="sub">{html.escape(c.get("sub", ""))}</div></div>')
    st.markdown(f'<div class="strip">{out}</div>', unsafe_allow_html=True)


def bill_strip(real_tl, pred_tl, real_kwh, pred_kwh):
    diff = pred_tl - real_tl
    pct = (diff / real_tl * 100) if real_tl else 0.0
    tone = "ok" if abs(pct) < 5 else ("over" if diff > 0 else "under")
    word = "fazla tahmin" if diff > 0 else "eksik tahmin"
    strip([dict(lab="Gerçek fatura", num=f"{real_tl:,.2f}", unit="TL", sub=f"{real_kwh:,.2f} kWh"),
           dict(lab="Tahmin edilen fatura", num=f"{pred_tl:,.2f}", unit="TL", sub=f"{pred_kwh:,.2f} kWh"),
           dict(lab="Fark", num=f"{diff:+,.2f}", unit="TL", sub=f"%{abs(pct):.1f} {word}", tone=tone)])


def callout(text_html: str):
    """Kısa özet cümlesi; text_html içinde <b> kullanılabilir (kullanıcı verisi değil, kod üretir)."""
    st.markdown(f'<div class="callout">{text_html}</div>', unsafe_allow_html=True)


def summary_sentence(bill: pd.DataFrame) -> str:
    """Fatura tablosundan otomatik özet cümlesi (sunumda anlatılacak ana mesaj)."""
    real, pred = bill["Gerçek (TL)"].sum(), bill["Tahmin (TL)"].sum()
    pct = (pred - real) / real * 100 if real else 0.0
    signed = bill["Tahmin (TL)"] - bill["Gerçek (TL)"]
    worst = signed.abs().idxmax()
    rel = (signed.abs() / bill["Gerçek (TL)"].clip(lower=1e-9))
    best = rel.idxmin()
    way = "fazla" if pct > 0 else "eksik"
    if abs(pct) < 0.05:
        head = "Model toplam faturayı neredeyse tam tahmin ediyor."
    else:
        head = f"Model toplam faturayı <b>%{abs(pct):.1f} {way}</b> tahmin ediyor."
    return (f"{head} En büyük sapma <b>{html.escape(tr(worst))}</b> kaleminde ({signed[worst]:+.2f} TL), "
            f"en yakın tahmin <b>{html.escape(tr(best))}</b> kaleminde (%{rel[best] * 100:.1f} sapma).")


def ledger(bill: pd.DataFrame):
    """Makbuz tarzı fatura kalemleri tablosu. bill: index=cihaz, bill_table sütunları."""
    peak = max(bill["Hata (TL)"].max(), 1e-9)
    total_real = max(bill["Gerçek (TL)"].sum(), 1e-9)
    rows = ""
    for a, r in bill.iterrows():
        w = max(2, int(r["Hata (TL)"] / peak * 60))
        share = r["Gerçek (TL)"] / total_real * 100
        rows += (f'<tr><td><span class="dot" style="background:{color(a)}"></span>{html.escape(tr(a))}</td>'
                 f'<td><span class="share" style="width:{max(2, int(share * 1.6))}px;background:{color(a)}"></span>%{share:.1f}</td>'
                 f'<td>{r["Gerçek (kWh)"]:,.2f}</td><td>{r["Gerçek (TL)"]:,.2f}</td><td>{r["Tahmin (TL)"]:,.2f}</td>'
                 f'<td><span class="errbar" style="width:{w}px"></span>{r["Hata (TL)"]:,.2f}</td></tr>')
    t = bill.sum(numeric_only=True)
    foot = (f'<tr><td>Toplam</td><td>%100</td><td>{t["Gerçek (kWh)"]:,.2f}</td><td>{t["Gerçek (TL)"]:,.2f}</td>'
            f'<td>{t["Tahmin (TL)"]:,.2f}</td><td>{t["Hata (TL)"]:,.2f}</td></tr>')
    st.markdown(f"""
<table class="ledger"><thead><tr><th>Cihaz</th><th>Fatura payı</th><th>Gerçek tüketim (kWh)</th><th>Gerçek (TL)</th><th>Tahmin (TL)</th><th>Mutlak hata (TL)</th></tr></thead>
<tbody>{rows}</tbody><tfoot>{foot}</tfoot></table>""", unsafe_allow_html=True)


def sidebar_footer():
    st.markdown('<div class="side-foot">Veri: UK-DALE<br>Disiplinler arası proje<br>Yusuf, Ersin, Kamil</div>',
                unsafe_allow_html=True)


def demo_note():
    st.markdown('<div class="demo-note">Sahte demo verisi gösteriliyor. Gerçek sonuçlar için '
                '<b>python -m scripts.run_eval --data ...</b> çalıştırın.</div>', unsafe_allow_html=True)


def side_label(text: str):
    st.markdown(f'<div class="side-label">{html.escape(text)}</div>', unsafe_allow_html=True)


def side_card(title: str, value: str, unit: str, sub: str, shares: list):
    """Kenar çubuğunda seçili evin özeti. shares: [(renk, pay)]."""
    tot = sum(v for _, v in shares) or 1.0
    bar = "".join(f'<i style="background:{c};width:{v / tot * 100:.1f}%"></i>' for c, v in shares if v > 0)
    st.markdown(f'<div class="sidecard"><div class="t">{html.escape(title)}</div>'
                f'<div class="v">{html.escape(value)}<small>{html.escape(unit)}</small></div>'
                f'<div class="s">{html.escape(sub)}</div><div class="bar">{bar}</div></div>', unsafe_allow_html=True)


def model_pill(m: str) -> str:
    dots = ["\U0001F534", "\U0001F7E2", "\U0001F535", "\U0001F7E1", "\U0001F7E3", "\u26AB"]
    i = _MODELS.index(m) if m in _MODELS else 0
    return f"{dots[i % len(dots)]} {m}"


def side_user(name: str, sub: str):
    st.markdown(f'<div class="sideuser"><span class="av">{html.escape(name[:1].upper())}</span>'
                f'<span><b>{html.escape(name)}</b><br><small>{html.escape(sub)}</small></span></div>', unsafe_allow_html=True)


def side_pills(items):
    st.markdown("".join(f'<span class="sidepill">{html.escape(i)}</span>' for i in items), unsafe_allow_html=True)


def model_legend(models, real_color: str | None = None, real_label: str = "Gerçek"):
    items = ""
    if real_color:
        items += f'<span class="mleg"><i class="real" style="background:{real_color}"></i>{html.escape(real_label)}</span>'
    items += "".join(f'<span class="mleg"><i style="background:{mcolor(m)}"></i>{html.escape(m)}</span>' for m in models)
    st.markdown(f'<div>{items}</div>', unsafe_allow_html=True)


def cards(items, min_h: int = 0):
    """Kart ızgarası. item: dict(color, name, rank=None, tag='', big='', unit='', sub='', rows=[(etiket, değer, kazanan_mı)], first=False)."""
    out = ""
    for c in items:
        rk = f'<span class="rk">{c["rank"]}</span>' if c.get("rank") else ""
        tag = f'<span class="tag">{html.escape(c["tag"])}</span>' if c.get("tag") else ""
        big = ""
        if c.get("big"):
            unit = f"<small>{html.escape(c.get('unit', ''))}</small>" if c.get("unit") else ""
            big = f'<div class="big">{c["big"]}{unit}</div><div class="big-sub">{html.escape(c.get("sub", ""))}</div>'
        rows = "".join(f'<div class="kv"><span>{html.escape(k)}</span><b class="{"win" if w else ""}">{html.escape(v)}</b></div>'
                       for k, v, w in c.get("rows", []))
        out += (f'<div class="card{" first" if c.get("first") else ""}" style="--c:{c["color"]};min-height:{min_h}px">'
                f'<div class="nm">{rk}<span>{html.escape(c["name"])}</span>{tag}</div>{big}{rows}</div>')
    st.markdown(f'<div class="cards">{out}</div>', unsafe_allow_html=True)
