import numpy as np
import pandas as pd
import pytest

from nilm.data import prep
from nilm.data.dataset import WindowDataset
from nilm.models.windowed import WindowedModel, sliding_predict

IDENT = prep.Normalizer(agg_mean=0.0, agg_std=1.0, app_max=1.0)


def center(x):  # pencere ortasını döndürür
    return x[:, x.shape[1] // 2]


@pytest.mark.parametrize("n", [1, 5, 99, 100, 1000])
def test_same_length_and_alignment(n):
    agg = np.arange(1, n + 1, dtype="float64") * 10
    out = sliding_predict(center, agg, IDENT, window=99, batch_size=64)
    assert len(out) == n
    np.testing.assert_allclose(out, agg)  # kenarlar dahil, her örnek kendi yerinde


def test_batch_size_independent():
    agg = np.random.default_rng(0).random(500) * 100
    f = lambda x: x.mean(axis=1)
    a = sliding_predict(f, agg, IDENT, window=21, batch_size=7)
    b = sliding_predict(f, agg, IDENT, window=21, batch_size=10_000)
    np.testing.assert_allclose(a, b, rtol=1e-6)


def test_clipped_to_zero_and_aggregate():
    agg = np.full(50, 100.0)
    assert sliding_predict(lambda x: np.full(len(x), 500.0), agg, IDENT, 11).max() == 100.0
    assert sliding_predict(lambda x: np.full(len(x), -5.0), agg, IDENT, 11).min() == 0.0


def test_empty_and_even_window():
    assert len(sliding_predict(center, np.array([]), IDENT)) == 0
    with pytest.raises(ValueError):
        sliding_predict(center, np.ones(10), IDENT, window=10)


def test_bad_batch_output_rejected():
    with pytest.raises(ValueError):
        sliding_predict(lambda x: np.zeros(1), np.ones(50), IDENT, window=11, batch_size=10)


def test_windows_match_training_dataset():
    """Çıkarımda modele giden pencereler, eğitimdekiyle (WindowDataset) aynı olmalı."""
    n, w = 300, 21
    rng = np.random.default_rng(1)
    df = pd.DataFrame({"timestamp": pd.date_range("2024-01-01", periods=n, freq="6s"),
                       "house": 1, "appliance": "fridge",
                       "aggregate_w": 200 + rng.random(n) * 50, "appliance_w": rng.random(n) * 100})
    norm = prep.Normalizer().fit(df)
    seen = []
    sliding_predict(lambda x: seen.append(x.copy()) or np.zeros(len(x)), df.aggregate_w.to_numpy(),
                    norm, window=w, batch_size=50)
    X = np.concatenate(seen)
    ds = WindowDataset(df, norm, window=w)
    half = w // 2
    for k in [0, 1, len(ds) // 2, len(ds) - 1]:
        np.testing.assert_allclose(X[k + half], ds[k][0].numpy(), rtol=1e-6)


class _Toy(WindowedModel):
    name = "toy"
    window = 11

    def fit(self, train):
        self.fit_normalizer(train)
        return self

    def predict_batch(self, x):
        return center(x) * 0 + 0.5


def test_windowed_model_contract():
    df = pd.DataFrame({"timestamp": pd.date_range("2024-01-01", periods=60, freq="6s"), "house": 1,
                       "appliance": "fridge", "aggregate_w": 300.0, "appliance_w": 100.0})
    m = _Toy()
    with pytest.raises(RuntimeError):
        m.predict(df.aggregate_w.to_numpy())
    out = m.fit(df).predict(df.aggregate_w.to_numpy())
    assert len(out) == 60 and np.allclose(out, 50.0)  # 0.5 * app_max(100)
