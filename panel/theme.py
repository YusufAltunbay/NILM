"""Panelin görünümü: renkler, CSS ve ortak bileşenler."""
import base64
import html
import zlib
from pathlib import Path

import pandas as pd
import streamlit as st

# İki görünüm. Sol panel ve sayfa başlık bandı her iki modda da koyu kalır; değişen ana alan.
PALETTES = {
    "dark": dict(INK="#E8EEF6", MUTED="#8FA3BF", LINE="#22344F", BG="#0A1524", SURFACE="#111F33", SURFACE2="#16273F",
                 GRID="#1E3049", SOFT="#C9D5E4", GLASS="rgba(255,255,255,.07)", GLASSLINE="rgba(255,255,255,.10)",
                 DOTS="rgba(255,255,255,.05)", OK="#34D3BF", OVER="#FBBF24", UNDER="#7FB4FF", ACC="#5EE6D6", ACCBLUE="#9CC3FF",
                 ERRBAR="#3A5070", SHADOW="0 22px 44px -28px rgba(0,0,0,.85)", GLOW1=".16", GLOW2=".12"),
    "light": dict(INK="#0E1B2E", MUTED="#5B6B82", LINE="#DDE3EC", BG="#F3F5F9", SURFACE="#FFFFFF", SURFACE2="#F6F8FB",
                  GRID="#E8EDF4", SOFT="#33445C", GLASS="#E9EEF5", GLASSLINE="#DCE3EC",
                  DOTS="rgba(14,27,46,.05)", OK="#0F766E", OVER="#B45309", UNDER="#1D4ED8", ACC="#0B6B61", ACCBLUE="#1D4ED8",
                  ERRBAR="#CBD5E3", SHADOW="0 1px 2px rgba(14,27,46,.05), 0 16px 32px -22px rgba(14,27,46,.30)", GLOW1=".10", GLOW2=".07"),
}
MODE = "dark"
INK = MUTED = LINE = BG = SURFACE = SURFACE2 = GRID = SOFT = GLASS = GLASSLINE = DOTS = ""
OK = OVER = UNDER = ACC = ACCBLUE = ERRBAR = SHADOW = GLOW1 = GLOW2 = ""


def mode() -> str:
    """Tarayıcıda seçili görünüm: 'light' ya da 'dark' (Streamlit temasından)."""
    try:
        t = st.context.theme.type
    except Exception:
        t = None
    return t if t in PALETTES else "dark"


def apply_mode(m: str | None = None):
    """Renk değişkenlerini seçili moda göre ayarlar (grafikler ve CSS bunları okur)."""
    global MODE
    MODE = m or mode()
    globals().update(PALETTES[MODE])


apply_mode("dark")

# Cihaz -> (Türkçe ad, renk). Yeni cihaz eklenirse buraya da eklenir.
APPLIANCES = {
    "fridge": ("Buzdolabı", "#2F80ED"),
    "washing machine": ("Çamaşır makinesi", "#7C5CFC"),
    "kettle": ("Su ısıtıcısı", "#FF9F1C"),
    "dish washer": ("Bulaşık makinesi", "#12B5A6"),
    "microwave": ("Mikrodalga", "#F0507A"),
    "other": ("Diğer cihazlar", "#A8B3C4"),  # faturanın modellenmeyen kısmı (aydınlatma, TV, ısıtma...)
}
_FALLBACK = ["#64748B", "#A16207", "#0F766E", "#9D174D", "#4F46E5", "#BE185D", "#15803D", "#B45309"]
# Model renkleri cihaz renklerinden (mavi, mor, turuncu, turkuaz, pembe) ayrışsın diye ayrı bir set.
MODEL_COLORS = ["#F43F5E", "#22C55E", "#22B8E0", "#EAB308", "#A855F7", "#E8EEF6"]
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


_FONT_DIR = Path(__file__).parent / "assets" / "fonts"


def _font_faces() -> str:
    """Başlık yazı tipi (Bricolage Grotesque, OFL) CSS'e gömülü; internet gerektirmez."""
    out = ""
    for f, rng in (("bricolage-grotesque-latin-wght-normal.woff2", "U+0000-00FF,U+0131,U+0152-0153,U+02BB-02BC,U+02C6,U+02DA,U+02DC,U+2000-206F,U+20AC,U+2122,U+2212"),
                   ("bricolage-grotesque-latin-ext-wght-normal.woff2", "U+0100-02BA,U+02BD-02C5,U+02C7-02CC,U+02CE-02D7,U+02DD-02FF,U+1E00-1E9F,U+20A0-20C0")):
        p = _FONT_DIR / f
        if p.exists():
            b = base64.b64encode(p.read_bytes()).decode()
            out += (f"@font-face {{ font-family: 'Bricolage'; font-style: normal; font-weight: 200 800; font-display: swap; "
                    f"src: url(data:font/woff2;base64,{b}) format('woff2'); unicode-range: {rng}; }}\n")
    return out


DISPLAY = "'Bricolage', 'Segoe UI Variable Display', 'Segoe UI', system-ui, sans-serif"
_FONTS = _font_faces()

