"""WindowDataset: prep.windows ile aynı pencereler, boşlukları aşmama, stride."""
import numpy as np
import pandas as pd

from nilm.data import prep
from nilm.data.dataset import WindowDataset


def _df(n=500, gap_at=None, house=1):
    ts = pd.date_range("2024-01-01", periods=n, freq="6s")
    if gap_at:
        ts = ts[:gap_at].append(ts[gap_at:] + pd.Timedelta("10min"))
    rng = np.random.default_rng(0)
    app = np.where(rng.random(n) > 0.7, 120.0, 0.0)
    return pd.DataFrame({"timestamp": ts, "house": house, "appliance": "fridge",
                         "aggregate_w": app + 200 + rng.random(n) * 50, "appliance_w": app})


def test_matches_prep_windows():
    df = _df(gap_at=200)
    norm = prep.Normalizer().fit(df)
    X, y = prep.windows(df, window=21, norm=norm)
    ds = WindowDataset(df, norm, window=21)
    assert len(ds) == len(X)
    for i in range(len(ds)):
        a, b = ds[i]
        np.testing.assert_allclose(a.numpy(), X[i], rtol=1e-6)
        assert np.isclose(b.item(), y[i])


def test_no_window_crosses_gap():
    df = _df(gap_at=200)
    norm = prep.Normalizer().fit(df)
    ds = WindowDataset(df, norm, window=21)
    assert len(ds) == (200 - 20) + (300 - 20)


def test_stride_and_multiple_houses():
    df = pd.concat([_df(house=1), _df(house=2)], ignore_index=True)
    norm = prep.Normalizer().fit(df)
    full = WindowDataset(df, norm, window=21)
    thin = WindowDataset(df, norm, window=21, stride=5)
    assert len(full) == 2 * (500 - 20)
    assert len(thin) == 2 * len(range(0, 480, 5))


def test_even_window_rejected():
    import pytest
    df = _df()
    with pytest.raises(ValueError):
        WindowDataset(df, prep.Normalizer().fit(df), window=20)
