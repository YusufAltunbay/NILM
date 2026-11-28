"""Basit oturum açma: kullanıcılar yerel bir SQLite dosyasında, parolalar tuzlu PBKDF2 ile saklanır.
Her kullanıcı kayıtta bir ev seçer ve panelde yalnızca o evin verisini görür.
'Misafir' girişi tüm evleri gösterir (sunum için)."""
import base64
import html
import hashlib
import hmac
import re
import secrets
import sqlite3
import time
from pathlib import Path

import streamlit as st

DB = Path(__file__).resolve().parents[1] / ".panel" / "users.db"
_NAME = re.compile(r"^[a-z0-9_.]{3,24}$")
ITER = 200_000


def _conn(db=None):
    path = Path(db or DB)
    path.parent.mkdir(parents=True, exist_ok=True)
    c = sqlite3.connect(path)
    c.execute("CREATE TABLE IF NOT EXISTS users(username TEXT PRIMARY KEY, salt TEXT NOT NULL, pw TEXT NOT NULL, house INTEGER NOT NULL)")
    if "bill" not in [r[1] for r in c.execute("PRAGMA table_info(users)")]:  # eski veritabanı: sütunu ekle
        c.execute("ALTER TABLE users ADD COLUMN bill REAL")
    return c


def _hash(password: str, salt: str) -> str:
    return hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), bytes.fromhex(salt), ITER).hex()


def create_user(username: str, password: str, house: int, db=None, bill: float | None = None):
    """-> hata metni ya da None (başarılı)."""
    username = username.strip().lower()
    if not _NAME.match(username):
        return "Kullanıcı adı 3-24 karakter olmalı (harf, rakam, nokta, alt çizgi)."
    if len(password) < 6:
        return "Parola en az 6 karakter olmalı."
    salt = secrets.token_hex(16)
    try:
        with _conn(db) as c:
            c.execute("INSERT INTO users(username, salt, pw, house, bill) VALUES (?,?,?,?,?)",
                      (username, salt, _hash(password, salt), int(house), float(bill) if bill else None))
    except sqlite3.IntegrityError:
        return "Bu kullanıcı adı alınmış."
    return None


def verify(username: str, password: str, db=None):
    """-> {'name', 'house'} ya da None."""
    with _conn(db) as c:
        row = c.execute("SELECT salt, pw, house, bill FROM users WHERE username=?", (username.strip().lower(),)).fetchone()
    salt = row[0] if row else "00" * 16  # kullanıcı yokken de aynı süreyi harca
    ok = hmac.compare_digest(_hash(password, salt), row[1] if row else "")
    if not (row and ok):
        time.sleep(0.4)
        return None
    return {"name": username.strip().lower(), "house": int(row[2]), "bill": row[3]}


def set_bill(username: str, bill: float | None, db=None):
    """Kullanıcının aylık faturasını kaydeder (0 ya da None: girilmemiş)."""
    with _conn(db) as c:
        c.execute("UPDATE users SET bill=? WHERE username=?", (float(bill) if bill else None, username.strip().lower()))


def current():
    return st.session_state.get("user")


def logout():
    st.session_state.pop("user", None)