def _css() -> str:
    """Seçili moda (aydınlık/karanlık) göre CSS; renkler apply_mode ile güncellenen modül değişkenlerinden."""
    return f"""
<style>
{_FONTS}
.stApp, [data-testid="stSidebar"] {{ font-family: 'Segoe UI Variable Text', 'Segoe UI', system-ui, sans-serif; }}
.stApp h1, .stApp h2, .stApp h3, .nilm-title, .num, .sec, .card .big, .sidecard .v, .card .rk {{ font-family: {DISPLAY} !important; }}
.stApp {{ background: radial-gradient(1100px 520px at 80% -120px, rgba(18,181,166,{GLOW1}), rgba(18,181,166,0) 70%), radial-gradient(900px 600px at -10% 110%, rgba(47,128,237,{GLOW2}), rgba(47,128,237,0) 70%), {BG} !important; }}
.stApp::before {{ content: ""; position: fixed; inset: 0; pointer-events: none; z-index: 0; opacity: .5;
        background-image: radial-gradient({DOTS} 1px, transparent 1px); background-size: 22px 22px; }}
.block-container {{ padding-top: 2.4rem; padding-bottom: 3rem; max-width: 1200px; }}
header[data-testid="stHeader"] {{ background: transparent; }}
.stDeployButton, [data-testid="stAppDeployButton"], [data-testid="stToolbarActions"], [data-testid="stMainMenu"], #MainMenu, footer {{ display: none !important; }}

.nilm-title {{ font-size: 2.3rem; font-weight: 700; letter-spacing: -0.02em; color: {INK}; margin: 0 0 .15rem 0; line-height: 1.15; }}
.nilm-sub {{ color: {MUTED}; max-width: 64ch; margin: 0 0 .9rem 0; font-size: 1.02rem; line-height: 1.55; }}
.chip {{ display: inline-block; padding: 3px 11px; border-radius: 999px; background: {GLASS}; color: {SOFT}; border: 1px solid {GLASSLINE};
         font-size: .82rem; font-weight: 500; margin: 0 6px 6px 0; }}
.chip.demo {{ background: #FFF1D6; color: #8A5200; }}

.sec {{ font-family: 'Segoe UI Variable Display', 'Segoe UI', sans-serif; font-size: 1.22rem; font-weight: 700; color: {INK};
        margin: 1.9rem 0 .15rem 0; letter-spacing: -0.01em; }}
.sec-note {{ color: {MUTED}; font-size: .92rem; margin: 0 0 .6rem 0; max-width: 70ch; }}

.strip {{ display: flex; flex-wrap: wrap; background: {SURFACE}; border: 1px solid {LINE}; border-radius: 8px; margin: 1.1rem 0 .4rem 0; }}
.strip .cell {{ flex: 1 1 170px; padding: 18px 26px; border-right: 1px solid {LINE}; }}
.strip .cell:last-child {{ border-right: none; }}
.strip .lab {{ font-size: .88rem; color: {MUTED}; margin-bottom: 2px; }}
.strip .num {{ font-size: 2.5rem; font-weight: 700; line-height: 1.1; color: {INK}; font-variant-numeric: tabular-nums; letter-spacing: -0.02em; }}
.strip .num small {{ font-family: 'Segoe UI Variable Text', 'Segoe UI', sans-serif; font-size: 1rem; font-weight: 500; color: {MUTED}; margin-left: 6px; letter-spacing: 0; }}
.strip .sub {{ font-size: .88rem; color: {MUTED}; margin-top: 2px; }}
.over {{ color: {OVER} !important; }} .under {{ color: {UNDER} !important; }} .ok {{ color: {OK} !important; }}

.legend {{ display: flex; flex-wrap: wrap; gap: 6px 18px; margin: .2rem 0 .3rem 0; font-size: .9rem; color: {SOFT}; }}
.legend i {{ display: inline-block; width: 11px; height: 11px; border-radius: 3px; margin-right: 7px; vertical-align: -1px; }}

table.ledger {{ width: 100%; border-collapse: collapse; background: {SURFACE}; border: 1px solid {LINE}; border-radius: 8px; overflow: hidden; font-variant-numeric: tabular-nums; }}
.ledger th {{ text-align: right; font-weight: 500; font-size: .86rem; color: {MUTED}; padding: 11px 16px; border-bottom: 1px solid {LINE}; background: {SURFACE2}; }}
.ledger th:first-child, .ledger td:first-child {{ text-align: left; }}
.ledger td {{ text-align: right; padding: 12px 16px; border-bottom: 1px solid {LINE}; color: {INK}; font-size: .97rem; }}
.ledger tr:last-child td {{ border-bottom: none; }}
.ledger tfoot td {{ font-weight: 600; background: {SURFACE2}; border-top: 1px solid {LINE}; }}
.ledger .dot {{ display: inline-block; width: 11px; height: 11px; border-radius: 3px; margin-right: 10px; vertical-align: -1px; }}
.ledger .errbar {{ display: inline-block; height: 7px; border-radius: 4px; background: {ERRBAR}; margin-right: 10px; vertical-align: middle; }}

[data-testid="stSidebar"] {{ border-right: none; }}
[data-testid="stSidebar"] h2, [data-testid="stSidebar"] h3 {{ font-family: 'Segoe UI Variable Display', 'Segoe UI', sans-serif; font-weight: 600; font-size: 1.05rem; }}
.side-foot {{ color: #8FA3BF; font-size: .8rem; line-height: 1.5; margin-top: 2rem; padding-top: .9rem; border-top: 1px solid #243752; }}
.demo-note {{ background: #2A2411; color: #FFD58A; font-size: .84rem; line-height: 1.45; padding: 9px 12px; border-radius: 6px; margin: 0 0 1rem 0; }}

[data-testid="stVegaLiteChart"], [data-testid="stArrowVegaLiteChart"] {{ background: {SURFACE}; border: 1px solid {LINE}; border-radius: 8px; padding: 14px 10px 6px 10px; overflow: hidden; }}
[data-testid="stDataFrame"] {{ border: 1px solid {LINE}; border-radius: 8px; overflow: hidden; }}
img[data-testid="stSidebarLogo"] {{ height: 54px !important; width: auto !important; max-width: 100% !important; }}
[data-testid="stSidebarHeader"] {{ height: auto !important; padding: 1.4rem 1rem .6rem 1.1rem !important; }}
.callout {{ border-left: 3px solid #12B5A6; background: {SURFACE}; padding: 12px 18px; color: {SOFT}; margin: .9rem 0 .2rem 0; max-width: 84ch; line-height: 1.55; }}
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
.card {{ background: {SURFACE}; border: 1px solid {LINE}; border-top: 4px solid var(--c); border-radius: 14px; padding: 15px 18px 14px 18px;
        box-shadow: {SHADOW}; }}
.card.first {{ background: linear-gradient(180deg, color-mix(in srgb, var(--c) 16%, {SURFACE}) 0%, {SURFACE} 75%); border-color: color-mix(in srgb, var(--c) 40%, {LINE}); }}
.card .nm {{ display: flex; align-items: center; gap: 9px; font-weight: 600; color: {INK}; font-size: 1.02rem; margin-bottom: 8px; }}
.card .rk {{ width: 28px; height: 28px; flex: none; border-radius: 50%; background: var(--c); color: #fff; display: inline-flex; align-items: center; justify-content: center;
        font-family: 'Segoe UI Variable Display', 'Segoe UI', sans-serif; font-weight: 700; font-size: .95rem; }}
.card .tag {{ margin-left: auto; background: rgba(18,181,166,.16); color: {ACC}; border-radius: 999px; padding: 2px 10px; font-size: .74rem; font-weight: 600; }}
.card .big {{ font-family: 'Segoe UI Variable Display', 'Segoe UI', sans-serif; font-size: 1.85rem; font-weight: 700; color: {INK}; line-height: 1.1; letter-spacing: -0.02em; }}
.card .big small {{ font-size: .9rem; color: {MUTED}; font-weight: 500; margin-left: 5px; font-family: 'Segoe UI Variable Text', 'Segoe UI', sans-serif; letter-spacing: 0; }}
.card .big-sub {{ color: {MUTED}; font-size: .84rem; margin-bottom: 8px; }}
.card .kv {{ display: flex; justify-content: space-between; align-items: center; font-size: .88rem; color: {MUTED}; padding: 3px 0; }}
.card .kv b {{ color: {INK}; font-weight: 600; font-variant-numeric: tabular-nums; }}
.card .kv b.win {{ color: {OK}; }}
.card .kv b.win::before {{ content: ""; display: inline-block; width: 7px; height: 7px; border-radius: 50%; background: #12B5A6; margin-right: 6px; vertical-align: 1px; }}
.mleg {{ display: inline-flex; align-items: center; gap: 7px; background: {SURFACE}; border: 1px solid {LINE}; border-radius: 999px; padding: 3px 12px 3px 9px; font-size: .88rem; color: {INK}; margin: 0 8px 6px 0; }}
.mleg i {{ display: inline-block; width: 18px; height: 4px; border-radius: 3px; }}
.mleg i.real {{ height: 10px; width: 14px; border-radius: 3px; opacity: .5; }}
[data-testid="stPopover"] button, [data-testid="stPopoverButton"] {{ border-radius: 10px; }}
[data-testid="stMain"] [data-testid="stButtonGroup"] button {{ border-radius: 10px !important; }}
[data-testid="stMain"] [data-testid="stButtonGroup"] button[kind$="Active"] {{ background: rgba(18,181,166,.20) !important; border-color: #12B5A6 !important; color: {ACC} !important; }}
[data-testid="stMain"] [data-baseweb="input"], [data-testid="stMain"] [data-testid="stNumberInputContainer"], [data-testid="stMain"] [data-baseweb="select"] > div {{ border-radius: 10px !important; }}
[data-testid="stMain"] .block-container {{ position: relative; z-index: 1; }}
/* ---- giriş animasyonları: sayfa açılınca bir kez, kısa ---- */
@keyframes nl-rise {{ from {{ opacity: 0; transform: translateY(10px); }} to {{ opacity: 1; transform: none; }} }}
@keyframes nl-fade {{ from {{ opacity: 0; }} to {{ opacity: 1; }} }}
@keyframes nl-grow {{ from {{ transform: scaleX(0); }} to {{ transform: scaleX(1); }} }}
.strip {{ animation: nl-rise .45s cubic-bezier(.2,.8,.2,1) .08s both; }}
.cards .card {{ animation: nl-rise .45s cubic-bezier(.2,.8,.2,1) both; transition: transform .18s ease, box-shadow .18s ease; }}
.cards .card:nth-child(2) {{ animation-delay: .07s; }} .cards .card:nth-child(3) {{ animation-delay: .14s; }}
.cards .card:nth-child(4) {{ animation-delay: .21s; }} .cards .card:nth-child(n+5) {{ animation-delay: .28s; }}
.cards .card:hover {{ transform: translateY(-3px); box-shadow: 0 0 0 1px color-mix(in srgb, var(--c) 55%, transparent), 0 24px 40px -22px color-mix(in srgb, var(--c) 60%, transparent); }}
.sidecard .bar i {{ transform-origin: left; animation: nl-grow .6s cubic-bezier(.2,.8,.2,1) .15s both; }}
.ledger .share, .ledger .errbar {{ transform-origin: left; animation: nl-grow .55s cubic-bezier(.2,.8,.2,1) .1s both; }}
[data-testid="stVegaLiteChart"], [data-testid="stArrowVegaLiteChart"] {{ animation: nl-fade .5s ease both; }}
.callout {{ animation: nl-rise .45s cubic-bezier(.2,.8,.2,1) .1s both; }}
[data-testid="InputInstructions"] {{ display: none !important; }}
/* ---- aydınlık / karanlık düğmesi (sol panel) ---- */
.nl-mode {{ display: flex; align-items: center; gap: 11px; cursor: pointer; user-select: none; margin: .2rem 0 .6rem 0; padding: 7px 10px;
           border-radius: 14px; border: 1px solid rgba(255,255,255,.10); background: rgba(255,255,255,.04); transition: background .2s, border-color .2s; }}
.nl-mode:hover {{ background: rgba(255,255,255,.08); border-color: rgba(18,181,166,.6); }}
.nl-mode:focus-visible {{ outline: 2px solid #12B5A6; outline-offset: 2px; }}
.nl-track {{ position: relative; width: 58px; height: 30px; border-radius: 999px; flex: none; overflow: hidden;
            background: linear-gradient(135deg, #0B1626, #1B2F4D); box-shadow: inset 0 2px 6px rgba(0,0,0,.5); transition: background .4s; }}
.nl-mode.is-light .nl-track {{ background: linear-gradient(135deg, #7DD3FC, #FDE68A); }}
.nl-track .st1, .nl-track .st2 {{ position: absolute; width: 3px; height: 3px; border-radius: 50%; background: #fff; transition: opacity .3s; }}
.nl-track .st1 {{ left: 36px; top: 8px; }} .nl-track .st2 {{ left: 44px; top: 18px; width: 2px; height: 2px; }}
.nl-mode.is-light .nl-track .st1, .nl-mode.is-light .nl-track .st2 {{ opacity: 0; }}
.nl-knob {{ position: absolute; top: 3px; left: 3px; width: 24px; height: 24px; border-radius: 50%; background: #E8EEF6;
           box-shadow: inset -6px -2px 0 0 #B9C7DA, 0 2px 6px rgba(0,0,0,.4); transition: transform .45s cubic-bezier(.5,1.6,.4,1), background .4s, box-shadow .4s; }}
.nl-mode.is-light .nl-knob {{ transform: translateX(28px) rotate(180deg); background: #FBBF24; box-shadow: 0 0 0 4px rgba(251,191,36,.25), 0 0 14px rgba(251,191,36,.8); }}
.nl-mode b {{ color: #E6ECF5; font-size: .9rem; font-weight: 600; display: block; line-height: 1.15; }}
.nl-mode small {{ color: #8FA3BF; font-size: .76rem; }}
.nl-wipe {{ position: fixed; inset: 0; z-index: 999999; pointer-events: none; }}
/* 'Benim faturam': halka kutusu sağdaki tabloyla aynı yükseklik ve genişlikte, halka ortada */
.st-key-mine_split [data-testid="stHorizontalBlock"] {{ align-items: stretch !important; }}
.st-key-mine_split [data-testid="stColumn"]:first-child [data-testid="stVerticalBlock"],
.st-key-mine_split [data-testid="stColumn"]:first-child [data-testid="stElementContainer"],
.st-key-mine_split [data-testid="stColumn"]:first-child [data-testid="stFullScreenFrame"],
.st-key-mine_split [data-testid="stColumn"]:first-child [data-testid="stFullScreenFrame"] > div {{ height: 100% !important; width: 100% !important; }}
.st-key-mine_split [data-testid="stColumn"]:first-child [data-testid="stVegaLiteChart"] {{ height: 100% !important; width: 100% !important;
        display: flex !important; align-items: center; justify-content: center; box-sizing: border-box; }}
.st-key-mine_split table.ledger {{ margin: 0; }}
.st-key-mine_split [data-testid="stMarkdownContainer"], .st-key-mine_split [data-testid="stMarkdown"] {{ margin-bottom: 0 !important; }}
/* ---- nasıl çalışır ---- */
.hw-flow {{ display: grid; grid-template-columns: repeat(4, 1fr); gap: 16px; margin: .4rem 0 .6rem 0; }}
.hw-step {{ position: relative; background: {SURFACE}; border: 1px solid {LINE}; border-radius: 18px; padding: 16px 18px 16px 18px;
           animation: nl-rise .55s cubic-bezier(.2,.8,.2,1) var(--d) both; box-shadow: {SHADOW}; }}
.hw-step:not(:last-child)::after {{ content: ""; position: absolute; right: -13px; top: 58px; width: 10px; height: 10px; border-top: 2px solid #12B5A6;
           border-right: 2px solid #12B5A6; transform: rotate(45deg); z-index: 2; }}
.hw-n {{ width: 30px; height: 30px; border-radius: 50%; background: linear-gradient(135deg, #12B5A6, #2F80ED); color: #fff; font-family: {DISPLAY};
        font-weight: 700; display: flex; align-items: center; justify-content: center; margin-bottom: 10px; }}
.hw-vis {{ height: 64px; margin-bottom: 12px; display: flex; align-items: flex-end; }}
.hw-spark {{ width: 100%; height: 54px; }} .hw-spark svg {{ width: 100%; height: 100%; }}
.hw-spark polyline {{ stroke-dasharray: 900; stroke-dashoffset: 900; animation: hw-draw 1.6s ease .3s forwards; }}
@keyframes hw-draw {{ to {{ stroke-dashoffset: 0; }} }}
.hw-model {{ display: grid; grid-template-columns: repeat(6, 1fr); gap: 5px; width: 100%; }}
.hw-model span {{ height: 26px; border-radius: 6px; background: #12B5A6; opacity: .15; animation: hw-pulse 1.8s ease-in-out var(--d) infinite; }}
@keyframes hw-pulse {{ 0%, 100% {{ opacity: .12; }} 50% {{ opacity: .75; }} }}
.hw-stack {{ display: flex; align-items: flex-end; gap: 6px; height: 60px; width: 100%; }}
.hw-stack i {{ flex: 1; border-radius: 5px 5px 2px 2px; transform-origin: bottom; animation: nl-up .6s cubic-bezier(.2,.8,.2,1) .5s both; }}
.hw-bill b {{ font-family: {DISPLAY}; font-size: 2.4rem; color: {INK}; line-height: 1; }} .hw-bill small {{ color: {MUTED}; margin-left: 6px; }}
.hw-t {{ font-family: {DISPLAY}; font-size: 1.15rem; font-weight: 700; color: {INK}; }}
.hw-x {{ color: {SOFT}; font-size: .9rem; line-height: 1.45; margin: 4px 0 10px 0; min-height: 3.9em; }}
.hw-f {{ display: inline-block; color: {ACC}; background: rgba(18,181,166,.12); border-radius: 999px; padding: 2px 10px; font-size: .78rem; }}
.hw-day {{ color: {MUTED}; font-size: .92rem; text-align: right; }}
.hw-houses {{ display: grid; grid-template-columns: repeat(5, 1fr); gap: 12px; margin: .5rem 0 .4rem 0; }}
.hw-house {{ background: {SURFACE}; border: 1px solid {LINE}; border-radius: 16px; padding: 14px 16px; opacity: .55; }}
.hw-house.on {{ opacity: 1; border-color: #12B5A6; box-shadow: 0 0 0 1px rgba(18,181,166,.35), 0 20px 40px -26px rgba(18,181,166,.6); }}
.hw-house b {{ display: block; font-family: {DISPLAY}; font-size: 1.4rem; color: {INK}; }}
.hw-house span {{ display: inline-block; font-size: .76rem; border-radius: 999px; padding: 1px 9px; margin: 4px 0 8px 0; background: {GLASS}; color: {SOFT}; }}
.hw-house.görülmeyen span {{ background: rgba(18,181,166,.2); color: {ACC}; }}
.hw-house.doğrulama span {{ background: rgba(47,128,237,.18); color: {ACCBLUE}; }}
.hw-house small {{ display: block; color: {MUTED}; font-size: .8rem; line-height: 1.35; }}
.hw-note {{ color: {MUTED}; font-size: .86rem; margin-top: .3rem; }}
@media (max-width: 1000px) {{ .hw-flow {{ grid-template-columns: repeat(2, 1fr); }} .hw-houses {{ grid-template-columns: repeat(2, 1fr); }} .hw-step::after {{ display: none; }} }}
/* ---- sayfa başlık bandı ---- */
.pg-hero {{ border: 1px solid rgba(255,255,255,.07); position: relative; overflow: hidden; display: flex; align-items: flex-end; justify-content: space-between; gap: 24px;
           background: radial-gradient(600px 260px at 12% 0%, rgba(19,74,87,.9), rgba(19,74,87,0) 70%), linear-gradient(120deg, #0E1B2E 0%, #0F2A42 60%, #0B3B45 100%);
           border-radius: 20px; padding: 26px 30px 22px 30px; margin: 0 0 1.1rem 0; box-shadow: 0 24px 48px -30px rgba(14,27,46,.7);
           animation: nl-rise .5s cubic-bezier(.2,.8,.2,1) both; }}
.pg-hero .nilm-title {{ color: #fff !important; font-size: 2.6rem; font-weight: 700; letter-spacing: -0.03em; margin: 0 0 .5rem 0; padding: 0; text-wrap: balance; animation: none; }}
.pg-hero .nilm-sub {{ color: #B9C7DA; margin-bottom: .7rem; }}
.pg-chips .chip {{ background: rgba(255,255,255,.10); color: #E6ECF5; border: 1px solid rgba(255,255,255,.14); backdrop-filter: blur(4px); animation: nl-fade .4s ease .15s both; }}
.pg-bars {{ display: flex; align-items: flex-end; gap: 7px; height: 92px; opacity: .8; flex: none; }}
.pg-bars span {{ display: flex; flex-direction: column-reverse; width: 16px; border-radius: 4px; overflow: hidden; transform-origin: bottom;
                animation: nl-up .6s cubic-bezier(.2,.8,.2,1) both; }}
.pg-bars i {{ display: block; width: 100%; }}
.pg-bars i + i {{ border-bottom: 1px solid #0F2A42; }}
@keyframes nl-up {{ from {{ transform: scaleY(0); }} to {{ transform: scaleY(1); }} }}
.sec {{ display: flex; align-items: center; gap: 10px; font-size: 1.3rem; }}
.sec::before {{ content: ""; width: 6px; height: 20px; border-radius: 3px; background: linear-gradient(180deg, #12B5A6, #2F80ED); }}
[data-testid="stVegaLiteChart"], [data-testid="stArrowVegaLiteChart"], .strip, table.ledger {{ border-radius: 16px !important;
        box-shadow: {SHADOW}; }}
.strip {{ overflow: hidden; }}
.strip .cell {{ position: relative; }}
.strip .cell::after {{ content: ""; position: absolute; left: 26px; right: 26px; bottom: 0; height: 3px; border-radius: 3px 3px 0 0;
        background: linear-gradient(90deg, #12B5A6, #2F80ED); transform: scaleX(0); transform-origin: left; transition: transform .35s ease; }}
.strip .cell:hover::after {{ transform: scaleX(1); }}
.callout {{ border-left: none; border-radius: 14px; background: linear-gradient(90deg, rgba(18,181,166,.12), rgba(18,181,166,.02) 70%), {SURFACE};
        box-shadow: inset 4px 0 0 #12B5A6; }}
.ledger tbody tr {{ animation: nl-fade .45s ease both; }}
.ledger tr.oth td {{ color: {MUTED}; font-style: italic; }}
.ledger td:first-child {{ white-space: nowrap; }}
.ledger .muted {{ color: {MUTED}; }}
.ledger tbody tr:hover td {{ background: {SURFACE2}; }}
/* kaydırınca beliren öğeler (motion betiği sınıf ekler) */
.nl-reveal {{ opacity: 0; transform: translateY(16px); }}
.nl-reveal.nl-in {{ opacity: 1; transform: none; transition: opacity .55s ease, transform .55s cubic-bezier(.2,.8,.2,1); }}
.stButton button[kind="primary"], [data-testid="stFormSubmitButton"] button[kind="primary"], [data-testid="stBaseButton-primaryFormSubmit"] {{
        background: linear-gradient(135deg, #12B5A6, #0E9C8F) !important; border: none !important; box-shadow: 0 8px 18px -10px rgba(18,181,166,.9);
        transition: transform .15s ease, box-shadow .15s ease !important; }}
.stButton button:hover, [data-testid="stFormSubmitButton"] button:hover {{ transform: translateY(-1px); }}
@media (max-width: 900px) {{ .pg-bars {{ display: none; }} .pg-hero .nilm-title {{ font-size: 2rem; }} }}
@media (max-width: 720px) {{ .nilm-title {{ font-size: 1.7rem; }} .strip .num {{ font-size: 2rem; }} }}
</style>
"""


