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
                             start=start, end=start + v))
            start += v
    d = pd.DataFrame(rows)
    names, colors = theme.palette(list(bill.index))
    row_enc = alt.Y("Satir:N", sort=["Gerçek", "Tahmin"], title=None,
                    axis=alt.Axis(domain=False, ticks=False, labelFontSize=14, labelColor=theme.INK, labelPadding=10))
    xmax = float(d["end"].max()) or 1.0
    bars = alt.Chart(d).mark_bar(height={"band": 0.72}, cornerRadius=3, stroke="#FFFFFF", strokeWidth=2).encode(
        x=alt.X("start:Q", title="Fatura (TL)", scale=alt.Scale(domain=[0, xmax], nice=False),
                axis=alt.Axis(grid=False, format=",.0f", tickCount=6, labelOverlap=True)), x2="end:Q", y=row_enc,
        color=alt.Color("Cihaz:N", scale=alt.Scale(domain=names, range=colors), legend=None),
        tooltip=[alt.Tooltip("Satir:N", title="Satır"), alt.Tooltip("Cihaz:N"), alt.Tooltip("TL:Q", format=",.2f", title="Tutar (TL)"),
                 alt.Tooltip("Pay:Q", format=".1f", title="Fatura payı (%)")])
    # Etiket, dilimin ekrandaki genişliğine göre: sığıyorsa tam ad, sığmıyorsa kısaltılmış, hiç sığmıyorsa boş.
    fit = (f"floor((datum.end - datum.start) / {xmax} * width / 7.4) - 2")
    text = (alt.Chart(d).transform_calculate(n=fit).transform_calculate(
        label="datum.n >= length(datum.Cihaz) ? datum.Cihaz : (datum.n >= 4 ? substring(datum.Cihaz, 0, datum.n - 1) + '…' : '')")
        .mark_text(align="left", dx=9, color="white", fontWeight=600, fontSize=13, font=FONT).encode(
        tooltip=alt.value(None), x="start:Q", y=row_enc, text="label:N"))
    return _style((bars + text).properties(height=190))


def _rgba(hex_color: str, alpha: float) -> str:
    h = hex_color.lstrip("#")
    r, g, b = (int(h[i:i + 2], 16) for i in (0, 2, 4))
    return f"rgba({r},{g},{b},{alpha})"


def series(df: pd.DataFrame, appliance: str, show_aggregate: bool, bands: pd.DataFrame | None = None):
    """Gerçek güç (gradyanlı alan, adım çizgisi) ve tahmin (ince lacivert çizgi); imleçle değerleri gösterir."""
    c = theme.color(appliance)
    x = alt.X("timestamp:T", title=None, axis=alt.Axis(format="%d.%m %H:%M", grid=False, tickCount=6, labelFontSize=11, domain=False, ticks=False))
    yax = alt.Axis(tickCount=5, gridColor="#EDF1F6", gridDash=[2, 3], labelFontSize=11, domain=False, ticks=False)
    y = alt.Y("Gerçek:Q", title="Güç (W)", axis=yax)
    grad = alt.Gradient(gradient="linear", x1=1, x2=1, y1=1, y2=0,
                        stops=[alt.GradientStop(color=_rgba(c, 0.0), offset=0), alt.GradientStop(color=_rgba(c, 0.55), offset=1)])
    nearest = alt.selection_point(fields=["timestamp"], nearest=True, on="mouseover", empty=False, clear="mouseout")
    layers = []
    if bands is not None and not bands.empty:
        layers.append(alt.Chart(bands).mark_rect(color=c, opacity=0.06).encode(x=alt.X("start:T"), x2="end:T"))
    if show_aggregate:
        layers.append(alt.Chart(df).mark_line(color="#C9D3E0", strokeWidth=1, interpolate="step-after").encode(
            x=x, y=alt.Y("Toplam:Q", title="Güç (W)", axis=yax)))
    layers.append(alt.Chart(df).mark_area(color=grad, interpolate="step-after", line={"color": c, "strokeWidth": 1.6}).encode(x=x, y=y))
    layers.append(alt.Chart(df).mark_line(color=theme.INK, strokeWidth=1.7, interpolate="step-after").encode(x=x, y=alt.Y("Tahmin:Q")))
    tips = [alt.Tooltip("timestamp:T", format="%d.%m %H:%M:%S", title="Zaman"),
            alt.Tooltip("Gerçek:Q", format=".0f", title="Gerçek (W)"), alt.Tooltip("Tahmin:Q", format=".0f", title="Tahmin (W)")]
    layers.append(alt.Chart(df).mark_point(opacity=0).encode(x=x, y=y).add_params(nearest))
    layers.append(alt.Chart(df).mark_rule(color="#94A3B8", strokeDash=[3, 3]).encode(x=x, tooltip=tips).transform_filter(nearest))
    layers.append(alt.Chart(df).mark_circle(size=70, color=c, stroke="#FFFFFF", strokeWidth=2, opacity=1).encode(x=x, y=y).transform_filter(nearest))
    layers.append(alt.Chart(df).mark_circle(size=70, color=theme.INK, stroke="#FFFFFF", strokeWidth=2, opacity=1).encode(
        x=x, y=alt.Y("Tahmin:Q")).transform_filter(nearest))
    return _style(alt.layer(*layers).properties(height=380))