_LOGIN_CSS = """
<style>
[data-testid='stSidebar'], [data-testid='stExpandSidebarButton'], [data-testid='stSidebarCollapsedControl'], [data-testid='stLogo'],
[data-testid='stSidebarLogo'], [data-testid='stHeaderLogo'], [data-testid='stHeader'] img { display: none !important; }
.stApp { background: radial-gradient(1200px 700px at 18% 30%, #134A57 0%, rgba(19,74,87,0) 60%),
                     linear-gradient(160deg, #0B1626 0%, #0F2A42 55%, #0B3B45 100%) !important; }
.block-container { max-width: 1240px !important; padding-top: 0 !important; }
/* arkadaki yarı saydam logo: faturayı dilimleyen sütun */
.lg-hero { position: relative; z-index: 1; min-height: 100vh; display: flex; flex-direction: column; justify-content: center; padding: 2rem 2rem 2rem 0; }
.lg-brand { display: flex; align-items: center; gap: 12px; color: #fff; margin-bottom: 1.6rem; }
.lg-brand b { font-family: 'Bricolage','Segoe UI',sans-serif; font-size: 1.6rem; letter-spacing: .02em; }
.lg-brand span { color: #8FA3BF; font-size: .95rem; }
.lg-hero h1 { font-family: 'Bricolage','Segoe UI',sans-serif; color: #fff !important; font-size: clamp(2.6rem, 4.6vw, 4.4rem);
              font-weight: 800; line-height: .98; letter-spacing: -0.035em; margin: 0 0 1.2rem 0; max-width: 11ch; padding: 0 !important; text-wrap: balance;
              animation: lg-in .6s cubic-bezier(.2,.8,.2,1) both; }
/* başlığın altında faturanın renkli dilimleri, soldan sağa dolar */
.lg-rule { display: flex; height: 6px; width: min(420px, 80%); border-radius: 4px; overflow: hidden; gap: 3px; margin: 0 0 1.4rem 0; }
.lg-rule i { display: block; height: 100%; transform-origin: left; animation: lg-x .5s cubic-bezier(.2,.8,.2,1) both; }
@keyframes lg-x { from { transform: scaleX(0); } to { transform: scaleX(1); } }
.lg-hero p { animation: lg-in .6s cubic-bezier(.2,.8,.2,1) .1s both; color: #B9C7DA; font-size: 1.08rem; line-height: 1.6; max-width: 46ch; margin: 0 0 1.6rem 0; }
.lg-demo { display: flex; align-items: flex-end; gap: 26px; }
.lg-col { width: 58px; height: 150px; display: flex; flex-direction: column-reverse; border-radius: 10px; overflow: hidden;
          background: rgba(255,255,255,.05); box-shadow: 0 20px 40px -20px rgba(0,0,0,.6); }
.lg-col i { display: block; width: 100%; transform-origin: bottom; animation: lg-grow .55s cubic-bezier(.2,.8,.2,1) both; }
.lg-col i + i { border-bottom: 2px solid #0F2A42; }
.lg-keys { display: flex; flex-direction: column; gap: 5px; padding-bottom: 6px; }
.lg-keys div { color: #D5E0EE; font-size: .92rem; display: flex; align-items: center; gap: 9px; animation: lg-fade .5s ease both; }
.lg-keys i { width: 11px; height: 11px; border-radius: 3px; display: inline-block; }
.lg-facts { display: flex; gap: 30px; margin-top: 1.6rem; color: #8FA3BF; font-size: .9rem; }
.lg-facts b { display: block; color: #fff; font-family: 'Bricolage','Segoe UI',sans-serif; font-size: 2rem; font-weight: 700; line-height: 1.1; }
.lg-facts div { padding-left: 14px; border-left: 2px solid rgba(255,255,255,.14); }
@keyframes lg-grow { from { transform: scaleY(0); } to { transform: scaleY(1); } }
@keyframes lg-fade { from { opacity: 0; transform: translateX(-6px); } to { opacity: 1; transform: none; } }
@keyframes lg-in { from { opacity: 0; transform: translateY(14px); } to { opacity: 1; transform: none; } }
/* form kartı */
.st-key-loginbox { position: relative; z-index: 1; background: rgba(17,31,51,.72); border: 1px solid rgba(255,255,255,.10);
                   backdrop-filter: blur(14px); -webkit-backdrop-filter: blur(14px); border-radius: 22px; padding: 26px 28px 22px 28px !important;
                   box-shadow: 0 40px 80px -40px rgba(0,0,0,.9), inset 0 1px 0 rgba(255,255,255,.06); animation: lg-in .5s ease .15s both; }
.st-key-loginbox h3 { font-family: 'Bricolage','Segoe UI',sans-serif; font-size: 1.35rem; margin: 0 0 .2rem 0; padding: 0; color: #fff; }
.st-key-loginbox [data-testid="stForm"] { border: none; padding: 0; }
.st-key-guest button { background: transparent !important; color: #D5E0EE !important; border: 1px solid rgba(255,255,255,.25) !important; }
.st-key-guest button:hover { border-color: #12B5A6 !important; color: #fff !important; }
.st-key-guest { position: relative; z-index: 1; margin-top: .4rem; }
@media (max-width: 900px) { .lg-hero { min-height: auto; padding: 2rem 0 1rem 0; } .st-key-loginbox { margin-top: 0; } }
</style>
"""


def possessive(name: str) -> str:
    """'kamil' -> "Kamil'in", 'ali' -> "Ali'nin", 'murat' -> "Murat'ın" (Türkçe ünlü uyumu)."""
    n = name.strip()
    n = n[:1].upper() + n[1:]
    vowels = [ch for ch in n.lower() if ch in "aeıioöuü"]
    last = vowels[-1] if vowels else "e"
    v = {"a": "ı", "ı": "ı", "e": "i", "i": "i", "o": "u", "u": "u", "ö": "ü", "ü": "ü"}[last]
    return f"{n}'{'n' if n[-1].lower() in 'aeıioöuü' else ''}{v}n"


