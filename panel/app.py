"""NILM web paneli. Çalıştırma: streamlit run panel/app.py"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import streamlit as st

st.set_page_config(page_title="NILM Paneli", layout="wide")

pages = [
    st.Page("views/tuketim.py", title="Cihaz tüketimi", icon=":material/bolt:", default=True),
    st.Page("views/zaman_serisi.py", title="Zaman serisi", icon=":material/show_chart:"),
    st.Page("views/karsilastirma.py", title="Model karşılaştırma", icon=":material/compare:"),
    st.Page("views/gorulmeyen_ev.py", title="Görülmeyen ev", icon=":material/home:"),
]
st.navigation(pages).run()