def donut(bill: pd.DataFrame):
    """İki halka: gerçek ve tahmin faturası; ortada toplam tutar."""
    names, colors = theme.palette(list(bill.index))
    w, h = 330, 290
    parts = []
    for title, col in (("Gerçek", "Gerçek (TL)"), ("Tahmin", "Tahmin (TL)")):
        d = pd.DataFrame({"Cihaz": [theme.tr(a) for a in bill.index], "TL": bill[col].round(2).to_numpy()})
        total = d["TL"].sum()
        d["Pay"] = (d["TL"] / max(total, 1e-9) * 100).round(1)
        arc = alt.Chart(d).mark_arc(innerRadius=88, outerRadius=138, stroke="#FFFFFF", strokeWidth=2).encode(
            theta=alt.Theta("TL:Q", stack=True),
            color=alt.Color("Cihaz:N", scale=alt.Scale(domain=names, range=colors), legend=None),
            tooltip=[alt.Tooltip("Cihaz:N"), alt.Tooltip("TL:Q", format=",.2f", title="Tutar (TL)"), alt.Tooltip("Pay:Q", format=".1f", title="Fatura payı (%)")])
        big = alt.Chart(pd.DataFrame({"t": [f"{total:,.0f}"]})).mark_text(
            fontSize=34, fontWeight=700, color=theme.INK, font="Bricolage Grotesque, " + FONT, align="center", baseline="middle").encode(
            text="t:N", x=alt.value(w / 2), y=alt.value(h / 2 - 10))
        small = alt.Chart(pd.DataFrame({"t": ["TL"]})).mark_text(
            fontSize=13, color=theme.MUTED, font=FONT, align="center", baseline="middle").encode(
            text="t:N", x=alt.value(w / 2), y=alt.value(h / 2 + 22))
        parts.append(alt.layer(arc, big, small).properties(
            width=w, height=h, title=alt.TitleParams(title, anchor="middle", fontSize=14, font=FONT, color=theme.INK, fontWeight=600)))
    return _style(alt.hconcat(*parts, spacing=70))


def bars(bill: pd.DataFrame):
    """Dikey, cihaz renkli çubuklar: dolu çubuk gerçek, açık dolgulu çubuk tahmin."""
    names, colors = theme.palette(list(bill.index))
    rows = []
    for seri, col in (("Gerçek", "Gerçek (TL)"), ("Tahmin", "Tahmin (TL)")):
        for a, v in bill[col].items():
            rows.append(dict(Cihaz=theme.tr(a), Seri=seri, TL=round(float(v), 2)))
    d = pd.DataFrame(rows)
    base = alt.Chart(d).encode(
        x=alt.X("Cihaz:N", sort=names, title=None, axis=alt.Axis(labelAngle=0, labelFontSize=12, labelColor=theme.INK, labelLimit=150, ticks=False, domain=False)),
        xOffset=alt.XOffset("Seri:N", sort=["Gerçek", "Tahmin"]),
        y=alt.Y("TL:Q", title="Fatura (TL)", axis=alt.Axis(format=",.0f", tickCount=5)))
    bar = base.mark_bar(cornerRadiusTopLeft=5, cornerRadiusTopRight=5, strokeWidth=2).encode(
        color=alt.Color("Cihaz:N", scale=alt.Scale(domain=names, range=colors), legend=None),
        stroke=alt.Stroke("Cihaz:N", scale=alt.Scale(domain=names, range=colors), legend=None),
        fillOpacity=alt.FillOpacity("Seri:N", scale=alt.Scale(domain=["Gerçek", "Tahmin"], range=[1.0, 0.28]), legend=None),
        tooltip=[alt.Tooltip("Cihaz:N"), alt.Tooltip("Seri:N"), alt.Tooltip("TL:Q", format=",.2f", title="Tutar (TL)")])
    txt = base.mark_text(dy=-8, fontSize=12, font=FONT, color=theme.INK, fontWeight=500).encode(tooltip=alt.value(None), text=alt.Text("TL:Q", format=",.1f"))
    return _style((bar + txt).properties(height=340))


