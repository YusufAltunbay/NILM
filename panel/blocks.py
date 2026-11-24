"""İki sayfada ortak kullanılan arayüz blokları."""
import streamlit as st

from panel import charts, theme

_VIEWS = {
    "Şerit": "Üst çubuk gerçek faturayı, alt çubuk tahmini gösterir. Dilimler aynı ölçekte olduğu için farklar doğrudan görülür.",
    "Dikey şerit": "Sol sütun gerçek, sağ sütun tahmin edilen fatura. Dilimlerin yüksekliği her cihazın tutarıdır (TL).",
    "Halka": "Her halka, faturanın cihazlar arasındaki payını gösterir. Ortadaki sayı toplam tutardır (TL).",
    "Çubuk": "Her cihaz için gerçek (dolu çubuk) ve tahmin edilen (açık dolgulu çubuk) fatura yan yana.",
}


def bill_view(bill, key: str, default: str = "Şerit"):
    """Fatura için Şerit / Dikey şerit / Halka / Çubuk seçicisi ve seçilen grafik."""
    view = st.segmented_control("Görünüm", list(_VIEWS), default=default, key=key, label_visibility="collapsed") or default
    st.caption(_VIEWS[view])
    theme.legend(list(bill.index))
    chart = {"Şerit": charts.ribbon, "Dikey şerit": charts.stacked, "Halka": charts.donut, "Çubuk": charts.bars}[view]
    st.altair_chart(chart(bill), width="stretch")