_MOTION = r"""
<script>
(() => {
  if (window.__nilmMotion) return; window.__nilmMotion = true;
  const reduce = false;  // hareketler kısa ve küçük; işletim sistemi ayarından bağımsız oynar
  const last = new Map();               // data-k -> son gösterilen değer (geçişler oradan başlar)
  const NUM = /^([+\u2212-]?)([\d,]*\.?\d+)$/;
  const fmt = (v, dec, sign) => (sign && v > 0 ? '+' : '') + v.toLocaleString('en-US', {minimumFractionDigits: dec, maximumFractionDigits: dec});
  function count(el) {
    const t = el.firstChild;
    if (!t || t.nodeType !== 3) return;
    const raw = t.nodeValue.trim();
    if (raw === el.__shown) return;     // kendi yazdığımız değer
    const m = raw.match(NUM);
    if (!m) return;
    const sign = m[1] === '+', neg = m[1] === '-' || m[1] === '\u2212';
    const to = parseFloat(m[2].replace(/,/g, '')) * (neg ? -1 : 1);
    const dec = (m[2].split('.')[1] || '').length;
    const key = (el.dataset.k || '') + location.pathname;
    const from = last.has(key) ? last.get(key) : 0;
    last.set(key, to);
    if (reduce || from === to) { el.__shown = raw; return; }
    const t0 = performance.now(), dur = 750;
    const step = now => {
      const k = Math.min(1, (now - t0) / dur), e = 1 - Math.pow(1 - k, 3);
      const s = k < 1 ? fmt(from + (to - from) * e, dec, sign) : raw;
      el.__shown = s; t.nodeValue = s;
      if (k < 1) requestAnimationFrame(step);
    };
    requestAnimationFrame(step);
  }
  const io = new IntersectionObserver(es => es.forEach(e => {
    if (e.isIntersecting) { e.target.classList.add('nl-in'); io.unobserve(e.target); }
  }), {rootMargin: '0px 0px -6% 0px'});
  const REVEAL = '[data-testid="stVegaLiteChart"], [data-testid="stArrowVegaLiteChart"], table.ledger, .cards, [data-testid="stDataFrame"]';
  function scan() {
    document.querySelectorAll('.strip .num, .card .big, .sidecard .v').forEach(count);
    if (reduce) return;
    document.querySelectorAll(REVEAL).forEach(el => {
      if (el.__rv) return; el.__rv = true;
      const r = el.getBoundingClientRect();
      if (r.top < innerHeight * 0.92) return;          // ilk ekranda görünenler zaten açılış animasyonuyla geliyor
      el.classList.add('nl-reveal'); io.observe(el);
    });
  }
  // ---- aydınlık / karanlık: Streamlit temasını her sayfa için tarayıcıda saklar, dairesel geçişle yeniler ----
  const PAGES = ['', 'nasil_calisir', 'tuketim', 'zaman_serisi', 'karsilastirma', 'tasarruf', 'gorulmeyen_ev', 'giris'];
  const BGS = {light: '#F3F5F9', dark: '#0A1524'};
  const setAll = name => {
    const base = location.pathname.replace(/[^/]*$/, '');
    PAGES.forEach(p => localStorage.setItem(`stActiveTheme-${base}${p}-v2`, JSON.stringify(name)));
    localStorage.setItem('nilm_theme', name);
  };
  try {
    if (!localStorage.getItem('nilm_theme')) {          // ilk ziyaret: karanlık başlar
      setAll('Dark');
      if (matchMedia('(prefers-color-scheme: light)').matches) location.reload();
    }
    const fade = sessionStorage.getItem('nilm_fade');
    if (fade) {                                           // yenilemeden sonra yeni renkten açılış
      sessionStorage.removeItem('nilm_fade');
      const o = document.createElement('div'); o.className = 'nl-wipe'; o.style.background = fade; document.body.appendChild(o);
      setTimeout(() => o.animate([{opacity: 1}, {opacity: 0}], {duration: 550, easing: 'ease-out', fill: 'forwards'}).onfinish = () => o.remove(), 450);
    }
  } catch (e) {}
  function switchTo(to, x, y) {
    const o = document.createElement('div'); o.className = 'nl-wipe'; o.style.background = BGS[to]; document.body.appendChild(o);
    const r = Math.hypot(Math.max(x, innerWidth - x), Math.max(y, innerHeight - y));
    o.animate([{clipPath: `circle(0px at ${x}px ${y}px)`}, {clipPath: `circle(${r}px at ${x}px ${y}px)`}],
              {duration: 560, easing: 'cubic-bezier(.6,0,.2,1)', fill: 'forwards'}).onfinish = () => {
      try { setAll(to === 'light' ? 'Light' : 'Dark'); sessionStorage.setItem('nilm_fade', BGS[to]); } catch (e) {}
      location.reload();
    };
  }
  const go = e => {
    const t = e.target.closest && e.target.closest('.nl-mode');
    if (!t || (e.type === 'keydown' && e.key !== 'Enter' && e.key !== ' ')) return;
    e.preventDefault();
    t.classList.toggle('is-light');
    const b = t.getBoundingClientRect();
    switchTo(t.dataset.to, b.left + 32, b.top + b.height / 2);
  };
  document.addEventListener('click', go); document.addEventListener('keydown', go);

  let q = false;
  new MutationObserver(() => { if (!q) { q = true; requestAnimationFrame(() => { q = false; scan(); }); } })
    .observe(document.body, {childList: true, subtree: true, characterData: true});
  scan();
})();
</script>
"""