def stacked(bill: pd.DataFrame):
    """Dikey şerit: iki sütun (gerçek, tahmin), cihaz dilimleri üst üste."""
    names, colors = theme.palette(list(bill.index))
    rows = []
    for seri, col in (("Gerçek", "Gerçek (TL)"), ("Tahmin", "Tahmin (TL)")):
        total = max(float(bill[col].sum()), 1e-9)
        start = 0.0
        for a, v in bill[col].items():
            v = float(v)
            rows.append(dict(Seri=seri, Cihaz=theme.tr(a), TL=round(v, 2), Pay=round(v / total * 100, 1),
                             start=start, end=start + v, mid=start + v / 2))
            start += v
    d = pd.DataFrame(rows)
    x = alt.X("Seri:N", sort=["Gerçek", "Tahmin"], title=None,
              axis=alt.Axis(labelAngle=0, labelFontSize=14, labelColor=theme.INK, ticks=False, domain=False, labelPadding=8))
    ymax = float(d["end"].max()) * 1.04 or 1.0
    bar = alt.Chart(d).mark_bar(width={"band": 0.55}, cornerRadius=4, stroke="#FFFFFF", strokeWidth=2).encode(
        x=x, y=alt.Y("start:Q", title="Fatura (TL)", scale=alt.Scale(domain=[0, ymax], nice=False), axis=alt.Axis(format=",.0f", tickCount=6)), y2="end:Q",
        color=alt.Color("Cihaz:N", scale=alt.Scale(domain=names, range=colors), legend=None),
        tooltip=[alt.Tooltip("Seri:N"), alt.Tooltip("Cihaz:N"), alt.Tooltip("TL:Q", format=",.2f", title="Tutar (TL)"),
                 alt.Tooltip("Pay:Q", format=".1f", title="Fatura payı (%)")])
    # Tutar etiketi yalnızca dilim yeterince yüksekse yazılır (yükseklik ekrandaki piksele göre hesaplanır).
    txt = (alt.Chart(d).transform_calculate(label=f"(datum.end - datum.start) / {ymax} * height >= 17 ? format(datum.TL, ',.0f') : ''")
           .mark_text(color="white", fontWeight=600, fontSize=13, font=FONT).encode(tooltip=alt.value(None), x=x, y="mid:Q", text="label:N"))
    return _style((bar + txt).properties(height=380))


def residual(df: pd.DataFrame):
    """Hata = tahmin - gerçek. Artı (fazla tahmin) kehribar, eksi (eksik tahmin) mavi."""
    x = alt.X("timestamp:T", title=None, axis=alt.Axis(format="%d.%m %H:%M", grid=False))
    d = df.assign(Hata=df["Tahmin"] - df["Gerçek"])
    tips = [alt.Tooltip("timestamp:T", format="%d.%m %H:%M:%S", title="Zaman"), alt.Tooltip("Hata:Q", format="+.0f", title="Hata (W)")]
    pos = alt.Chart(d).transform_calculate(v="datum.Hata > 0 ? datum.Hata : 0").mark_area(color="#F59E0B", opacity=0.75).encode(
        x=x, y=alt.Y("v:Q", title="Hata (W)"), tooltip=tips)
    neg = alt.Chart(d).transform_calculate(v="datum.Hata < 0 ? datum.Hata : 0").mark_area(color="#2F80ED", opacity=0.75).encode(
        x=x, y=alt.Y("v:Q", title="Hata (W)"))
    zero = alt.Chart(pd.DataFrame({"y": [0]})).mark_rule(color="#94A3B8").encode(y="y:Q")
    return _style((pos + neg + zero).properties(height=150))


