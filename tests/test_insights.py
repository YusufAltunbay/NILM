import pandas as pd

from panel import insights


def test_usage_facts_counts_separate_uses():
    ts = pd.Series(pd.date_range("2026-01-01", periods=1000, freq="6s", tz="UTC"))
    p = [0.0] * 1000
    for start in (100, 400, 700):          # üç ayrı kullanım, her biri 50 örnek x 2500 W
        for i in range(start, start + 50):
            p[i] = 2500.0
    f = insights.usage_facts(ts, pd.Series(p), "kettle", price=3.0)
    assert f["uses"] == 3
    assert abs(f["kwh_per_use"] - 2500 * 50 * 6 / 3600 / 1000) < 1e-9
    assert f["tl_per_use"] == f["kwh_per_use"] * 3.0
    rows = dict(insights.describe(f))
    assert "Bir kullanım" in rows


def test_describe_handles_no_use_and_cycling_devices():
    f = dict(per_day=0, uses=0, kwh_per_use=0, tl_per_use=0, peak_hour=None, minutes_per_day=0)
    assert insights.describe(f) == [("Kullanım", "bu dönemde yok")]
    g = dict(per_day=30, uses=300, kwh_per_use=0.05, tl_per_use=0.1, peak_hour=14, minutes_per_day=240)
    labels = [k for k, _ in insights.describe(g)]
    assert "Çalışma çevrimi" in labels and "Bir kullanım" not in labels


def test_noisy_threshold_crossings_are_not_separate_uses():
    import numpy as np
    n = 2000
    ts = pd.Series(pd.date_range("2026-01-01", periods=n, freq="6s", tz="UTC"))
    rng = np.random.default_rng(0)
    p = np.zeros(n)
    p[500:700] = 2400 + rng.normal(0, 300, 200)       # tek gerçek kullanım, titreyen tahmin
    p[::7] += 3000 * (rng.random(len(p[::7])) < 0.5)   # tek tek eşiği aşan sivri gürültü
    f = insights.usage_facts(ts, pd.Series(p), "kettle", price=3.0)
    assert f["uses"] <= 3                              # binlerce değil


def test_constant_prediction_is_not_described_as_usage():
    f = dict(per_day=0.03, uses=1, kwh_per_use=14.0, tl_per_use=45.0, peak_hour=0, minutes_per_day=1440)
    assert insights.describe(f) == [("Kullanım", "bu model ayırt edemiyor")]