def inject():
    """Tüm sayfalar için CSS ve küçük hareket betiği (app.py bir kez çağırır)."""
    apply_mode()
    st.markdown(_css(), unsafe_allow_html=True)
    st.html(_MOTION, unsafe_allow_javascript=True)


def page_header(title: str, sub: str = "", chips=(), demo: bool = False):
    """Sayfa başlığı: koyu bant, sağda giriş ekranındaki fatura sütunlarının küçük bir yankısı."""
    chip_html = "".join(f'<span class="chip">{html.escape(c)}</span>' for c in chips)
    seed = zlib.crc32(title.encode())
    cols = [c for _, c in APPLIANCES.values()][:5]
    bars = ""
    for k in range(9):  # her sayfada farklı ama sabit yükseklikler
        segs = ""
        for j, c in enumerate(cols):
            h = 6 + (seed >> ((k * 5 + j) % 27) & 7) * 3
            segs += f'<i style="background:{c};height:{h}px"></i>'
        bars += f'<span style="animation-delay:{.05 * k:.2f}s">{segs}</span>'
    st.markdown(f'<div class="pg-hero"><div class="pg-txt"><h1 class="nilm-title">{html.escape(title)}</h1>'
                f'{f"<p class=nilm-sub>{html.escape(sub)}</p>" if sub else ""}<div class="pg-chips">{chip_html}</div></div>'
                f'<div class="pg-bars" aria-hidden="true">{bars}</div></div>', unsafe_allow_html=True)