def rank_bars(ozet: pd.DataFrame, metric: str, title: str, lower_better: bool):
    """Genel sıralama: modellerin cihazlar üzerinden ortalaması; en iyi üstte."""
    d = ozet[["Model", metric]].sort_values(metric, ascending=lower_better).reset_index(drop=True)
    models = list(d["Model"])
    all_models = sorted(models)
    palette = {m: theme.mcolor(m) for m in all_models}
    base = alt.Chart(d).encode(
        y=alt.Y("Model:N", sort=models, title=None, axis=alt.Axis(labelFontSize=14, labelColor=theme.INK, labelLimit=260, ticks=False, domain=False)),
        x=alt.X(f"{metric}:Q", title=title, axis=alt.Axis(tickCount=5)))
    bar = base.mark_bar(cornerRadiusEnd=4, height={"band": 0.6}).encode(
        color=alt.Color("Model:N", scale=alt.Scale(domain=all_models, range=[palette[m] for m in all_models]), legend=None),
        tooltip=[alt.Tooltip("Model:N"), alt.Tooltip(f"{metric}:Q", format=".3f", title=title)])
    txt = base.mark_text(align="left", dx=8, fontSize=13, font=FONT, color=theme.INK, fontWeight=600).encode(tooltip=alt.value(None), text=alt.Text(f"{metric}:Q", format=".3f"))
    return _style((bar + txt).properties(height=max(110, 56 * len(models))))


def heatmap(r: pd.DataFrame, metric: str, title: str, lower_better: bool):
    """Model x cihaz ısı haritası. Koyu renk daha iyi; her cihazın en iyi modeli çerçeveli."""
    d = r.groupby(["appliance", "model"], as_index=False)[metric].mean()
    d["Cihaz"] = d["appliance"].map(theme.tr)
    best = d.groupby("Cihaz")[metric].transform("min" if lower_better else "max")
    d["best"] = d[metric] == best
    # Renk, her cihazın içinde modeller arası göreli konumu gösterir (koyu = o cihazda daha iyi).
    g = d.groupby("Cihaz")[metric]
    lo, hi = g.transform("min"), g.transform("max")
    span = (hi - lo).where(hi > lo)
    d["score"] = ((d[metric] - lo) / span).fillna(0.7)
    if lower_better:
        d["score"] = (1 - d["score"]).where(span.notna(), 0.7)
    d["label"] = d[metric].map(lambda v: f"{v:.2f}" if abs(v) >= 0.1 else f"{v:.3f}")
    order = [theme.tr(a) for a in theme.ordered(d["appliance"].unique())]
    models = sorted(d["model"].unique())
    x = alt.X("Cihaz:N", sort=order, title=None, axis=alt.Axis(labelAngle=0, labelFontSize=12, labelColor=theme.INK, labelLimit=150, ticks=False, domain=False, orient="top"))
    y = alt.Y("model:N", sort=models, title=None, axis=alt.Axis(labelFontSize=13, labelColor=theme.INK, labelLimit=260, ticks=False, domain=False))
    scale = alt.Scale(domain=[0, 1], range=["#E4F5F2", "#0B6B61"])
    rect = alt.Chart(d).mark_rect(stroke="#FFFFFF", strokeWidth=3, cornerRadius=4).encode(
        x=x, y=y, color=alt.Color("score:Q", scale=scale, legend=None),
        tooltip=[alt.Tooltip("Cihaz:N"), alt.Tooltip("model:N", title="Model"), alt.Tooltip(f"{metric}:Q", format=".3f", title=title)])
    txt = alt.Chart(d).mark_text(fontSize=13, fontWeight=600, font=FONT).encode(tooltip=alt.value(None), 
        x=x, y=y, text="label:N",
        color=alt.condition(alt.datum.score > 0.5, alt.value("#FFFFFF"), alt.value(theme.INK)))
    layers = [rect, txt]
    if len(models) > 1:  # tek modelde "en iyi" çerçevesi anlamsız
        layers.insert(1, alt.Chart(d[d["best"]]).mark_rect(fill=None, stroke=theme.INK, strokeWidth=2.5, cornerRadius=4).encode(x=x, y=y))
    return _style(alt.layer(*layers).properties(height=max(110, 62 * len(models))))