def _hero(pred):
    from panel import theme
    # Örnek fatura sütunu: seçili ilk modelin cihaz payları (veriden, sabit değil)
    sub = pred[pred["house"] == pred["house"].min()]
    first = sub["model"].cat.categories[0] if hasattr(sub["model"], "cat") else sub["model"].iloc[0]
    e = sub[sub["model"] == first].groupby("appliance", observed=True)["appliance_w"].mean()
    apps = theme.ordered(list(e.index))
    tot = float(e.sum()) or 1.0
    segs = "".join(f'<i style="background:{theme.color(a)};height:{e[a] / tot * 100:.1f}%;animation-delay:{.25 + k * .16:.2f}s"></i>'
                   for k, a in enumerate(apps))
    keys = "".join(f'<div style="animation-delay:{.35 + k * .16:.2f}s"><i style="background:{theme.color(a)}"></i>{html.escape(theme.tr(a))}'
                   f' <span style="color:#8FA3BF">%{e[a] / tot * 100:.0f}</span></div>' for k, a in enumerate(reversed(apps)))
    rule = "".join(f'<i style="background:{theme.color(a)};width:{e[a] / tot * 100:.1f}%;animation-delay:{.2 + k * .08:.2f}s"></i>'
                   for k, a in enumerate(apps))
    facts = [(pred["appliance"].nunique(), "cihaz"), (pred["model"].nunique(), "model"), (pred["house"].nunique(), "ev")]
    fact_html = "".join(f"<div><b>{n}</b>{t}</div>" for n, t in facts)
    svg = base64.b64encode((Path(__file__).parent / "assets" / "logo.svg").read_bytes()).decode()
    # arkadaki yarı saydam büyük logo
    st.markdown("<style>.stApp::before { content: ''; position: fixed; inset: auto -5vw -2vh auto; width: 60vw; height: 15vw; z-index: 0;"
                f"background: url(data:image/svg+xml;base64,{svg}) no-repeat right bottom / contain; opacity: .07; pointer-events: none; }}"
                "@media (max-width: 900px) { .stApp::before { display: none; } }</style>", unsafe_allow_html=True)
    st.markdown(f'''<div class="lg-hero">
  <div class="lg-brand"><img src="data:image/svg+xml;base64,{svg}" style="height:46px"></div>
  <h1>Faturanı cihaz cihaz gör.</h1>
  <div class="lg-rule">{rule}</div>
  <p>Evin tek sayacından ölçülen tüketimi, makine öğrenmesi modelleri buzdolabı, çamaşır makinesi, su ısıtıcısı gibi cihazlara ayırır.</p>
  <div class="lg-demo"><div class="lg-col">{segs}</div><div class="lg-keys">{keys}</div></div>
  <div class="lg-facts">{fact_html}</div>
</div>''', unsafe_allow_html=True)


def login_page():
    from panel import data, theme
    theme.inject()
    st.markdown(_LOGIN_CSS, unsafe_allow_html=True)
    pred, _, _ = data.load()
    houses = sorted(int(h) for h in pred["house"].unique())
    home = next((h for h in data.config.UNSEEN_HOUSES if h in houses), houses[0])  # yeni hesaplara verilen örnek ev
    left, right = st.columns([1.25, 1], gap="large", vertical_alignment="center")
    with left:
        _hero(pred)
    with right:
        with st.container(key="loginbox"):
            st.markdown("### Hoş geldin")
            t_in, t_up = st.tabs(["Giriş yap", "Kayıt ol"])
            with t_in:
                with st.form("giris", border=False):
                    u = st.text_input("Kullanıcı adı")
                    p = st.text_input("Parola", type="password")
                    if st.form_submit_button("Giriş yap", type="primary", width="stretch"):
                        user = verify(u, p)
                        if user:
                            st.session_state["user"] = user
                            st.rerun()
                        st.error("Kullanıcı adı ya da parola hatalı.")
            with t_up:
                with st.form("kayit", border=False):
                    u = st.text_input("Kullanıcı adı", key="reg_u")
                    p = st.text_input("Parola", type="password", key="reg_p")
                    p2 = st.text_input("Parola (tekrar)", type="password")
                    b = st.number_input("Aylık elektrik faturan (TL, isteğe bağlı)", 0.0, 100000.0, 0.0, 50.0,
                                        help="Tasarruf hesapları senin faturana göre ölçeklenir. Sonra da değiştirebilirsin.")
                    st.caption("Hesabın, ölçüm verisi olan örnek bir evle açılır.")
                    if st.form_submit_button("Hesap oluştur", type="primary", width="stretch"):
                        err = "Parolalar aynı değil." if p != p2 else create_user(u, p, home, bill=b)
                        if err:
                            st.error(err)
                        else:
                            st.session_state["user"] = {"name": u.strip().lower(), "house": int(home), "bill": b or None}
                            st.rerun()
        if st.button("Misafir olarak devam et (tüm evler)", width="stretch", key="guest"):
            st.session_state["user"] = {"name": "Misafir", "house": None}
            st.rerun()
