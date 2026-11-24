"""Tasarruf senaryosu hesapları (arayüzden bağımsız, test edilebilir)."""
import math

import pandas as pd

MAX_CUT = 50  # kaydırıcının üst sınırı (%)
STEP = 5

# Öneri metinleri ve tahmini tasarruf aralıkları (%). Bunlar VARSAYIMDIR, ölçüm değil; sunumda "tahmini" denir.
# Tanımsız cihaz için GENERIC kullanılır.
TIPS = {
    "fridge": ("Kapağı az aç, ısıyı 4 °C civarında tut, arkasını temiz bırak.", 5, 10),
    "washing machine": ("Tam dolu çalıştır, 30-40 °C programı seç.", 10, 20),
    "kettle": ("Yalnızca ihtiyacın kadar su kaynat.", 10, 25),
    "dish washer": ("Tam dolu çalıştır, eko programı kullan.", 10, 20),
    "microwave": ("Küçük porsiyonlar için ocak yerine kısa süreli kullan, gereksiz bekletme.", 5, 10),
}
GENERIC = ("Kullanım süresini ve sıklığını azalt.", 5, 15)


PRESETS = ("Hafif", "Orta", "Sıkı")


def tip_range(appliance: str):
    _, lo, hi = TIPS.get(appliance, GENERIC)
    return lo, hi


def preset_cuts(appliances, level: str) -> dict:
    """Her cihaz için kendi gerçekçi aralığından: Hafif = alt sınır, Orta = orta nokta, Sıkı = üst sınır."""
    t = {"Hafif": 0.0, "Orta": 0.5, "Sıkı": 1.0}[level]
    out = {}
    for a in appliances:
        lo, hi = tip_range(a)
        out[a] = min(MAX_CUT, int(round((lo + (hi - lo) * t) / STEP) * STEP))
    return out


def span_days(timestamps: pd.Series) -> float:
    """Verinin kapsadığı gün sayısı (en az 1)."""
    return max(1.0, (timestamps.max() - timestamps.min()).total_seconds() / 86400)


def monthly(bill: pd.DataFrame, days: float) -> pd.DataFrame:
    """Veri penceresindeki tutarları 30 günlük aya ölçekler. bill: data.bill_table çıktısı."""
    k = 30.0 / days
    return pd.DataFrame({"kWh": bill["Tahmin (kWh)"] * k, "TL": bill["Tahmin (TL)"] * k})


def scenario(m: pd.DataFrame, cuts: dict) -> pd.DataFrame:
    """cuts: {cihaz: azaltma %}. -> Sütunlar: TL, Yeni TL, Tasarruf TL, Tasarruf kWh."""
    r = pd.Series({a: cuts.get(a, 0) / 100 for a in m.index})
    out = pd.DataFrame({"TL": m["TL"], "Yeni TL": m["TL"] * (1 - r)})
    out["Tasarruf TL"] = out["TL"] - out["Yeni TL"]
    out["Tasarruf kWh"] = m["kWh"] * r
    return out


def plan_for_target(m: pd.DataFrame, target_pct: float):
    """Faturayı target_pct kadar düşürmek için plan. Her cihaz kendi gerçekçi tavanını (TIPS üst sınırı) aşmaz;
    kazancı en yüksek cihazdan başlanır. -> (plan {cihaz: %}, hedef tutuyor mu, toplam potansiyel TL)."""
    need = m["TL"].sum() * target_pct / 100
    cap = {a: tip_range(a)[1] for a in m.index}
    potential = {a: m.loc[a, "TL"] * cap[a] / 100 for a in m.index}
    plan = {}
    for a in sorted(potential, key=potential.get, reverse=True):
        tl = m.loc[a, "TL"]
        if need <= 1e-9 or tl <= 0:
            break
        take = min(potential[a], need)
        pct = min(cap[a], math.ceil(take / tl * 100 / STEP - 1e-9) * STEP)
        pct = max(STEP, pct) if cap[a] >= STEP else cap[a]
        plan[a] = int(min(MAX_CUT, pct))
        need -= plan[a] / 100 * tl
    return plan, need <= 1e-6, sum(potential.values())


def suggestions(m: pd.DataFrame, top: int = 3):
    """Tasarruf POTANSİYELİ (TL, aralığın ortası) en yüksek cihazlar önce. Fatura payı değil, kazanç sıralar."""
    total = m["TL"].sum() or 1.0
    rows = []
    for a in m.index:
        text, lo, hi = TIPS.get(a, GENERIC)
        tl = m.loc[a, "TL"]
        rows.append(dict(appliance=a, tip=text, share=tl / total * 100, tl=tl, low=tl * lo / 100, high=tl * hi / 100,
                         mid=tl * (lo + hi) / 200, lo=lo, hi=hi, mid_pct=min(MAX_CUT, int(round((lo + hi) / 2 / STEP) * STEP))))
    return sorted(rows, key=lambda r: r["mid"], reverse=True)[:top]