def model_bars(r: pd.DataFrame, metric: str, title: str):
    """Cihaz bazında, modeller yan yana dikey çubuklar."""
    models = sorted(r["model"].unique())
    colors = [theme.mcolor(m) for m in models]
    d = r.groupby(["appliance", "model"], as_index=False)[metric].mean()
    d["Cihaz"] = d["appliance"].map(theme.tr)
    order = [theme.tr(a) for a in theme.ordered(d["appliance"].unique())]
    ch = alt.Chart(d).mark_bar(cornerRadiusTopLeft=4, cornerRadiusTopRight=4).encode(
        x=alt.X("Cihaz:N", sort=order, title=None, axis=alt.Axis(labelAngle=0, labelFontSize=12, labelLimit=140, ticks=False, domain=False)),
        xOffset=alt.XOffset("model:N"),
        y=alt.Y(f"{metric}:Q", title=title, axis=alt.Axis(tickCount=5)),
        color=alt.Color("model:N", scale=alt.Scale(domain=models, range=colors), title="Model"),
        tooltip=[alt.Tooltip("Cihaz:N"), alt.Tooltip("model:N", title="Model"), alt.Tooltip(f"{metric}:Q", format=".3f", title=title)])
    return _style(ch.properties(height=330))


_DASH = [[], [7, 3], [2, 3], [10, 3, 2, 3], [4, 4], [1, 4]]
_AX_X = dict(format="%d.%m %H:%M", grid=False, tickCount=6, labelFontSize=11, domain=False, ticks=False)
_AX_Y = dict(tickCount=5, gridColor="#EDF1F6", gridDash=[2, 3], labelFontSize=11, domain=False, ticks=False)


def _real_area(df, c, x, y):
    grad = alt.Gradient(gradient="linear", x1=1, x2=1, y1=1, y2=0,
                        stops=[alt.GradientStop(color=_rgba(c, 0.0), offset=0), alt.GradientStop(color=_rgba(c, 0.45), offset=1)])
    return alt.Chart(df).mark_area(color=grad, interpolate="step-after", line={"color": c, "strokeWidth": 1.5}).encode(x=x, y=y)


def series_multi(df: pd.DataFrame, appliance: str, models, show_aggregate: bool = False,
                 bands: pd.DataFrame | None = None, height: int = 400):
    """Gerçek güç (renkli alan) ve tüm seçili modellerin tahmini aynı grafikte.
    df: timestamp, Gerçek, Toplam, m0, m1, ... (data.wide)."""
    c = theme.color(appliance)
    x = alt.X("timestamp:T", title=None, axis=alt.Axis(**_AX_X))
    y = alt.Y("Gerçek:Q", title="Güç (W)", axis=alt.Axis(**_AX_Y))
    nearest = alt.selection_point(fields=["timestamp"], nearest=True, on="mouseover", empty=False, clear="mouseout")
    layers = []
    if bands is not None and not bands.empty:
        layers.append(alt.Chart(bands).mark_rect(color=c, opacity=0.07).encode(x=alt.X("start:T"), x2="end:T"))
    if show_aggregate:
        layers.append(alt.Chart(df).mark_line(color="#C9D3E0", strokeWidth=1, interpolate="step-after").encode(
            x=x, y=alt.Y("Toplam:Q", title="Güç (W)")))
    layers.append(_real_area(df, c, x, y))
    for i, m in enumerate(models):
        layers.append(alt.Chart(df).mark_line(color=theme.mcolor(m), strokeWidth=2, interpolate="step-after",
                                              strokeDash=_DASH[i % len(_DASH)], opacity=0.95).encode(x=x, y=alt.Y(f"m{i}:Q")))
    tips = [alt.Tooltip("timestamp:T", format="%d.%m %H:%M:%S", title="Zaman"), alt.Tooltip("Gerçek:Q", format=".0f", title="Gerçek (W)")]
    tips += [alt.Tooltip(f"m{i}:Q", format=".0f", title=f"{m} (W)") for i, m in enumerate(models)]
    layers.append(alt.Chart(df).mark_point(opacity=0).encode(x=x, y=y).add_params(nearest))
    layers.append(alt.Chart(df).mark_rule(color="#94A3B8", strokeDash=[3, 3]).encode(x=x, tooltip=tips).transform_filter(nearest))
    layers.append(alt.Chart(df).mark_circle(size=80, color=c, stroke="#FFFFFF", strokeWidth=2, opacity=1).encode(x=x, y=y).transform_filter(nearest))
    for i, m in enumerate(models):
        layers.append(alt.Chart(df).mark_circle(size=60, color=theme.mcolor(m), stroke="#FFFFFF", strokeWidth=2, opacity=1).encode(
            x=x, y=alt.Y(f"m{i}:Q")).transform_filter(nearest))
    return _style(alt.layer(*layers).properties(height=height))


