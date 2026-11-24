"""Gerçek veri gelene kadar şemaya uygun sahte veri üretir (sadece geliştirme/test için)."""
import numpy as np
import pandas as pd
from nilm import config
from nilm.data.schema import validate

# (açık güç W, açık kalma oranı, ortalama açık süre örnek sayısı)
_PROFILES = {
    "fridge": (120, 0.35, 100),
    "washing machine": (500, 0.08, 300),
    "kettle": (2200, 0.01, 20),
    "dish washer": (700, 0.07, 250),
    "microwave": (1200, 0.02, 30),
}


def _appliance_signal(rng, n, power, duty, mean_len):
    sig = np.zeros(n)
    i = 0
    while i < n:
        gap = int(rng.exponential(mean_len * (1 - duty) / duty))
        i += gap
        length = max(1, int(rng.exponential(mean_len)))
        sig[i:i + length] = power * (1 + 0.05 * rng.standard_normal(min(length, max(0, n - i))))
        i += length
    return np.clip(sig, 0, None)


def make(houses=(1, 2, 3, 4, 5), n=20000, seed=0):
    rng = np.random.default_rng(seed)
    ts = pd.date_range("2024-01-01", periods=n, freq=f"{config.SAMPLE_PERIOD_S}s", tz="UTC")
    frames = []
    for h in houses:
        sigs = {a: _appliance_signal(rng, n, *_PROFILES[a]) for a in config.APPLIANCES}
        base = 80 + 40 * rng.random() + 20 * rng.standard_normal(n).clip(-2, 2)
        agg = base.clip(0) + sum(sigs.values())
        for a, s in sigs.items():
            frames.append(pd.DataFrame({"timestamp": ts, "house": h, "appliance": a,
                                        "aggregate_w": agg, "appliance_w": s}))
    return validate(pd.concat(frames, ignore_index=True))
