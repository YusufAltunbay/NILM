"""Altair grafikleri. Tüm grafikler aynı sakin görünümü paylaşır."""
import altair as alt
import pandas as pd

from panel import theme

FONT = "Figtree, Segoe UI, system-ui, sans-serif"


def _style(chart):
    return (chart.properties(padding={"left": 8, "right": 34, "top": 8, "bottom": 8}).configure(background="#FFFFFF").configure_view(stroke=None)
            .configure_axis(labelFont=FONT, titleFont=FONT, labelColor=theme.MUTED, titleColor=theme.MUTED,
                            gridColor="#E8EDF4", domainColor="#CBD5E3", tickColor="#CBD5E3", labelFontSize=12, titleFontSize=12)
            .configure_legend(labelFont=FONT, titleFont=FONT, labelColor=theme.INK, titleColor=theme.MUTED, orient="top", symbolType="square"))


def ribbon(bill: pd.DataFrame):
    """Fatura şeridi: üst satır gerçek, alt satır tahmin; cihaz dilimleri aynı ölçekte hizalı."""
    rows = []
    for name, col in (("Gerçek", "Gerçek (TL)"), ("Tahmin", "Tahmin (TL)")):
        total = max(bill[col].sum(), 1e-9)
        start = 0.0
        for a, v in bill[col].items():
            share = v / total
            rows.append(dict(Satir=name, Cihaz=theme.tr(a), TL=round(v, 2), Pay=round(share * 100, 1),
                             start=start, end=start + v, label=theme.tr(a) if share >= 0.13 else ""))
            start += v
    d = pd.DataFrame(rows)
    names, colors = theme.palette(list(bill.index))
    row_enc = alt.Y("Satir:N", sort=["Gerçek", "Tahmin"], title=None,
                    axis=alt.Axis(domain=False, ticks=False, labelFontSize=14, labelColor=theme.INK, labelPadding=10))
    bars = alt.Chart(d).mark_bar(size=50, cornerRadius=3, stroke="#FFFFFF", strokeWidth=2).encode(
        x=alt.X("start:Q", title="Fatura (TL)", axis=alt.Axis(grid=False, format=",.0f", tickCount=6, labelOverlap=True)), x2="end:Q", y=row_enc,
        color=alt.Color("Cihaz:N", scale=alt.Scale(domain=names, range=colors), legend=None),
        tooltip=[alt.Tooltip("Satir:N", title="Satır"), alt.Tooltip("Cihaz:N"), alt.Tooltip("TL:Q", format=",.2f", title="Tutar (TL)"),
                 alt.Tooltip("Pay:Q", format=".1f", title="Fatura payı (%)")])
    text = alt.Chart(d).mark_text(align="left", dx=9, color="white", fontWeight=600, fontSize=13, font=FONT).encode(
        x="start:Q", y=row_enc, text="label:N")
    return _style((bars + text).properties(height=190))


def series(df: pd.DataFrame, appliance: str, show_aggregate: bool):
    """Gerçek (dolgulu alan) ve tahmin (kesikli çizgi) zaman serisi; üzerine gelince değerleri gösterir."""
    c = theme.color(appliance)
    x = alt.X("timestamp:T", title=None, axis=alt.Axis(format="%d.%m %H:%M", grid=False))
    y = alt.Y("Gerçek:Q", title="Güç (W)")
    nearest = alt.selection_point(fields=["timestamp"], nearest=True, on="mouseover", empty=False, clear="mouseout")
    layers = []
    if show_aggregate:
        layers.append(alt.Chart(df).mark_line(color="#B6C2D3", strokeWidth=1.2).encode(x=x, y=alt.Y("Toplam:Q", title="Güç (W)")))
    layers.append(alt.Chart(df).mark_area(color=c, opacity=0.28, line={"color": c, "strokeWidth": 1.6}).encode(x=x, y=y))
    layers.append(alt.Chart(df).mark_line(color=theme.INK, strokeDash=[5, 3], strokeWidth=1.8).encode(x=x, y=alt.Y("Tahmin:Q")))
    tips = [alt.Tooltip("timestamp:T", format="%d.%m %H:%M:%S", title="Zaman"),
            alt.Tooltip("Gerçek:Q", format=".0f", title="Gerçek (W)"), alt.Tooltip("Tahmin:Q", format=".0f", title="Tahmin (W)")]
    layers.append(alt.Chart(df).mark_point(opacity=0).encode(x=x, y=y).add_params(nearest))
    layers.append(alt.Chart(df).mark_rule(color="#94A3B8").encode(x=x, tooltip=tips).transform_filter(nearest))
    return _style(alt.layer(*layers).properties(height=360).interactive(bind_y=False))


def model_bars(r: pd.DataFrame, metric: str, title: str):
    models = sorted(r["model"].unique())
    colors = [theme.MODEL_COLORS[i % len(theme.MODEL_COLORS)] for i in range(len(models))]
    d = r.groupby(["appliance", "model"], as_index=False)[metric].mean()
    d["Cihaz"] = d["appliance"].map(theme.tr)
    order = [theme.tr(a) for a in theme.APPLIANCES if theme.tr(a) in set(d["Cihaz"])] or sorted(d["Cihaz"].unique())
    ch = alt.Chart(d).mark_bar(cornerRadiusTopLeft=3, cornerRadiusTopRight=3).encode(
        x=alt.X("Cihaz:N", sort=order, title=None, axis=alt.Axis(labelAngle=0, labelFontSize=12, labelLimit=140)),
        xOffset=alt.XOffset("model:N"),
        y=alt.Y(f"{metric}:Q", title=title),
        color=alt.Color("model:N", scale=alt.Scale(domain=models, range=colors), title="Model"),
        tooltip=[alt.Tooltip("Cihaz:N"), alt.Tooltip("model:N", title="Model"), alt.Tooltip(f"{metric}:Q", format=".3f", title=title)])
    return _style(ch.properties(height=330))