def overview(df: pd.DataFrame, appliance: str, start, end):
    """İnce 'mini harita': tüm zaman aralığı; seçili pencere vurgulanır."""
    c = theme.color(appliance)
    x = alt.X("timestamp:T", title=None, axis=alt.Axis(format="%d.%m", grid=False, tickCount=8, labelFontSize=11, domain=False, ticks=False))
    area = alt.Chart(df).mark_area(color=_rgba(c, 0.35), line={"color": c, "strokeWidth": 1}, interpolate="monotone").encode(
        x=x, y=alt.Y("Gerçek:Q", title=None, axis=None))
    win = alt.Chart(pd.DataFrame({"a": [start], "b": [end]})).mark_rect(color=c, opacity=0.18, stroke=c, strokeWidth=1.5).encode(
        x=alt.X("a:T"), x2="b:T")
    mid = pd.Timestamp(start) + (pd.Timestamp(end) - pd.Timestamp(start)) / 2
    pin = alt.Chart(pd.DataFrame({"t": [mid]})).mark_rule(color=theme.INK, strokeWidth=3).encode(x="t:T")
    return _style((area + win + pin).properties(height=70))


def facets(frames: dict, models, height: int = 92):
    """Tüm cihazlar alt alta (küçük çoklu grafikler). frames: {cihaz: data.wide çıktısı (pencerelenmiş)}."""
    parts = []
    items = list(frames.items())
    for n, (a, df) in enumerate(items):
        c = theme.color(a)
        last = n == len(items) - 1
        x = alt.X("timestamp:T", title=None, axis=alt.Axis(**{**_AX_X, "labels": last}))
        y = alt.Y("Gerçek:Q", title="W", axis=alt.Axis(**{**_AX_Y, "tickCount": 3}))
        layers = [_real_area(df, c, x, y)]
        for i, m in enumerate(models):
            layers.append(alt.Chart(df).mark_line(color=theme.mcolor(m), strokeWidth=1.7, interpolate="step-after",
                                                  strokeDash=_DASH[i % len(_DASH)]).encode(x=x, y=alt.Y(f"m{i}:Q")))
        title = alt.TitleParams(theme.tr(a), anchor="start", fontSize=13, font=FONT, color=c, fontWeight=700, offset=2)
        parts.append(alt.layer(*layers).properties(height=height, title=title))
    return _style(alt.vconcat(*parts, spacing=30).resolve_scale(x="shared"))


def stacked_multi(bills: dict):
    """Dikey şeritler yan yana: ilk sütun gerçek fatura, sonra her modelin tahmini. bills: {sütun adı: fatura tablosu}."""
    first = next(iter(bills.values()))
    names, colors = theme.palette(list(first.index))
    rows = []
    for seri, bill in bills.items():
        col = "Gerçek (TL)" if seri == "Gerçek" else "Tahmin (TL)"
        total = max(float(bill[col].sum()), 1e-9)
        start = 0.0
        for a, v in bill[col].items():
            v = float(v)
            rows.append(dict(Seri=seri, Cihaz=theme.tr(a), TL=round(v, 2), Pay=round(v / total * 100, 1), start=start, end=start + v,
                             mid=start + v / 2))
            start += v
    d = pd.DataFrame(rows)
    order = list(bills)
    x = alt.X("Seri:N", sort=order, title=None, axis=alt.Axis(labelAngle=0, labelFontSize=13, labelColor=theme.INK, ticks=False, domain=False,
                                                             labelPadding=8, labelLimit=170))
    ymax = float(d["end"].max()) * 1.04 or 1.0
    bar = alt.Chart(d).mark_bar(width={"band": 0.62}, cornerRadius=4, stroke="#FFFFFF", strokeWidth=2).encode(
        x=x, y=alt.Y("start:Q", title="Fatura (TL)", scale=alt.Scale(domain=[0, ymax], nice=False), axis=alt.Axis(format=",.0f", tickCount=6)), y2="end:Q",
        color=alt.Color("Cihaz:N", scale=alt.Scale(domain=names, range=colors), legend=None),
        tooltip=[alt.Tooltip("Seri:N", title="Sütun"), alt.Tooltip("Cihaz:N"), alt.Tooltip("TL:Q", format=",.2f", title="Tutar (TL)"),
                 alt.Tooltip("Pay:Q", format=".1f", title="Fatura payı (%)")])
    txt = (alt.Chart(d).transform_calculate(label=f"(datum.end - datum.start) / {ymax} * height >= 16 ? format(datum.TL, ',.0f') : ''")
           .mark_text(color="white", fontWeight=600, fontSize=12, font=FONT).encode(tooltip=alt.value(None), x=x, y="mid:Q", text="label:N"))
    return _style((bar + txt).properties(height=390))


