"""Sahte veriyle uçtan uca kontrol: şema -> model -> değerlendirme."""
import numpy as np, pandas as pd
from nilm.data.schema import validate
from nilm.models.base import MeanModel
from nilm.eval.evaluate import evaluate

n = 1000
app = np.where(np.random.rand(n) > 0.7, 120.0, 0.0)
df = validate(pd.DataFrame({
    "timestamp": pd.date_range("2024-01-01", periods=n, freq="6s"),
    "house": 1, "appliance": "fridge",
    "aggregate_w": app + 200 + np.random.rand(n) * 50, "appliance_w": app}))
print(evaluate(MeanModel().fit(df[:800]), df[800:], "synthetic", "fridge", log=False))