def mode_toggle():
    """Sol panelde aydınlık/karanlık düğmesi. Tıklama hareket betiğinde işlenir (sayfa geçiş animasyonuyla)."""
    light = MODE == "light"
    to = "dark" if light else "light"
    st.markdown(f'<div class="nl-mode{" is-light" if light else ""}" role="button" tabindex="0" data-to="{to}" '
                f'aria-label="{"Karanlık" if light else "Aydınlık"} görünüme geç"><span class="nl-track"><i class="st1"></i><i class="st2"></i>'
                f'<span class="nl-knob"></span></span><span><b>{"Aydınlık" if light else "Karanlık"} görünüm</b>'
                f'<small>{"Karanlığa" if light else "Aydınlığa"} geçmek için dokun</small></span></div>', unsafe_allow_html=True)


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
                f'<div class="{cls}" data-k="{html.escape(c["lab"])}">{c["num"]}{unit}</div><div class="sub">{html.escape(c.get("sub", ""))}</div></div>')
    st.markdown(f'<div class="strip">{out}</div>', unsafe_allow_html=True)


def bill_strip(bill: pd.DataFrame):
    """Fatura özeti. 'other' satırı varsa: sayaç toplamı, cihazların gerçek ve tahmin edilen tutarı."""
    dev = bill.drop(index="other", errors="ignore")
    real_tl, pred_tl = dev["Gerçek (TL)"].sum(), dev["Tahmin (TL)"].sum()
    diff = pred_tl - real_tl
    pct = (diff / real_tl * 100) if real_tl else 0.0
    tone = "ok" if abs(pct) < 5 else ("over" if diff > 0 else "under")
    word = "fazla" if diff > 0 else "eksik"
    if "other" in bill.index:
        total = bill["Gerçek (TL)"].sum()
        strip([dict(lab="Toplam fatura (sayaç)", num=f"{total:,.2f}", unit="TL", sub=f"{bill['Gerçek (kWh)'].sum():,.1f} kWh"),
               dict(lab=f"{len(dev)} cihazın gerçek payı", num=f"{real_tl:,.2f}", unit="TL", sub=f"faturanın %{real_tl / total * 100 if total else 0:.0f}'i"),
               dict(lab="Modelin tahmini", num=f"{pred_tl:,.2f}", unit="TL", sub=f"{diff:+,.2f} TL, %{abs(pct):.1f} {word}", tone=tone)])
        return
    strip([dict(lab="Gerçek fatura", num=f"{real_tl:,.2f}", unit="TL", sub=f"{dev['Gerçek (kWh)'].sum():,.2f} kWh"),
           dict(lab="Tahmin edilen fatura", num=f"{pred_tl:,.2f}", unit="TL", sub=f"{dev['Tahmin (kWh)'].sum():,.2f} kWh"),
           dict(lab="Fark", num=f"{diff:+,.2f}", unit="TL", sub=f"%{abs(pct):.1f} {word} tahmin", tone=tone)])