def scorecard(d: pd.DataFrame):
    """Ölçüt karnesi: her ölçütte en iyi model 100 olacak şekilde modellerin göreli başarısı.
    d: sütunlar Ölçüt, Model, Skor (0-100)."""
    models = sorted(d["Model"].unique())
    order = list(dict.fromkeys(d["Ölçüt"]))
    ch = alt.Chart(d).mark_bar(cornerRadiusTopLeft=5, cornerRadiusTopRight=5).encode(
        x=alt.X("Ölçüt:N", sort=order, title=None, axis=alt.Axis(labelAngle=0, labelFontSize=13, labelColor=theme.INK, labelLimit=170, ticks=False, domain=False)),
        xOffset=alt.XOffset("Model:N", sort=models),
        y=alt.Y("Skor:Q", title="En iyi modele göre başarı (%)", scale=alt.Scale(domain=[0, 105]), axis=alt.Axis(tickCount=5, values=[0, 25, 50, 75, 100])),
        color=alt.Color("Model:N", scale=alt.Scale(domain=models, range=[theme.mcolor(m) for m in models]), legend=None),
        tooltip=[alt.Tooltip("Ölçüt:N"), alt.Tooltip("Model:N"), alt.Tooltip("Skor:Q", format=".0f", title="Başarı (%)"), alt.Tooltip("Değer:N", title="Değer")])
    txt = alt.Chart(d).mark_text(dy=-8, fontSize=11, font=FONT, color=theme.INK, fontWeight=600).encode(tooltip=alt.value(None), 
        x=alt.X("Ölçüt:N", sort=order), xOffset=alt.XOffset("Model:N", sort=models), y="Skor:Q", text=alt.Text("Skor:Q", format=".0f"))
    return _style((ch + txt).properties(height=330))


def savings_bars(s: pd.DataFrame):
    """Cihaz bazında aylık tasarruf (TL). s: index=cihaz, 'Tasarruf TL' sütunu."""
    d = s[s["Tasarruf TL"] > 0].reset_index()
    d = d.rename(columns={d.columns[0]: "appliance"})
    d["Cihaz"] = d["appliance"].map(theme.tr)
    d = d.sort_values("Tasarruf TL", ascending=False)
    names, colors = theme.palette(list(d["appliance"]))
    base = alt.Chart(d).encode(
        y=alt.Y("Cihaz:N", sort=list(d["Cihaz"]), title=None, axis=alt.Axis(labelFontSize=13, labelColor=theme.INK, labelLimit=220, ticks=False, domain=False)),
        x=alt.X("Tasarruf TL:Q", title="Aylık tasarruf (TL)", axis=alt.Axis(tickCount=5, format=",.0f")))
    bar = base.mark_bar(cornerRadiusEnd=4, height={"band": 0.6}).encode(
        color=alt.Color("Cihaz:N", scale=alt.Scale(domain=names, range=colors), legend=None),
        tooltip=[alt.Tooltip("Cihaz:N"), alt.Tooltip("Tasarruf TL:Q", format=",.2f", title="Aylık tasarruf (TL)"),
                 alt.Tooltip("Tasarruf kWh:Q", format=",.1f", title="Aylık tasarruf (kWh)")])
    txt = base.mark_text(align="left", dx=8, fontSize=13, font=FONT, color=theme.INK, fontWeight=600).encode(
        tooltip=alt.value(None), text=alt.Text("Tasarruf TL:Q", format=",.1f"))
    return _style((bar + txt).properties(height=max(110, 52 * len(d))))
