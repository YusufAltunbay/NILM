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


def plan_for_target(m: pd.DataFrame, target_pct: float, cap: int = MAX_CUT):
    """Faturayı target_pct kadar düşürmek için en pahalı cihazdan başlayarak azaltma planı.
    -> (plan {cihaz: %}, hedef tutuyor mu)."""
    need = m["TL"].sum() * target_pct / 100
    plan = {}
    for a in m["TL"].sort_values(ascending=False).index:
        tl = m.loc[a, "TL"]
        if need <= 1e-9 or tl <= 0:
            break
        take = min(cap / 100 * tl, need)
        pct = min(cap, math.ceil(take / tl * 100 / STEP - 1e-9) * STEP)
        plan[a] = int(pct)
        need -= pct / 100 * tl
    return plan, need <= 1e-6


def suggestions(m: pd.DataFrame, top: int = 3):
    """En pahalı cihazlar için öneri kartı verisi."""
    total = m["TL"].sum() or 1.0
    out = []
    for a in m["TL"].sort_values(ascending=False).index[:top]:
        text, lo, hi = TIPS.get(a, GENERIC)
        tl = m.loc[a, "TL"]
        out.append(dict(appliance=a, tip=text, share=tl / total * 100, tl=tl, low=tl * lo / 100, high=tl * hi / 100, lo=lo, hi=hi))
    return out