def callout(text_html: str):
    """Kısa özet cümlesi; text_html içinde <b> kullanılabilir (kullanıcı verisi değil, kod üretir)."""
    st.markdown(f'<div class="callout">{text_html}</div>', unsafe_allow_html=True)


def summary_sentence(bill: pd.DataFrame) -> str:
    """Fatura tablosundan otomatik özet cümlesi (sunumda anlatılacak ana mesaj). 'Diğer' satırı hesaba katılmaz."""
    bill = bill.drop(index="other", errors="ignore")
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
    dev = bill.drop(index="other", errors="ignore")
    peak = max(dev["Hata (TL)"].max(), 1e-9)
    total_real = max(bill["Gerçek (TL)"].sum(), 1e-9)
    rows = ""
    for k, (a, r) in enumerate(bill.iterrows()):
        share = r["Gerçek (TL)"] / total_real * 100
        is_other = a == "other"
        err = ('<span class="muted" title="Sayaçtan kalan enerji; hatası cihazlardaki hatanın tersidir">—</span>' if is_other else
               f'<span class="errbar" style="width:{max(2, int(r["Hata (TL)"] / peak * 60))}px"></span>{r["Hata (TL)"]:,.2f}')
        rows += (f'<tr class="{"oth" if is_other else ""}" style="animation-delay:{.04 * k:.2f}s">'
                 f'<td><span class="dot" style="background:{color(a)}"></span>{html.escape(tr(a))}</td>'
                 f'<td><span class="share" style="width:{max(2, int(share * 1.6))}px;background:{color(a)}"></span>%{share:.1f}</td>'
                 f'<td>{r["Gerçek (kWh)"]:,.2f}</td><td>{r["Gerçek (TL)"]:,.2f}</td><td>{r["Tahmin (TL)"]:,.2f}</td><td>{err}</td></tr>')
    t = bill.sum(numeric_only=True)
    foot = (f'<tr><td>Toplam</td><td>%100</td><td>{t["Gerçek (kWh)"]:,.2f}</td><td>{t["Gerçek (TL)"]:,.2f}</td>'
            f'<td>{t["Tahmin (TL)"]:,.2f}</td><td>{dev["Hata (TL)"].sum():,.2f}</td></tr>')
    st.markdown(f"""
<table class="ledger"><thead><tr><th>Cihaz</th><th>Fatura payı</th><th>Gerçek tüketim (kWh)</th><th>Gerçek (TL)</th><th>Tahmin (TL)</th><th>Mutlak hata (TL)</th></tr></thead>
<tbody>{rows}</tbody><tfoot>{foot}</tfoot></table>""", unsafe_allow_html=True)


