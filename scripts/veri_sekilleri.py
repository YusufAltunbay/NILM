"""Rapor için veri analizi şekilleri -> results/figures/veri/*.png

Girdi: data/processed/{cihaz}.h5 (06 numaralı şekil için ayrıca data/raw/ukdale.h5).
Kullanım: python -m scripts.veri_sekilleri
"""
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib.colors import LinearSegmentedColormap
from matplotlib.patches import Patch

from nilm import config
from nilm.data import prep, ukdale
from nilm.data.dataset import load_processed

OUT = Path(__file__).resolve().parents[1] / "results" / "figures" / "veri"

# Renk: roller = kategorik (sabit sıra), cihazlar = küçük çoklu paneller (tek renk).
SURFACE, INK, INK2, GRID = "#fcfcfb", "#1a1a19", "#5b5a55", "#e1e0d9"
BLUE, ORANGE, AQUA = "#2a78d6", "#eb6834", "#1baf7a"
ROLE_COLOR = {"eğitim": BLUE, "doğrulama": ORANGE, "test (görülmeyen)": AQUA}
NAMES = {"fridge": "Buzdolabı", "washing machine": "Çamaşır makinesi", "kettle": "Su ısıtıcısı",
         "dish washer": "Bulaşık makinesi", "microwave": "Mikrodalga"}
PERIOD_S = config.SAMPLE_PERIOD_S

plt.rcParams.update({
    "figure.facecolor": SURFACE, "axes.facecolor": SURFACE, "savefig.facecolor": SURFACE,
    "text.color": INK, "axes.labelcolor": INK2, "xtick.color": INK2, "ytick.color": INK2,
    "axes.edgecolor": GRID, "axes.grid": True, "grid.color": GRID, "grid.linewidth": 0.6,
    "axes.spines.top": False, "axes.spines.right": False, "axes.axisbelow": True,
    "font.size": 10, "axes.titlesize": 11, "axes.titleweight": "bold", "axes.titlelocation": "left",
    "legend.frameon": False,
})


def role(house):
    if house in config.UNSEEN_HOUSES:
        return "test (görülmeyen)"
    if house in config.VAL_HOUSES:
        return "doğrulama"
    return "eğitim"


def save(fig, name):
    OUT.mkdir(parents=True, exist_ok=True)
    fig.savefig(OUT / name, dpi=170, bbox_inches="tight")
    plt.close(fig)
    print("yazıldı:", OUT / name)


def collect():
    """Tek geçişte istatistikler: ev x cihaz için gün sayısı, açık oranı, zaman aralığı."""
    rows, on_power, daily_on = [], {}, {}
    for app in config.APPLIANCES:
        df = load_processed(app)
        thr = config.ON_THRESHOLD_W.get(app, config.DEFAULT_ON_THRESHOLD_W)
        for h, g in df.groupby("house"):
            rows.append(dict(app=app, house=h, days=len(g) * PERIOD_S / 86400,
                             on_frac=float((g["appliance_w"] > thr).mean()),
                             t0=g["timestamp"].min(), t1=g["timestamp"].max()))
        g1 = df[df["house"] == 1]
        if len(g1):
            on = g1.loc[g1["appliance_w"] > thr, "appliance_w"]
            on_power[app] = on.sample(min(len(on), 300_000), random_state=0).to_numpy()
            daily_on[app] = (g1.set_index("timestamp")["appliance_w"] > thr).resample("D").sum() * PERIOD_S / 60
    return pd.DataFrame(rows), on_power, daily_on


def fig_ev_ayrimi(st):
    iv = st.groupby("house").agg(t0=("t0", "min"), t1=("t1", "max"))
    fig, ax = plt.subplots(figsize=(10, 3.4))
    for i, (h, r) in enumerate(iv.iterrows()):
        c = ROLE_COLOR[role(h)]
        ax.barh(i, (r.t1 - r.t0).days, left=matplotlib.dates.date2num(r.t0), height=0.55, color=c,
                edgecolor=SURFACE, linewidth=1.5)
        apps = st[st.house == h].app.nunique()
        note = f"{(r.t1 - r.t0).days} gün" + ("" if apps == 5 else " · yalnızca su ısıtıcısı")
        ax.text(matplotlib.dates.date2num(r.t1) + 12, i, note, va="center", fontsize=9, color=INK2)
    ax.set_yticks(range(len(iv)), [f"Ev {h}" for h in iv.index])
    ax.invert_yaxis()
    ax.xaxis_date()
    ax.set_xlim(right=matplotlib.dates.date2num(iv.t1.max()) + 330)
    ax.grid(axis="y", visible=False)
    ax.set_title("Evlerin kayıt aralıkları ve kullanım rolü")
    ax.legend(handles=[Patch(color=c, label=r) for r, c in ROLE_COLOR.items()], loc="lower right")
    save(fig, "01_ev_ayrimi.png")


