"""NILM web paneli. Çalıştırma: streamlit run panel/app.py"""
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))

import streamlit as st

from panel import auth, theme

st.set_page_config(page_title="NILM paneli", page_icon=":material/bolt:", layout="wide")
theme.inject()
st.logo(str(HERE / "assets" / "logo.svg"), size="large")

user = auth.current()
script = auth.cookie_script()
if script:
    st.html(script, unsafe_allow_javascript=True)
if user is None:
    st.navigation([st.Page(auth.login_page, title="Giriş", url_path="giris")], position="hidden").run()
    st.stop()
st.session_state.pop("logged_out", None)
guest = user.get("house") is None   # misafir: sunum ve değerlendirme için tüm evler ve sayfalar

pages = [
    st.Page("views/nasil_calisir.py", title="Nasıl çalışır", icon=":material/lightbulb:"),
    st.Page("views/tuketim.py", title="Fatura dağılımı", icon=":material/receipt_long:", default=True),
    st.Page("views/zaman_serisi.py", title="Zaman serisi", icon=":material/show_chart:"),
    st.Page("views/karsilastirma.py", title="Model karşılaştırma", icon=":material/compare_arrows:"),
    st.Page("views/tasarruf.py", title="Tasarruf", icon=":material/savings:"),
]
if guest:  # model değerlendirme sayfası; kendi evini izleyen kullanıcıya gerekmez
    pages.append(st.Page("views/gorulmeyen_ev.py", title="Görülmeyen ev", icon=":material/home_work:"))
st.navigation(pages).run()