def share_table(tl: pd.Series, kwh: pd.Series):
    """Kullanıcının faturasının kalemleri (tahmini): cihaz, pay, kWh, TL."""
    total = max(float(tl.sum()), 1e-9)
    rows = ""
    for k, a in enumerate(tl.index):
        share = tl[a] / total * 100
        rows += (f'<tr class="{"oth" if a == "other" else ""}" style="animation-delay:{.04 * k:.2f}s">'
                 f'<td><span class="dot" style="background:{color(a)}"></span>{html.escape(tr(a))}</td>'
                 f'<td><span class="share" style="width:{max(2, int(share * 1.6))}px;background:{color(a)}"></span>%{share:.1f}</td>'
                 f'<td>{kwh[a]:,.1f}</td><td>{tl[a]:,.2f}</td></tr>')
    st.markdown(f'<table class="ledger"><thead><tr><th>Cihaz</th><th>Pay</th><th>kWh</th><th>TL</th></tr></thead>'
                f'<tbody>{rows}</tbody><tfoot><tr><td>Toplam</td><td>%100</td><td>{kwh.sum():,.1f}</td><td>{tl.sum():,.2f}</td></tr></tfoot></table>',
                unsafe_allow_html=True)


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
                f'<div class="v" data-k="side">{html.escape(value)}<small>{html.escape(unit)}</small></div>'
                f'<div class="s">{html.escape(sub)}</div><div class="bar">{bar}</div></div>', unsafe_allow_html=True)