def fig_veri_gunu(st):
    houses = sorted(st.house.unique())
    m = np.full((len(houses), len(config.APPLIANCES)), np.nan)
    for _, r in st.iterrows():
        m[houses.index(r.house), config.APPLIANCES.index(r.app)] = r.days
    cmap = LinearSegmentedColormap.from_list("mavi", ["#cde2fb", "#3987e5", "#104281"])
    fig, ax = plt.subplots(figsize=(8.5, 3.8))
    im = ax.imshow(m, cmap=cmap, aspect="auto", vmin=0)
    for i in range(m.shape[0]):
        for j in range(m.shape[1]):
            v = m[i, j]
            if np.isnan(v):
                ax.text(j, i, "–", ha="center", va="center", color=INK2)
            else:
                ax.text(j, i, f"{v:.0f}", ha="center", va="center", fontsize=10,
                        color="white" if v > m[~np.isnan(m)].max() * 0.45 else INK)
    ax.set_xticks(range(len(config.APPLIANCES)), [NAMES[a] for a in config.APPLIANCES], rotation=15)
    ax.set_yticks(range(len(houses)), [f"Ev {h} ({role(h).split(' ')[0]})" for h in houses])
    ax.grid(False)
    for s in ax.spines.values():
        s.set_visible(False)
    ax.set_title("Temizlenmiş veri miktarı (gün) — ev × cihaz")
    fig.colorbar(im, ax=ax, label="gün", shrink=0.85)
    save(fig, "02_veri_gunu.png")


def fig_acik_orani(st):
    houses = [h for h in (config.TRAIN_HOUSES[0], *config.VAL_HOUSES, *config.UNSEEN_HOUSES)]
    w = 0.26
    fig, ax = plt.subplots(figsize=(10, 4.2))
    for k, h in enumerate(houses):
        xs, vs = [], []
        for j, app in enumerate(config.APPLIANCES):
            r = st[(st.app == app) & (st.house == h)]
            if len(r):
                xs.append(j + (k - 1) * w)
                vs.append(max(r.on_frac.iloc[0] * 100, 1e-3))
        ax.bar(xs, vs, width=w - 0.03, color=ROLE_COLOR[role(h)], label=f"Ev {h} — {role(h)}")
        for x, v in zip(xs, vs):
            ax.text(x, v * 1.12, f"{v:.1f}", ha="center", fontsize=8, color=INK2)
    ax.set_yscale("log")
    ax.set_ylim(0.03, 200)
    ax.set_yticks([0.1, 1, 10, 100], ["0.1", "1", "10", "100"])
    ax.set_xticks(range(len(config.APPLIANCES)), [NAMES[a] for a in config.APPLIANCES])
    ax.grid(axis="x", visible=False)
    ax.set_ylabel("açık kalma oranı (% zaman, log ölçek)")
    ax.set_title("Cihazlar zamanın ne kadarında açık? (cihaz bazlı açık eşiğine göre)")
    ax.legend(loc="upper right")
    save(fig, "03_acik_orani.png")


