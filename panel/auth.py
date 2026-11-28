"""Basit oturum açma: kullanıcılar yerel bir SQLite dosyasında, parolalar tuzlu PBKDF2 ile saklanır.
Her kullanıcı kayıtta bir ev seçer ve panelde yalnızca o evin verisini görür.
'Misafir' girişi tüm evleri gösterir (sunum için)."""
import base64
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


def login_page():
    from panel import data, theme
    theme.inject()
    st.markdown("<style>[data-testid='stSidebar'], [data-testid='stExpandSidebarButton'], [data-testid='stSidebarCollapsedControl'], [data-testid='stLogo'], [data-testid='stSidebarLogo'], [data-testid='stHeaderLogo'], [data-testid='stHeader'] img"
                "{display:none !important}</style>", unsafe_allow_html=True)
    pred, _, _ = data.load()
    houses = sorted(int(h) for h in pred["house"].unique())
    _, mid, _ = st.columns([1, 1.15, 1])
    with mid:
        svg = base64.b64encode((Path(__file__).parent / "assets" / "logo.svg").read_bytes()).decode()
        st.markdown(f'<div style="background:#0E1B2E;border-radius:16px;padding:14px 20px;display:inline-block">'
                    f'<img src="data:image/svg+xml;base64,{svg}" style="height:54px"></div>', unsafe_allow_html=True)
        st.markdown('<h1 class="nilm-title" style="font-size:1.9rem">Evinin tüketimini cihaz cihaz takip et</h1>', unsafe_allow_html=True)
        t_in, t_up = st.tabs(["Giriş yap", "Kayıt ol"])
        with t_in:
            with st.form("giris"):
                u = st.text_input("Kullanıcı adı")
                p = st.text_input("Parola", type="password")
                if st.form_submit_button("Giriş yap", type="primary", width="stretch"):
                    user = verify(u, p)
                    if user:
                        st.session_state["user"] = user
                        st.rerun()
                    st.error("Kullanıcı adı ya da parola hatalı.")
        with t_up:
            with st.form("kayit"):
                u = st.text_input("Kullanıcı adı", key="reg_u")
                p = st.text_input("Parola", type="password", key="reg_p")
                p2 = st.text_input("Parola (tekrar)", type="password")
                h = st.selectbox("Evin", houses, format_func=data.house_name)
                b = st.number_input("Aylık elektrik faturan (TL, isteğe bağlı)", 0.0, 100000.0, 0.0, 50.0,
                                    help="Tasarruf hesapları senin faturana göre ölçeklenir. Sonra da değiştirebilirsin.")
                if st.form_submit_button("Hesap oluştur", type="primary", width="stretch"):
                    err = "Parolalar aynı değil." if p != p2 else create_user(u, p, h, bill=b)
                    if err:
                        st.error(err)
                    else:
                        st.session_state["user"] = {"name": u.strip().lower(), "house": int(h), "bill": b or None}
                        st.rerun()
        if st.button("Misafir olarak devam et (tüm evler)", width="stretch"):
            st.session_state["user"] = {"name": "Misafir", "house": None}
            st.rerun()
