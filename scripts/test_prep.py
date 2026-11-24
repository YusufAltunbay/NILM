"""Veri hazırlama kodunu sahte veriyle sınar."""
import numpy as np, pandas as pd
from nilm.data import prep

rng = np.random.default_rng(0)
parts = []
for house in [1, 2, 3]:
    n = 2000
    app = np.where(rng.random(n) > 0.7, 120.0, 0.0)
    df = pd.DataFrame({"timestamp": pd.date_range("2024-01-01", periods=n, freq="6s"),
                       "house": house, "appliance": "fridge",
                       "aggregate_w": app + 200 + rng.random(n) * 50, "appliance_w": app})
    df.loc[100:110, "aggregate_w"] = np.nan     # kısa boşluk -> doldurulmalı
    df.loc[1000:1100, "appliance_w"] = np.nan   # uzun boşluk -> atılmalı
    df.loc[5, "aggregate_w"] = -3               # geçersiz
    parts.append(df)
raw = pd.concat(parts, ignore_index=True)

c = prep.clean(raw)
assert c[["aggregate_w", "appliance_w"]].notna().all().all()
assert (c["appliance_w"] <= c["aggregate_w"]).all()
assert len(c) < len(raw) and len(c) > 0.9 * len(raw)

tr, va, te = prep.split_by_house(c, [1], [2], [3])
assert set(tr.house) == {1} and set(te.house) == {3}

norm = prep.Normalizer().fit(tr)
X, y = prep.windows(tr, window=99, norm=norm)
assert X.shape[1] == 99 and len(X) == len(y)
# atılan uzun boşluğun üzerinden pencere geçmemeli: iki parça
seg = prep._segments(tr["timestamp"], 6)
assert len(seg) == 2
assert len(X) == sum(len(s) - 98 for s in seg)
assert abs(X.mean()) < 0.1 and y.max() <= 1.0
print("tamam:", len(raw), "->", len(c), "satır;", X.shape, "pencere")