def model_pill(m: str) -> str:
    dots = ["\U0001F534", "\U0001F7E2", "\U0001F535", "\U0001F7E1", "\U0001F7E3", "\u26AB"]
    i = _MODELS.index(m) if m in _MODELS else 0
    return f"{dots[i % len(dots)]} {m}"


def side_user(name: str, sub: str):
    st.markdown(f'<div class="sideuser"><span class="av">{html.escape(name[:1].upper())}</span>'
                f'<span><b>{html.escape(name[:1].upper() + name[1:])}</b><br><small>{html.escape(sub)}</small></span></div>', unsafe_allow_html=True)


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
            big = f'<div class="big" data-k="{html.escape(c["name"])}">{c["big"]}{unit}</div><div class="big-sub">{html.escape(c.get("sub", ""))}</div>'
        rows = "".join(f'<div class="kv"><span>{html.escape(k)}</span><b class="{"win" if w else ""}">{html.escape(v)}</b></div>'
                       for k, v, w in c.get("rows", []))
        out += (f'<div class="card{" first" if c.get("first") else ""}" style="--c:{c["color"]};min-height:{min_h}px">'
                f'<div class="nm">{rk}<span>{html.escape(c["name"])}</span>{tag}</div>{big}{rows}</div>')
    st.markdown(f'<div class="cards">{out}</div>', unsafe_allow_html=True)