def fig_ornek_gun(daily_on):
    score = sum((d.clip(upper=30) / 30) for d in daily_on.values())
    ok = pd.concat(daily_on, axis=1, sort=True).ge(1).all(axis=1)
    day = score[ok].idxmax()
    sl = slice(day, day + pd.Timedelta("1D") - pd.Timedelta("1s"))
    fig, axes = plt.subplots(6, 1, figsize=(10, 9), sharex=True,
                             gridspec_kw={"height_ratios": [1.6, 1, 1, 1, 1, 1]})
    for i, app in enumerate(config.APPLIANCES):
        g = load_processed(app)
        g = g[g.house == 1].set_index("timestamp").sort_index().loc[sl]
        if i == 0:
            axes[0].plot(g.index, g.aggregate_w, color=INK2, lw=0.8)
            axes[0].set_title(f"Ev 1 — örnek gün ({day:%d.%m.%Y}, UTC): toplam güç ve cihazlar")
            axes[0].set_ylabel("toplam (W)")
        ax = axes[i + 1]
        ax.plot(g.index, g.appliance_w, color=BLUE, lw=0.9)
        ax.text(0.005, 0.82, NAMES[app], transform=ax.transAxes, fontsize=10, fontweight="bold")
        ax.set_ylabel("W")
        ax.set_ylim(-0.05 * max(g.appliance_w.max(), 1), max(g.appliance_w.max(), 1) * 1.1)
    axes[-1].xaxis.set_major_formatter(matplotlib.dates.DateFormatter("%H:%M"))
    fig.tight_layout()
    save(fig, "04_ornek_gun.png")


def fig_guc_dagilimi(on_power):
    fig, axes = plt.subplots(2, 3, figsize=(11, 5.6))
    for ax, app in zip(axes.flat, config.APPLIANCES):
        v = on_power[app]
        ax.hist(v, bins=60, color=BLUE, edgecolor=SURFACE, linewidth=0.4)
        ax.set_yscale("log")
        ax.set_title(NAMES[app])
        ax.set_xlabel("açıkken güç (W)")
        ax.axvline(config.MAX_POWER_W[app], color=ORANGE, lw=1.2, ls="--")
    axes.flat[-1].axis("off")
    axes.flat[-1].text(0, 0.6, "Turuncu çizgi: temizlemede\nuygulanan üst sınır\n(config.MAX_POWER_W)\n\nEv 1, eğitim verisi\n(her cihazdan ≤300 bin örnek)",
                       fontsize=9, color=INK2, va="top")
    fig.suptitle("Açık durumdaki güç dağılımı (log sayı ekseni)", x=0.01, ha="left", fontweight="bold")
    fig.tight_layout()
    save(fig, "05_guc_dagilimi.png")


def fig_temizleme():
    raw_path = ukdale.DEFAULT_PATH
    if not Path(raw_path).exists():
        print("data/raw/ukdale.h5 yok, 06_temizleme.png atlandı")
        return
    fig, (a, b) = plt.subplots(1, 2, figsize=(12, 3.8))
    raw = ukdale.load(5, "microwave", start="2014-08-10", end="2014-08-13")
    cl = prep.clean(raw)
    a.plot(raw.timestamp, raw.appliance_w, color=INK2, lw=0.8, label="ham")
    a.plot(cl.timestamp, cl.appliance_w, color=BLUE, lw=1.0, label="temizlenmiş")
    a.set_ylim(-5, 130)
    a.set_title("Ev 5 mikrodalga: sabit 50 W ofset sıfırlanır")
    a.set_ylabel("W (1.3 kW'lık kullanım tepeleri görünmüyor)")
    a.xaxis.set_major_locator(matplotlib.dates.DayLocator())
    a.xaxis.set_major_formatter(matplotlib.dates.DateFormatter("%d.%m"))
    a.legend(loc="upper right")
    raw = ukdale.load(1, "fridge", start="2014-10-28 23:00", end="2014-10-28 23:40")
    cl = prep.clean(raw)
    b.plot(raw.timestamp, raw.appliance_w, color=INK2, lw=0.9, label="ham")
    b.plot(cl.timestamp, cl.appliance_w, color=BLUE, lw=1.2, label="temizlenmiş")
    b.set_title("Ev 1 buzdolabı: kalkış tepesi 300 W'a kırpılır")
    b.set_ylabel("W")
    b.xaxis.set_major_formatter(matplotlib.dates.DateFormatter("%H:%M"))
    b.legend(loc="upper right")
    fig.tight_layout()
    save(fig, "06_temizleme.png")


def main():
    st, on_power, daily_on = collect()
    st.to_csv((OUT.mkdir(parents=True, exist_ok=True) or OUT) / "veri_ozeti.csv", index=False)
    fig_ev_ayrimi(st)
    fig_veri_gunu(st)
    fig_acik_orani(st)
    fig_ornek_gun(daily_on)
    fig_guc_dagilimi(on_power)
    fig_temizleme()


if __name__ == "__main__":
    main()
